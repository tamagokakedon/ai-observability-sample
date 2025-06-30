"""Configuration utilities and helpers."""

import logging
import os
from typing import Dict, Any
try:
    from ..settings import settings
except ImportError:
    # Direct import when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from settings import settings


def setup_logging() -> None:
    """Configure logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def validate_aws_config() -> Dict[str, Any]:
    """Validate AWS configuration."""
    config_status = {
        "aws_configured": False,
        "bedrock_configured": False,
        "knowledge_base_configured": False,
        "issues": []
    }
    
    # Check AWS credentials
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        config_status["aws_configured"] = True
    elif not (os.getenv("AWS_PROFILE") or os.path.exists(os.path.expanduser("~/.aws/credentials"))):
        config_status["issues"].append("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or configure AWS CLI.")
    else:
        config_status["aws_configured"] = True
    
    # Check Bedrock configuration
    if settings.BEDROCK_MODEL_ID:
        config_status["bedrock_configured"] = True
    else:
        config_status["issues"].append("BEDROCK_MODEL_ID not configured.")
    
    # Check Knowledge Base configuration
    if settings.KNOWLEDGE_BASE_ID and settings.S3_BUCKET_NAME:
        config_status["knowledge_base_configured"] = True
    else:
        config_status["issues"].append("Knowledge Base not configured. Set KNOWLEDGE_BASE_ID and S3_BUCKET_NAME for RAG functionality.")
    
    return config_status


def get_app_info() -> Dict[str, Any]:
    """Get application information."""
    return {
        "service_name": settings.OTEL_SERVICE_NAME,
        "model_id": settings.BEDROCK_MODEL_ID,
        "region": settings.AWS_DEFAULT_REGION,
        "debug_mode": settings.DEBUG,
        "cache_ttl": settings.CACHE_TTL_SECONDS,
        "scraper_delay": settings.WEB_SCRAPER_DELAY
    }