"""Recipe detection and ingredient extraction service using Amazon Bedrock."""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import re

try:
    from ..settings import settings
    from ..utils.observability import trace_function, obs_manager
    from .bedrock_service import BedrockService
    from .web_scraper import WebScraperService
except ImportError:
    # Direct import when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from settings import settings
    from utils.observability import trace_function, obs_manager
    from services.bedrock_service import BedrockService
    from services.web_scraper import WebScraperService

logger = logging.getLogger(__name__)


class RecipeDetectorService:
    """Service for AI-powered recipe detection and ingredient extraction."""
    
    def __init__(self):
        """Initialize the recipe detector service."""
        self.bedrock_service = BedrockService()
        self.web_scraper = WebScraperService()
        
        # Simple in-memory cache with TTL (1 hour)
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour in seconds
        
        # Confidence thresholds
        self.recipe_confidence_threshold = 0.7
        self.ingredient_confidence_threshold = 0.6
        
        logger.info("RecipeDetectorService initialized")
    
    def _get_cache_key(self, url: str, operation: str) -> str:
        """Generate cache key for URL and operation."""
        content = f"{url}_{operation}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache if still valid."""
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            # Check if cache is still valid
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_data['data']
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key}")
        
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store result in cache with timestamp."""
        self._cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        logger.debug(f"Cached result for key: {cache_key}")
    
    def _create_recipe_detection_prompt(self, content: str, language: str = "auto") -> str:
        """Create prompt for recipe detection."""
        if not isinstance(content, str):
            content = str(content)
        
        if language == "ja" or (language == "auto" and self._detect_japanese(content)):
            return f"""あなたは料理レシピの専門家です。以下のウェブページのコンテンツを分析して、これが料理のレシピページかどうかを判定してください。

コンテンツ:
{content[:3000]}  # Limit content length

以下の基準で判定してください：
1. 材料リストが含まれているか
2. 調理手順や作り方が含まれているか  
3. 料理名や完成品の説明があるか
4. 調理時間や分量の記載があるか

回答は以下のJSON形式で返してください：
{{
    "is_recipe": true/false,
    "confidence": 0.0-1.0,
    "reason": "判定理由",
    "detected_elements": ["要素1", "要素2", ...],
    "language": "ja"
}}"""
        else:
            return f"""You are a culinary expert. Analyze the following web page content and determine if this is a recipe page.

Content:
{content[:3000]}  # Limit content length

Evaluate based on these criteria:
1. Contains ingredient list
2. Contains cooking instructions or method
3. Has dish name or description
4. Includes cooking time or serving information

Please respond in the following JSON format:
{{
    "is_recipe": true/false,
    "confidence": 0.0-1.0,
    "reason": "reasoning for the decision",
    "detected_elements": ["element1", "element2", ...],
    "language": "en"
}}"""
    
    def _create_ingredient_extraction_prompt(self, content: str, language: str = "auto") -> str:
        """Create prompt for ingredient extraction."""
        if not isinstance(content, str):
            content = str(content)
            
        if language == "ja" or (language == "auto" and self._detect_japanese(content)):
            return f"""あなたは料理レシピの専門家です。以下のレシピコンテンツから材料リストを抽出してください。

コンテンツ:
{content[:4000]}  # Limit content length

材料を以下の形式で構造化して抽出してください：
- 材料名
- 分量（数値）
- 単位（g、ml、個、カップなど）
- 備考（あれば）

回答は以下のJSON形式で返してください：
{{
    "ingredients": [
        {{
            "name": "材料名",
            "quantity": "分量",
            "unit": "単位",
            "notes": "備考"
        }}
    ],
    "serving_size": "人数",
    "confidence": 0.0-1.0,
    "language": "ja"
}}"""
        else:
            return f"""You are a culinary expert. Extract the ingredient list from the following recipe content.

Content:
{content[:4000]}  # Limit content length

Extract ingredients in structured format with:
- Ingredient name
- Quantity (numerical value)
- Unit (g, ml, pieces, cups, etc.)
- Notes (if any)

