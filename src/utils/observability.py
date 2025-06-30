"""OpenTelemetry observability configuration and utilities."""

import os
import logging
from typing import Optional, Dict, Any
from functools import wraps
import time

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.cloudwatch.logs import CloudWatchLogsExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    metrics = None

try:
    from ..settings import settings
except ImportError:
    # Direct import when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from settings import settings

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Manager for OpenTelemetry observability setup."""
    
    def __init__(self):
        """Initialize observability manager."""
        self.tracer = None
        self.meter = None
        self.is_initialized = False
        
        if OTEL_AVAILABLE:
            self._setup_observability()
        else:
            logger.warning("OpenTelemetry not available. Install with: pip install opentelemetry-*")
    
    def _setup_observability(self) -> None:
        """Set up OpenTelemetry providers and exporters."""
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": settings.OTEL_SERVICE_NAME,
                "service.version": "1.0.0",
                "deployment.environment": "development" if settings.DEBUG else "production"
            })
            
            # Set up tracing
            trace_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(trace_provider)
            self.tracer = trace.get_tracer(__name__)
            
            # Set up metrics
            metrics_provider = MeterProvider(resource=resource)
            metrics.set_meter_provider(metrics_provider)
            self.meter = metrics.get_meter(__name__)
            
            # Set up logging (if CloudWatch credentials are available)
            if self._has_aws_credentials():
                self._setup_cloudwatch_logging()
            
            # Auto-instrument common libraries
            RequestsInstrumentor().instrument()
            
            self.is_initialized = True
            logger.info("OpenTelemetry observability initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize observability: {e}")
    
    def _has_aws_credentials(self) -> bool:
        """Check if AWS credentials are available."""
        return bool(
            (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY) or
            os.getenv("AWS_PROFILE") or
            os.path.exists(os.path.expanduser("~/.aws/credentials"))
        )
    
    def _setup_cloudwatch_logging(self) -> None:
        """Set up CloudWatch logging export."""
        try:
            # Create CloudWatch exporter
            cloudwatch_exporter = CloudWatchLogsExporter(
                region_name=settings.OTEL_EXPORTER_CLOUDWATCH_REGION,
                log_group_name=f"/aws/ai-recipe-analyzer/{settings.OTEL_SERVICE_NAME}"
            )
            
            # Set up log provider
            logger_provider = LoggerProvider(resource=Resource.create({
                "service.name": settings.OTEL_SERVICE_NAME
            }))
            
            # Add batch processor
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(cloudwatch_exporter)
            )
            
            # Create handler for Python logging
            handler = LoggingHandler(
                level=logging.INFO,
                logger_provider=logger_provider
            )
            
            # Add to root logger
            logging.getLogger().addHandler(handler)
            
            logger.info("CloudWatch logging configured successfully")
            
        except Exception as e:
            logger.warning(f"CloudWatch logging setup failed: {e}")
    
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a new span for tracing."""
        if not self.is_initialized or not self.tracer:
            return DummySpan()
        
        span = self.tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        return span
    
    def record_metric(self, name: str, value: float, attributes: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        if not self.is_initialized or not self.meter:
            return
        
        try:
            counter = self.meter.create_counter(name)
            counter.add(value, attributes or {})
        except Exception as e:
            logger.debug(f"Failed to record metric {name}: {e}")


class DummySpan:
    """Dummy span for when OpenTelemetry is not available."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        pass
    
    def set_attribute(self, _key: str, _value: Any):
        pass
    
    def set_status(self, _status):
        pass
    
    def end(self):
        pass


# Global observability manager
obs_manager = ObservabilityManager()


def trace_function(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to trace function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with obs_manager.create_span(
                f"{func.__module__}.{func.__name__}",
                attributes or {}
            ) as span:
                span.set_attribute("operation.name", operation_name)
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("operation.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("operation.success", False)
                    span.set_attribute("error.message", str(e))
                    raise
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("operation.duration_ms", duration * 1000)
                    
                    # Record metrics
                    obs_manager.record_metric(
                        f"{operation_name}_duration_seconds",
                        duration,
                        {"function": func.__name__}
                    )
        
        return wrapper
    return decorator


def log_with_correlation(message: str, level: int = logging.INFO, **kwargs):
    """Log message with correlation context."""
    extra_data = {
        "service.name": settings.OTEL_SERVICE_NAME,
        **kwargs
    }
    
    logger.log(level, message, extra=extra_data)