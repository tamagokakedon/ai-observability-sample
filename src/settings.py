"""Application settings and configuration."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application configuration settings."""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", 
        "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    BEDROCK_MAX_TOKENS: int = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))
    BEDROCK_TEMPERATURE: float = float(os.getenv("BEDROCK_TEMPERATURE", "0.1"))
    
    # Knowledge Base Configuration
    KNOWLEDGE_BASE_ID: Optional[str] = os.getenv("KNOWLEDGE_BASE_ID")
    S3_BUCKET_NAME: Optional[str] = os.getenv("S3_BUCKET_NAME")
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    WEB_SCRAPER_DELAY: float = float(os.getenv("WEB_SCRAPER_DELAY", "1.0"))
    
    # OpenTelemetry Configuration
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "ai-recipe-analyzer")
    OTEL_EXPORTER_CLOUDWATCH_REGION: str = os.getenv(
        "OTEL_EXPORTER_CLOUDWATCH_REGION", "us-east-1"
    )


# Global settings instance
settings = Settings()