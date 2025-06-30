"""Amazon Bedrock service for AI model interactions."""

import json
import logging
import time
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError

try:
    from ..settings import settings
    from ..utils.observability import trace_function, obs_manager
except ImportError:
    # Direct import when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from settings import settings
    from utils.observability import trace_function, obs_manager

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for interacting with Amazon Bedrock AI models."""
    
    # Supported Claude models
    SUPPORTED_MODELS = [
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-7-sonnet-20250219-v1:0"
    ]
    
    def __init__(self):
        """Initialize the Bedrock service."""
        self.client = None
        self.session = None
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimum 100ms between requests
        
        # Initialize client
        self._initialize_client()
        
        logger.info(f"BedrockService initialized with model: {settings.BEDROCK_MODEL_ID}")
    
    def _initialize_client(self) -> None:
        """Initialize the Bedrock runtime client with proper error handling."""
        try:
            # Create session with credentials
            session_kwargs = {
                "region_name": settings.AWS_DEFAULT_REGION
            }
            
            # Add explicit credentials if provided
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                session_kwargs.update({
                    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY
                })
            
            self.session = boto3.Session(**session_kwargs)
            
            # Create Bedrock runtime client
            self.client = self.session.client(
                "bedrock-runtime",
                config=boto3.session.Config(
                    read_timeout=60,
                    connect_timeout=10,
                    retries={'max_attempts': 3, 'mode': 'adaptive'}
                )
            )
            
            logger.info("Bedrock client initialized successfully")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise RuntimeError("AWS credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise RuntimeError(f"Failed to initialize Bedrock client: {str(e)}")
    
    def _rate_limit(self) -> None:
        """Implement rate limiting to avoid throttling."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @trace_function("bedrock_connection_test")
    def test_connection(self) -> bool:
        """Test the connection to Bedrock service."""
        if not self.client:
            logger.error("Bedrock client not initialized")
            obs_manager.record_metric("bedrock_connection_test", 1.0, {"success": "false", "error": "no_client"})
            return False
        
        try:
            logger.info("Testing Bedrock connection...")
            
            # Use a simple test prompt
            response = self.invoke_model(
                prompt="Hello, please respond with just 'OK'.",
                max_tokens=10,
                temperature=0.0
            )
            
            # Check if response contains expected content
            success = "OK" in response.get("content", "").upper()
            
            if success:
                logger.info("Bedrock connection test successful")
                obs_manager.record_metric("bedrock_connection_test", 1.0, {"success": "true"})
            else:
                logger.warning(f"Bedrock connection test unexpected response: {response.get('content', '')}")
                obs_manager.record_metric("bedrock_connection_test", 1.0, {"success": "false", "error": "unexpected_response"})
            
            return success
            
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {e}")
            obs_manager.record_metric("bedrock_connection_test", 1.0, {"success": "false", "error": str(type(e).__name__)})
            return False
    
    @trace_function("bedrock_model_invocation")
    def invoke_model(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke a Bedrock model with the given prompt.
        
        Args:
            prompt: The input prompt for the model
            max_tokens: Maximum tokens to generate (default from settings)
            temperature: Sampling temperature (default from settings)
            model_id: Model ID to use (default from settings)
            system_prompt: Optional system prompt for the model
            
        Returns:
            Dictionary with model response containing content, usage, etc.
        """
        if not self.client:
            raise RuntimeError("Bedrock client not initialized")
        
        # Use provided values or fall back to settings
        model_id = model_id or settings.BEDROCK_MODEL_ID
        max_tokens = max_tokens or settings.BEDROCK_MAX_TOKENS
        temperature = temperature or settings.BEDROCK_TEMPERATURE
        
        # Validate model ID
        if model_id not in self.SUPPORTED_MODELS:
            logger.warning(f"Model {model_id} not in supported models list: {self.SUPPORTED_MODELS}")
        
        # Apply rate limiting
        self._rate_limit()
        
        # Prepare request body for Claude models
        if "anthropic.claude" in model_id:
            messages = [{"role": "user", "content": prompt}]
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            
            # Add system prompt if provided
            if system_prompt:
                body["system"] = system_prompt
        else:
            # Fallback for other models (if any)
            body = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        
        try:
            logger.info(f"Invoking model {model_id} with prompt length: {len(prompt)} chars")
            logger.debug(f"Request parameters: max_tokens={max_tokens}, temperature={temperature}")
            
            start_time = time.time()
            
            # Make the API call
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_time = time.time() - start_time
            response_body = json.loads(response["body"].read())
            
            # Parse response based on model type
            if "anthropic.claude" in model_id:
                content = response_body.get("content", [{}])[0].get("text", "")
                usage = response_body.get("usage", {})
                
                result = {
                    "content": content,
                    "model_id": model_id,
                    "usage": {
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    },
                    "response_time": response_time,
                    "stop_reason": response_body.get("stop_reason"),
                    "stop_sequence": response_body.get("stop_sequence")
                }
            else:
                # Fallback parsing for other models
                result = {
                    "content": response_body.get("completion", ""),
                    "model_id": model_id,
                    "usage": response_body.get("usage", {}),
                    "response_time": response_time
                }
            
            # Log successful invocation
            logger.info(
                f"Model invocation successful - "
                f"Input tokens: {result['usage'].get('input_tokens', 0)}, "
                f"Output tokens: {result['usage'].get('output_tokens', 0)}, "
                f"Response time: {response_time:.2f}s"
            )
            
            # Record metrics
            obs_manager.record_metric("bedrock_invocation", 1.0, {
                "model": model_id, 
                "success": "true"
            })
            obs_manager.record_metric("bedrock_tokens_input", result['usage'].get('input_tokens', 0), {
                "model": model_id
            })
            obs_manager.record_metric("bedrock_tokens_output", result['usage'].get('output_tokens', 0), {
                "model": model_id
            })
            obs_manager.record_metric("bedrock_response_time", response_time, {
                "model": model_id
            })
            
            return result
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            
            logger.error(f"Bedrock ClientError {error_code}: {error_message}")
            
            # Record error metrics
            obs_manager.record_metric("bedrock_invocation", 1.0, {
                "model": model_id, 
                "success": "false", 
                "error": error_code
            })
            
            # Provide user-friendly error messages
            if error_code == "ThrottlingException":
                raise RuntimeError("Rate limit exceeded. Please try again later.")
            elif error_code == "ValidationException":
                raise ValueError(f"Invalid request parameters: {error_message}")
            elif error_code == "AccessDeniedException":
                raise RuntimeError("Access denied. Please check your AWS permissions for Bedrock.")
            elif error_code == "ResourceNotFoundException":
                raise RuntimeError(f"Model {model_id} not found or not available in region {settings.AWS_DEFAULT_REGION}")
            else:
                raise RuntimeError(f"Bedrock API error ({error_code}): {error_message}")
                
        except BotoCoreError as e:
            logger.error(f"Bedrock BotoCoreError: {e}")
            obs_manager.record_metric("bedrock_invocation", 1.0, {
                "model": model_id, 
                "success": "false", 
                "error": "network"
            })
            raise RuntimeError("Network error connecting to Bedrock service")
            
        except Exception as e:
            logger.error(f"Unexpected error invoking model: {e}")
            obs_manager.record_metric("bedrock_invocation", 1.0, {
                "model": model_id, 
                "success": "false", 
                "error": "unknown"
            })
            raise RuntimeError(f"Failed to invoke model: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        """Get list of supported Claude models."""
        return self.SUPPORTED_MODELS.copy()
    
    def validate_model_id(self, model_id: str) -> bool:
        """Validate if a model ID is supported."""
        return model_id in self.SUPPORTED_MODELS
    
    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a model."""
        model_id = model_id or settings.BEDROCK_MODEL_ID
        
        model_info = {
            "model_id": model_id,
            "is_supported": self.validate_model_id(model_id),
            "max_tokens": settings.BEDROCK_MAX_TOKENS,
            "temperature": settings.BEDROCK_TEMPERATURE,
            "region": settings.AWS_DEFAULT_REGION
        }
        
        # Add model-specific information
        if "claude-3-5" in model_id:
            model_info.update({
                "family": "Claude 3.5",
                "context_window": 200000,
                "description": "Fast and capable model for complex reasoning"
            })
        elif "claude-3-7" in model_id:
            model_info.update({
                "family": "Claude 3.7", 
                "context_window": 200000,
                "description": "Latest Claude model with enhanced capabilities"
            })
        
        return model_info
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, model_id: Optional[str] = None) -> Dict[str, float]:
        """
        Estimate cost for token usage (approximate pricing).
        Note: Pricing may vary by region and time. Check AWS pricing for accurate costs.
        """
        model_id = model_id or settings.BEDROCK_MODEL_ID
        
        # Approximate pricing (USD per 1K tokens) - these are estimates
        pricing = {
            "anthropic.claude-3-5-sonnet-20240620-v1:0": {"input": 0.003, "output": 0.015},
            "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 0.003, "output": 0.015},
            "anthropic.claude-3-7-sonnet-20250219-v1:0": {"input": 0.003, "output": 0.015}  # Estimated
        }
        
        model_pricing = pricing.get(model_id, {"input": 0.003, "output": 0.015})
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "currency": "USD",
            "model_id": model_id,
            "note": "Estimated pricing - check AWS for current rates"
        }