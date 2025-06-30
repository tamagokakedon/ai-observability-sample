"""RAG service for Knowledge Base integration with AWS Bedrock using LangChain."""

import logging
import time
from typing import Dict, Any, List, Union
from datetime import datetime

try:
    from ..settings import settings
    from ..utils.observability import trace_function, obs_manager
    from .bedrock_service import BedrockService
except ImportError:
    # Direct import when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from settings import settings
    from utils.observability import trace_function, obs_manager
    from services.bedrock_service import BedrockService

# LangChain imports with error handling
LANGCHAIN_AVAILABLE = False
AmazonKnowledgeBasesRetriever = None
RetrievalQA = None
PromptTemplate = None
ChatBedrock = None
Document = Any

try:
    # Try langchain-aws package (recommended for AWS services)
    from langchain_aws import AmazonKnowledgeBasesRetriever
    from langchain_aws import ChatBedrock  # Updated class name
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
    logging.info("LangChain loaded successfully with langchain-aws")
except ImportError as e1:
    logging.warning(f"langchain-aws not available: {e1}")
    try:
        # Fallback to langchain_community
        from langchain_community.retrievers import AmazonKnowledgeBasesRetriever
        from langchain_community.chat_models import BedrockChat as ChatBedrock
        from langchain.chains import RetrievalQA
        from langchain.prompts import PromptTemplate
        from langchain.schema import Document
        LANGCHAIN_AVAILABLE = True
        logging.info("LangChain loaded successfully with langchain_community")
    except ImportError as e2:
        logging.warning(f"LangChain not available with either import method: community={e2}, aws={e1}")
        LANGCHAIN_AVAILABLE = False
        # Keep placeholder types defined above

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG queries using AWS Bedrock Knowledge Base with LangChain."""
    
    def __init__(self):
        """Initialize the RAG service."""
        self.bedrock_service = BedrockService()
        self.retriever = None
        self.qa_chain = None
        self._is_initialized = False
        
        # Recipe-specific prompt template
        if LANGCHAIN_AVAILABLE and PromptTemplate:
            self.recipe_prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template="""あなたは料理の専門家です。以下のレシピ情報を基に、質問に答えてください。

レシピ情報:
{context}

質問: {question}

回答は以下の形式で提供してください：
- レシピ名
- 材料リスト（分量も含めて）
- 調理手順
- 調理時間
- コツやポイント（あれば）

見つからない場合は、代替レシピや類似の料理を提案してください。