Please respond in the following JSON format:
{{
    "ingredients": [
        {{
            "name": "ingredient name",
            "quantity": "amount",
            "unit": "unit",
            "notes": "additional notes"
        }}
    ],
    "serving_size": "number of servings",
    "confidence": 0.0-1.0,
    "language": "en"
}}"""
    
    def _detect_japanese(self, text: str) -> bool:
        """Detect if text contains Japanese characters."""
        if not isinstance(text, str):
            return False
        # Check for Hiragana, Katakana, or Kanji characters
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
        return bool(re.search(japanese_pattern, text))
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON content."""
        try:
            # Convert to string if needed
            if not isinstance(response, str):
                response = str(response)
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # Fallback parsing
                logger.warning("No JSON found in AI response, attempting fallback parsing")
                return self._fallback_parse_response(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._fallback_parse_response(response)
    
    def _fallback_parse_response(self, response: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails."""
        # Convert to string if needed
        if not isinstance(response, str):
            response = str(response)
        
        # Simple keyword-based fallback
        is_recipe = any(keyword in response.lower() for keyword in 
                       ['recipe', 'ingredient', 'cook', 'bake', '材料', 'レシピ', '作り方'])
        
        return {
            "is_recipe": is_recipe,
            "confidence": 0.5,  # Low confidence for fallback
            "reason": "Fallback parsing due to JSON parsing error",
            "detected_elements": [],
            "language": "ja" if self._detect_japanese(response) else "en"
        }
    
    def _validate_detection_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize detection result."""
        # Ensure required fields exist
        validated = {
            "is_recipe": result.get("is_recipe", False),
            "confidence": max(0.0, min(1.0, result.get("confidence", 0.0))),
            "reason": result.get("reason", "No reason provided"),
            "detected_elements": result.get("detected_elements", []),
            "language": result.get("language", "en")
        }
        
        # Apply confidence threshold
        if validated["confidence"] < self.recipe_confidence_threshold:
            validated["is_recipe"] = False
            validated["reason"] += f" (Below confidence threshold: {self.recipe_confidence_threshold})"
        
        return validated
    
    def _validate_ingredient_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize ingredient extraction result."""
        ingredients = result.get("ingredients", [])
        
        # Clean and validate ingredients
        validated_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict) and ingredient.get("name"):
                cleaned_ingredient = {
                    "name": str(ingredient.get("name", "")).strip(),
                    "quantity": str(ingredient.get("quantity", "")).strip(),
                    "unit": str(ingredient.get("unit", "")).strip(),
                    "notes": str(ingredient.get("notes", "")).strip()
                }
                if cleaned_ingredient["name"]:  # Only add if name exists
                    validated_ingredients.append(cleaned_ingredient)
        
        validated = {
            "ingredients": validated_ingredients,
            "serving_size": str(result.get("serving_size", "")).strip(),
            "confidence": max(0.0, min(1.0, result.get("confidence", 0.0))),
            "language": result.get("language", "en"),
            "total_ingredients": len(validated_ingredients)
        }
        
        return validated
    
    @trace_function("recipe_detector_detect")
    def detect_recipe(self, url: str, language: str = "auto") -> Dict[str, Any]:
        """
        Detect if a URL contains a recipe page.
        
        Args:
            url: URL to analyze
            language: Language preference ("en", "ja", or "auto")
            
        Returns:
            Dictionary containing detection results and metadata
        """
        # Check cache first
        cache_key = self._get_cache_key(url, f"detect_{language}")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached recipe detection for: {url}")
            return cached_result
        
        try:
            start_time = time.time()
            logger.info(f"Detecting recipe from URL: {url}")
            
            # Fetch page content
            page_data = self.web_scraper.fetch_page_content(url)
            
            # Combine relevant content for analysis
            content_parts = []
            if page_data.get("title"):
                title = page_data['title']
                if isinstance(title, str):
                    content_parts.append(f"Title: {title}")
            if page_data.get("meta_description"):
                meta_desc = page_data['meta_description']
                if isinstance(meta_desc, str):
                    content_parts.append(f"Description: {meta_desc}")
            if page_data.get("content"):
                content = page_data['content']
                if isinstance(content, str):
                    content_parts.append(f"Content: {content}")
            
            combined_content = "\n\n".join(content_parts)
            
            # Ensure we have some content to analyze
            if not combined_content.strip():
                logger.warning(f"No analyzable content found for URL: {url}")
                return {
                    "is_recipe": False,
                    "confidence": 0.0,
                    "reason": "No analyzable content found on the webpage",
                    "detected_elements": [],
                    "language": "en",
                    "url": url,
                    "processing_time": time.time() - start_time,
                    "timestamp": datetime.now().isoformat(),
                    "page_metadata": {
                        "title": page_data.get("title"),
                        "content_length": 0,
                        "has_structured_data": bool(page_data.get("structured_data")),
                        "recipe_indicators": page_data.get("recipe_indicators", {})
                    }
                }
            
            # Create detection prompt
            prompt = self._create_recipe_detection_prompt(combined_content, language)
            
            # Get AI response
            ai_response = self.bedrock_service.invoke_model(
                prompt=prompt,
                model_id=settings.BEDROCK_MODEL_ID,
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            # Extract content from Bedrock response
            if isinstance(ai_response, dict) and "content" in ai_response:
                response_text = ai_response["content"]
                logger.debug(f"Extracted content from Bedrock response: {type(response_text)}")
                
                # Ensure content is a string
                if not isinstance(response_text, str):
                    response_text = str(response_text)
                    logger.warning(f"Converted non-string content to string: {type(ai_response['content'])}")
            else:
                response_text = str(ai_response)
                logger.warning(f"Unexpected AI response format: {type(ai_response)}")
            
            # Parse and validate response
            raw_result = self._parse_ai_response(response_text)
            validated_result = self._validate_detection_result(raw_result)
            
            # Add metadata
            processing_time = time.time() - start_time
            result = {
                **validated_result,
                "url": url,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "page_metadata": {
                    "title": page_data.get("title"),
                    "content_length": len(page_data.get("content", "")),
                    "has_structured_data": bool(page_data.get("structured_data")),
                    "recipe_indicators": page_data.get("recipe_indicators", {})
                }
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            logger.info(f"Recipe detection completed for {url}: {validated_result['is_recipe']} "
                       f"(confidence: {validated_result['confidence']:.2f}) in {processing_time:.2f}s")
            
            # Record metrics
            obs_manager.record_metric("recipe_detector_detection", 1.0, {
                "success": "true",
                "is_recipe": str(validated_result['is_recipe']),
                "confidence_bucket": self._get_confidence_bucket(validated_result['confidence']),
                "language": validated_result['language']
            })
            obs_manager.record_metric("recipe_detector_processing_time", processing_time, {
                "operation": "detect_recipe"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting recipe from {url}: {e}")
            obs_manager.record_metric("recipe_detector_detection", 1.0, {
                "success": "false",
                "error": "detection_failed"
            })
            raise RuntimeError(f"Failed to detect recipe: {str(e)}")
    
    @trace_function("recipe_detector_extract")
    def extract_ingredients(self, url: str, language: str = "auto") -> Dict[str, Any]:
        """
        Extract ingredients from a recipe URL.
        
        Args:
            url: Recipe URL to extract ingredients from
            language: Language preference ("en", "ja", or "auto")
            
        Returns:
            Dictionary containing extracted ingredients and metadata
        """
        # Check cache first
        cache_key = self._get_cache_key(url, f"extract_{language}")
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached ingredient extraction for: {url}")
            return cached_result
        
        try:
            start_time = time.time()
            logger.info(f"Extracting ingredients from URL: {url}")
            
            # First check if it's a recipe
            detection_result = self.detect_recipe(url, language)
            if not detection_result.get("is_recipe", False):
                return {
                    "ingredients": [],
                    "serving_size": "",
                    "confidence": 0.0,
                    "language": detection_result.get("language", "en"),
                    "total_ingredients": 0,
                    "url": url,
                    "processing_time": time.time() - start_time,
                    "timestamp": datetime.now().isoformat(),
                    "error": "Not detected as a recipe page"
                }
            
            # Fetch page content (might be cached from detection)
            page_data = self.web_scraper.fetch_page_content(url)
            
            # Focus on recipe-relevant content
            content_parts = []
            if page_data.get("title"):
                title = page_data['title']
                if isinstance(title, str):
                    content_parts.append(f"Recipe: {title}")
            
            # Add content with focus on ingredients and instructions
            content = page_data.get("content", "")
            if content and isinstance(content, str):
                # Try to extract recipe-specific sections
                ingredient_content = self._extract_ingredient_sections(content)
                content_parts.append(ingredient_content)
            
            combined_content = "\n\n".join(content_parts)
            
            # Ensure we have some content to analyze
            if not combined_content.strip():
                logger.warning(f"No analyzable content found for ingredients extraction: {url}")
                return {
                    "ingredients": [],
                    "serving_size": "",
                    "confidence": 0.0,
                    "language": detection_result.get("language", "en"),
                    "total_ingredients": 0,
                    "url": url,
                    "processing_time": time.time() - start_time,
                    "timestamp": datetime.now().isoformat(),
                    "detection_confidence": detection_result.get("confidence", 0.0),
                    "error": "No analyzable content found for ingredients extraction"
                }
            
            # Create extraction prompt
            prompt = self._create_ingredient_extraction_prompt(combined_content, language)
            
            # Get AI response
            ai_response = self.bedrock_service.invoke_model(
                prompt=prompt,
                model_id=settings.BEDROCK_MODEL_ID,
                max_tokens=2000,  # More tokens for ingredient lists
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            # Extract content from Bedrock response
            if isinstance(ai_response, dict) and "content" in ai_response:
                response_text = ai_response["content"]
                logger.debug(f"Extracted content from Bedrock response: {type(response_text)}")
                
                # Ensure content is a string
                if not isinstance(response_text, str):
                    response_text = str(response_text)
                    logger.warning(f"Converted non-string content to string: {type(ai_response['content'])}")
            else:
                response_text = str(ai_response)
                logger.warning(f"Unexpected AI response format: {type(ai_response)}")
            
            # Parse and validate response
            raw_result = self._parse_ai_response(response_text)
            validated_result = self._validate_ingredient_result(raw_result)
            
            # Add metadata
            processing_time = time.time() - start_time
            result = {
                **validated_result,
                "url": url,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "detection_confidence": detection_result.get("confidence", 0.0)
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            logger.info(f"Ingredient extraction completed for {url}: {len(validated_result['ingredients'])} "
                       f"ingredients (confidence: {validated_result['confidence']:.2f}) in {processing_time:.2f}s")
            
            # Record metrics
            obs_manager.record_metric("recipe_detector_extraction", 1.0, {
                "success": "true",
                "ingredient_count": str(len(validated_result['ingredients'])),
                "confidence_bucket": self._get_confidence_bucket(validated_result['confidence']),
                "language": validated_result['language']
            })
            obs_manager.record_metric("recipe_detector_processing_time", processing_time, {
                "operation": "extract_ingredients"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting ingredients from {url}: {e}")
            obs_manager.record_metric("recipe_detector_extraction", 1.0, {
                "success": "false",
                "error": "extraction_failed"
            })
            raise RuntimeError(f"Failed to extract ingredients: {str(e)}")
    
    def _extract_ingredient_sections(self, content: str) -> str:
        """Extract ingredient-focused sections from content."""
        if not isinstance(content, str):
            return ""
            
        # Look for common ingredient section indicators
        ingredient_indicators = [
            "ingredients", "材料", "ingredient list", "材料リスト",
            "instructions", "作り方", "directions", "手順"
        ]
        
        lines = content.split('\n')
        relevant_lines = []
        in_ingredient_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if we're entering an ingredient section
            if any(indicator in line_lower for indicator in ingredient_indicators):
                in_ingredient_section = True
                relevant_lines.append(line)
                continue
            
            # If we're in an ingredient section, keep adding lines
            if in_ingredient_section:
                relevant_lines.append(line)
                # Stop if we hit a section break or get too much content
                if len(relevant_lines) > 100:  # Reasonable limit
                    break
        
        # If no specific sections found, return first portion of content
        if not relevant_lines:
            return content[:2000]
        
        return '\n'.join(relevant_lines)
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for metrics."""
        if confidence >= 0.9:
            return "high"
        elif confidence >= 0.7:
            return "medium"
        elif confidence >= 0.5:
            return "low"
        else:
            return "very_low"
    
    def analyze_url(self, url: str, language: str = "auto") -> Dict[str, Any]:
        """
        Complete analysis: detect recipe and extract ingredients if found.
        
        Args:
            url: URL to analyze
            language: Language preference ("en", "ja", or "auto")
            
        Returns:
            Dictionary containing complete analysis results
        """
        try:
            start_time = time.time()
            logger.info(f"Starting complete analysis for URL: {url}")
            
            # Detect if it's a recipe
            detection_result = self.detect_recipe(url, language)
            
            analysis_result = {
                "url": url,
                "is_recipe": detection_result.get("is_recipe", False),
                "detection_confidence": detection_result.get("confidence", 0.0),
                "detection_reason": detection_result.get("reason", ""),
                "language": detection_result.get("language", "en"),
                "timestamp": datetime.now().isoformat()
            }
            
            # If it's a recipe, extract ingredients
            if detection_result.get("is_recipe", False):
                extraction_result = self.extract_ingredients(url, language)
                analysis_result.update({
                    "ingredients": extraction_result.get("ingredients", []),
                    "serving_size": extraction_result.get("serving_size", ""),
                    "extraction_confidence": extraction_result.get("confidence", 0.0),
                    "total_ingredients": extraction_result.get("total_ingredients", 0)
                })
            else:
                analysis_result.update({
                    "ingredients": [],
                    "serving_size": "",
                    "extraction_confidence": 0.0,
                    "total_ingredients": 0
                })
            
            processing_time = time.time() - start_time
            analysis_result["total_processing_time"] = processing_time
            
            logger.info(f"Complete analysis finished for {url} in {processing_time:.2f}s")
            
            # Record comprehensive metrics
            obs_manager.record_metric("recipe_detector_complete_analysis", 1.0, {
                "success": "true",
                "is_recipe": str(analysis_result["is_recipe"]),
                "has_ingredients": str(len(analysis_result["ingredients"]) > 0),
                "language": analysis_result["language"]
            })
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in complete analysis for {url}: {e}")
            obs_manager.record_metric("recipe_detector_complete_analysis", 1.0, {
                "success": "false",
                "error": "analysis_failed"
            })
            raise RuntimeError(f"Failed to analyze URL: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for cache_key, cache_data in self._cache.items():
            if current_time - cache_data['timestamp'] < self._cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_hours": self._cache_ttl / 3600,
            "hit_rate_info": "Cache hits logged in individual method calls"
        }
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared cache with {cache_size} entries")