回答:"""
            )
        else:
            self.recipe_prompt_template = None
        
        # PDF format specification for S3 storage: [Dish Name].pdf
        self.pdf_format_info = {
            "format": "[Dish Name].pdf",
            "examples": ["チキンテリヤキ.pdf", "パスタカルボナーラ.pdf", "Chicken Teriyaki.pdf"],
            "description": "Recipe PDFs stored in S3 bucket with dish name as filename"
        }
        
        # Initialize if dependencies are available
        if LANGCHAIN_AVAILABLE:
            self._initialize_rag_components()
        
        logger.info(f"RAGService initialized (LangChain available: {LANGCHAIN_AVAILABLE})")
    
    def _initialize_rag_components(self):
        """Initialize LangChain RAG components."""
        try:
            # Check if Knowledge Base is configured
            if not settings.KNOWLEDGE_BASE_ID:
                logger.warning("Knowledge Base ID not configured")
                return
            
            # Check if LangChain components are available
            if not (AmazonKnowledgeBasesRetriever and RetrievalQA and ChatBedrock):
                logger.warning("LangChain components not available for initialization")
                return
            
            # Initialize Knowledge Base retriever
            self.retriever = AmazonKnowledgeBasesRetriever(
                knowledge_base_id=settings.KNOWLEDGE_BASE_ID,
                retrieval_config={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5,
                        "overrideSearchType": "HYBRID"
                    }
                },
                region_name=settings.AWS_DEFAULT_REGION
            )
            
            # Initialize Bedrock LLM through LangChain (using ChatBedrock for Claude v3)
            bedrock_llm = ChatBedrock(
                model_id=settings.BEDROCK_MODEL_ID,
                region=settings.AWS_DEFAULT_REGION,
                model_kwargs={
                    "max_tokens": settings.BEDROCK_MAX_TOKENS,
                    "temperature": settings.BEDROCK_TEMPERATURE
                }
            )
            
            # Create RetrievalQA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=bedrock_llm,
                chain_type="stuff",
                retriever=self.retriever,
                chain_type_kwargs={
                    "prompt": self.recipe_prompt_template
                },
                return_source_documents=True
            )
            
            self._is_initialized = True
            logger.info("RAG components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            self._is_initialized = False
    
    def is_available(self) -> bool:
        """Check if RAG service is properly configured and available."""
        if not LANGCHAIN_AVAILABLE:
            return False
        
        # Check basic configuration
        required_settings = [
            settings.KNOWLEDGE_BASE_ID,
            settings.S3_BUCKET_NAME,
            settings.AWS_DEFAULT_REGION,
            settings.BEDROCK_MODEL_ID
        ]
        
        if not all(required_settings):
            logger.warning("Missing required RAG configuration")
            return False
        
        return self._is_initialized
    
    def _format_dish_query(self, dish_name: str) -> str:
        """Format dish name into an appropriate query."""
        # Clean and format the dish name
        dish_name = dish_name.strip()
        
        # Create search queries in both Japanese and English
        queries = [
            f"{dish_name}のレシピ",
            f"{dish_name} recipe",
            f"{dish_name}の作り方",
            f"How to make {dish_name}",
            dish_name
        ]
        
        # Return the most appropriate query (use first one for now)
        return queries[0]
    
    def _extract_recipe_info(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract structured recipe information from retrieved documents."""
        recipe_info = {
            "recipe_name": "",
            "ingredients": [],
            "instructions": [],
            "cooking_time": "",
            "tips": "",
            "confidence_score": 0.0
        }
        
        if not documents:
            return recipe_info
        
        # Combine all document content
        combined_content = "\n\n".join([
            getattr(doc, 'page_content', str(doc)) for doc in documents
        ])
        
        # Extract recipe name (simple heuristic)
        lines = combined_content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            if any(keyword in line.lower() for keyword in ['recipe', 'レシピ', '料理']):
                recipe_info["recipe_name"] = line.strip()
                break
        
        # Extract ingredients (look for patterns)
        ingredient_patterns = ['材料', 'ingredients', '・', '-', '*']
        ingredients = []
        for line in lines:
            for pattern in ingredient_patterns:
                if pattern in line.lower() and any(char.isdigit() for char in line):
                    ingredients.append(line.strip())
        
        recipe_info["ingredients"] = ingredients[:10]  # Limit to 10 ingredients
        
        # Calculate confidence based on document relevance and content quality
        recipe_info["confidence_score"] = min(len(documents) * 0.2, 1.0)
        
        return recipe_info
    
    def _validate_retrieval_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize retrieval results."""
        validated = {
            "recipe_found": result.get("recipe_found", False),
            "recipe_name": result.get("recipe_name", ""),
            "answer": result.get("answer", ""),
            "ingredients": result.get("ingredients", []),
            "instructions": result.get("instructions", []),
            "confidence": max(0.0, min(1.0, result.get("confidence", 0.0))),
            "sources": result.get("sources", []),
            "processing_time": result.get("processing_time", 0.0),
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "language": result.get("language", "auto")
        }
        
        return validated
    
    @trace_function("rag_service_search")
    def search_recipe(self, dish_name: str, language: str = "auto") -> Dict[str, Any]:
        """
        Search for recipe information using dish name.
        
        Args:
            dish_name: Name of the dish to search for
            language: Language preference ("en", "ja", or "auto")
            
        Returns:
            Dictionary containing recipe information and metadata
        """
        if not self.is_available():
            return {
                "recipe_found": False,
                "recipe_name": "",
                "answer": "RAG service is not available. Please check configuration.",
                "ingredients": [],
                "instructions": [],
                "confidence": 0.0,
                "sources": [],
                "processing_time": 0.0,
                "timestamp": datetime.now().isoformat(),
                "error": "Service not available",
                "language": language
            }
        
        try:
            start_time = time.time()
            logger.info(f"Searching recipe for: {dish_name}")
            
            # Record search request
            obs_manager.record_metric("rag_service_search", 1.0, {
                "success": "pending",
                "dish_name_length": str(len(dish_name))
            })
            
            # Format query
            query = self._format_dish_query(dish_name)
            
            # Perform retrieval and generation
            result = self.qa_chain.invoke({
                "query": query,
                "question": f"{dish_name}のレシピを教えてください"
            })
            
            # Extract information
            answer = result.get("result", "")
            source_documents = result.get("source_documents", [])
            
            # Process and structure the response
            recipe_info = self._extract_recipe_info(source_documents)
            
            processing_time = time.time() - start_time
            
            # Determine if recipe was found
            recipe_found = bool(answer and len(answer.strip()) > 50)
            
            response = {
                "recipe_found": recipe_found,
                "recipe_name": recipe_info.get("recipe_name") or dish_name,
                "answer": answer,
                "ingredients": recipe_info.get("ingredients", []),
                "instructions": recipe_info.get("instructions", []),
                "confidence": recipe_info.get("confidence_score", 0.5),
                "sources": [
                    {
                        "content": (
                            getattr(doc, 'page_content', str(doc))[:200] + "..." 
                            if len(getattr(doc, 'page_content', str(doc))) > 200 
                            else getattr(doc, 'page_content', str(doc))
                        ),
                        "metadata": getattr(doc, 'metadata', {})
                    }
                    for doc in source_documents[:3]  # Limit to top 3 sources
                ],
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "language": language,
                "query_used": query
            }
            
            # Validate response
            validated_response = self._validate_retrieval_result(response)
            
            logger.info(f"Recipe search completed for '{dish_name}': "
                       f"found={validated_response['recipe_found']}, "
                       f"confidence={validated_response['confidence']:.2f}, "
                       f"time={processing_time:.2f}s")
            
            # Record success metrics
            obs_manager.record_metric("rag_service_search", 1.0, {
                "success": "true",
                "recipe_found": str(validated_response['recipe_found']),
                "confidence_bucket": self._get_confidence_bucket(validated_response['confidence']),
                "language": language
            })
            
            obs_manager.record_metric("rag_service_processing_time", processing_time, {
                "operation": "search_recipe"
            })
            
            return validated_response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error searching recipe for '{dish_name}': {e}")
            
            # Record error metrics
            obs_manager.record_metric("rag_service_search", 1.0, {
                "success": "false",
                "error": "search_failed"
            })
            
            return {
                "recipe_found": False,
                "recipe_name": dish_name,
                "answer": f"申し訳ございませんが、'{dish_name}'のレシピを見つけることができませんでした。",
                "ingredients": [],
                "instructions": [],
                "confidence": 0.0,
                "sources": [],
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "language": language
            }
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for metrics."""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        elif confidence >= 0.4:
            return "low"
        else:
            return "very_low"
    
    @trace_function("rag_service_test_connection")
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Knowledge Base."""
        try:
            if not self.is_available():
                return {
                    "success": False,
                    "error": "RAG service not available",
                    "details": {
                        "langchain_available": LANGCHAIN_AVAILABLE,
                        "knowledge_base_id": bool(settings.KNOWLEDGE_BASE_ID),
                        "s3_bucket": bool(settings.S3_BUCKET_NAME),
                        "initialized": self._is_initialized
                    }
                }
            
            # Test with a simple query
            test_result = self.search_recipe("テスト")
            
            return {
                "success": True,
                "message": "Knowledge Base connection successful",
                "test_query_time": test_result.get("processing_time", 0.0),
                "details": {
                    "langchain_available": LANGCHAIN_AVAILABLE,
                    "knowledge_base_id": settings.KNOWLEDGE_BASE_ID,
                    "s3_bucket": settings.S3_BUCKET_NAME,
                    "initialized": self._is_initialized
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "langchain_available": LANGCHAIN_AVAILABLE,
                    "knowledge_base_id": bool(settings.KNOWLEDGE_BASE_ID),
                    "s3_bucket": bool(settings.S3_BUCKET_NAME),
                    "initialized": self._is_initialized
                }
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the RAG service."""
        return {
            "service_name": "RAGService",
            "langchain_available": LANGCHAIN_AVAILABLE,
            "knowledge_base_id": settings.KNOWLEDGE_BASE_ID,
            "s3_bucket": settings.S3_BUCKET_NAME,
            "is_available": self.is_available(),
            "is_initialized": self._is_initialized,
            "retriever_configured": self.retriever is not None,
            "qa_chain_configured": self.qa_chain is not None,
            "supported_languages": ["ja", "en", "auto"],
            "max_results": 5,
            "search_type": "HYBRID",
            "pdf_format": self.pdf_format_info
        }
    
    def list_available_recipes(self) -> Dict[str, Any]:
        """List available recipes in the knowledge base (if supported)."""
        try:
            if not self.is_available():
                return {
                    "success": False,
                    "error": "RAG service not available",
                    "recipes": []
                }
            
            # This is a conceptual implementation
            # In practice, you would need to implement this based on your S3 structure
            logger.info("Listing available recipes not fully implemented - requires S3 bucket enumeration")
            
            return {
                "success": True,
                "message": "Recipe listing requires S3 bucket enumeration",
                "recipes": [],
                "note": "This feature requires additional implementation for S3 bucket listing"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recipes": []
            }
    
    def suggest_similar_recipes(self, dish_name: str, max_suggestions: int = 3) -> Dict[str, Any]:
        """Suggest similar recipes based on dish name."""
        try:
            if not self.is_available():
                return {
                    "success": False,
                    "error": "RAG service not available",
                    "suggestions": []
                }
            
            # Create a similarity search query
            similarity_query = f"{dish_name}に似た料理や代替レシピを提案してください"
            
            # Use retriever directly for similarity search
            similar_docs = self.retriever.get_relevant_documents(similarity_query)
            
            suggestions = []
            for doc in similar_docs[:max_suggestions]:
                content = getattr(doc, 'page_content', str(doc))
                suggestions.append({
                    "content": content[:150] + "..." if len(content) > 150 else content,
                    "metadata": getattr(doc, 'metadata', {}),
                    "relevance_score": 0.5  # Placeholder - actual scoring would require more complex implementation
                })
            
            return {
                "success": True,
                "original_dish": dish_name,
                "suggestions": suggestions,
                "count": len(suggestions)
            }
            
        except Exception as e:
            logger.error(f"Error suggesting similar recipes for '{dish_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "suggestions": []
            }