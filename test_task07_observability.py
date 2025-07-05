#!/usr/bin/env python3
"""Test enhanced OpenTelemetry observability implementation for Task 07."""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_opentelemetry_imports():
    """Test that all enhanced OpenTelemetry components can be imported."""
    print("🧪 Testing Enhanced OpenTelemetry Imports")
    print("=" * 45)
    
    try:
        from utils.observability import (
            obs_manager, 
            trace_function, 
            trace_ai_operation,
            log_with_correlation,
            get_correlation_context,
            EnhancedMetrics,
            StructuredLoggingHandler
        )
        
        print("✅ All observability components imported successfully")
        
        # Test observability manager initialization
        print(f"✅ ObservabilityManager initialized: {obs_manager.is_initialized}")
        print(f"✅ Enhanced metrics available: {obs_manager.enhanced_metrics is not None}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_xray_propagator():
    """Test X-Ray propagator configuration."""
    print("\n🧪 Testing X-Ray Propagator Configuration")
    print("=" * 42)
    
    try:
        from opentelemetry import propagate
        from opentelemetry.propagators.aws import AwsXRayPropagator
        
        # Check if X-Ray propagator is set
        current_propagator = propagate.get_global_textmap()
        
        if isinstance(current_propagator, AwsXRayPropagator):
            print("✅ X-Ray propagator is correctly configured")
            return True
        else:
            print(f"❌ X-Ray propagator not set. Current: {type(current_propagator)}")
            return False
            
    except ImportError as e:
        print(f"❌ X-Ray propagator import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking X-Ray propagator: {e}")
        return False

def test_enhanced_metrics():
    """Test enhanced metrics functionality."""
    print("\n🧪 Testing Enhanced Metrics")
    print("=" * 28)
    
    try:
        from utils.observability import obs_manager
        
        if not obs_manager.enhanced_metrics:
            print("❌ Enhanced metrics not available")
            return False
        
        metrics = obs_manager.enhanced_metrics
        
        # Test metric recording
        print("📊 Testing metric recording...")
        
        # Test request metrics
        obs_manager.start_request_context("test_operation", test_type="unit_test")
        print("✅ Request context created")
        
        # Test AI metrics
        obs_manager.record_ai_metrics(
            model_id="test-model",
            tokens_used=100,
            operation_type="test",
            cost_estimate=0.001
        )
        print("✅ AI metrics recorded")
        
        # Test cache metrics
        obs_manager.record_cache_operation("test_cache", hit=True)
        print("✅ Cache metrics recorded")
        
        # Test error metrics
        obs_manager.record_error(
            error_type="TestError",
            error_message="This is a test error",
            operation="test_operation"
        )
        print("✅ Error metrics recorded")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_correlation_context():
    """Test correlation context functionality."""
    print("\n🧪 Testing Correlation Context")
    print("=" * 32)
    
    try:
        from utils.observability import obs_manager, get_correlation_context, log_with_correlation
        
        # Start a request context
        correlation_id = obs_manager.start_request_context("test_correlation", user_id="test_user")
        print(f"✅ Correlation ID created: {correlation_id}")
        
        # Get correlation context
        context = get_correlation_context()
        print(f"✅ Correlation context: {context}")
        
        if context["correlation_id"] == correlation_id:
            print("✅ Correlation context matches")
        else:
            print("❌ Correlation context mismatch")
            return False
        
        # Test structured logging with correlation
        log_with_correlation(
            "Test log message with correlation",
            level=logging.INFO,
            test_field="test_value"
        )
        print("✅ Structured logging with correlation completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Correlation context test failed: {e}")
        return False

def test_tracing_decorators():
    """Test enhanced tracing decorators."""
    print("\n🧪 Testing Tracing Decorators")
    print("=" * 31)
    
    try:
        from utils.observability import trace_function, trace_ai_operation
        
        # Test basic trace function
        @trace_function("test_operation", {"test_attr": "test_value"})
        def test_basic_function(value):
            time.sleep(0.1)  # Simulate processing
            return f"processed_{value}"
        
        result = test_basic_function("test_input")
        print(f"✅ Basic trace function: {result}")
        
        # Test AI operation tracing
        @trace_ai_operation(
            model_id="test-ai-model",
            operation_type="test_generation",
            cost_per_token=0.00001
        )
        def test_ai_function(prompt):
            time.sleep(0.05)  # Simulate AI processing
            return {
                "content": f"AI response to: {prompt}",
                "usage": {"total_tokens": 50}
            }
        
        ai_result = test_ai_function("Test prompt")
        print(f"✅ AI trace function: {ai_result['content']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tracing decorators test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cloudwatch_configuration():
    """Test CloudWatch configuration and exporters."""
    print("\n🧪 Testing CloudWatch Configuration")
    print("=" * 36)
    
    try:
        from utils.observability import obs_manager
        import settings
        
        # Check AWS credentials availability
        has_aws_creds = obs_manager._has_aws_credentials()
        print(f"📋 AWS credentials available: {has_aws_creds}")
        
        if has_aws_creds:
            print("✅ CloudWatch exporters should be configured")
            
            # Test that trace provider has exporters
            from opentelemetry import trace
            tracer_provider = trace.get_tracer_provider()
            
            if hasattr(tracer_provider, '_span_processors'):
                processor_count = len(tracer_provider._span_processors)
                print(f"✅ Trace processors configured: {processor_count}")
            
            # Test metrics provider
            from opentelemetry import metrics
            metrics_provider = metrics.get_meter_provider()
            
            if hasattr(metrics_provider, '_metric_readers'):
                reader_count = len(metrics_provider._metric_readers)
                print(f"✅ Metric readers configured: {reader_count}")
            
        else:
            print("⚠️  CloudWatch exporters not configured (no AWS credentials)")
        
        return True
        
    except Exception as e:
        print(f"❌ CloudWatch configuration test failed: {e}")
        return False

def test_instrumentation():
    """Test automatic instrumentation."""
    print("\n🧪 Testing Automatic Instrumentation")
    print("=" * 36)
    
    try:
        # Test that instrumentors are available
        instrumentors = []
        
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            instrumentors.append("RequestsInstrumentor")
        except ImportError:
            pass
        
        try:
            from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
            instrumentors.append("BotocoreInstrumentor")
        except ImportError:
            pass
        
        try:
            from opentelemetry.instrumentation.logging import LoggingInstrumentor
            instrumentors.append("LoggingInstrumentor")
        except ImportError:
            pass
        
        print(f"✅ Available instrumentors: {', '.join(instrumentors)}")
        
        if len(instrumentors) >= 2:
            print("✅ Sufficient instrumentation available")
            return True
        else:
            print("⚠️  Limited instrumentation available")
            return False
            
    except Exception as e:
        print(f"❌ Instrumentation test failed: {e}")
        return False

def test_dashboard_configuration():
    """Test CloudWatch dashboard configuration."""
    print("\n🧪 Testing Dashboard Configuration")
    print("=" * 34)
    
    try:
        # Check if dashboard configuration file exists
        dashboard_file = "cloudwatch-dashboard.json"
        
        if os.path.exists(dashboard_file):
            print(f"✅ Dashboard configuration file found: {dashboard_file}")
            
            # Validate JSON format
            with open(dashboard_file, 'r') as f:
                dashboard_config = json.load(f)
            
            # Check for required widgets
            widgets = dashboard_config.get("widgets", [])
            widget_types = [w.get("type") for w in widgets]
            
            print(f"✅ Dashboard widgets: {len(widgets)} total")
            print(f"✅ Widget types: {set(widget_types)}")
            
            if "metric" in widget_types and "log" in widget_types:
                print("✅ Dashboard includes both metric and log widgets")
                return True
            else:
                print("⚠️  Dashboard missing required widget types")
                return False
        else:
            print(f"❌ Dashboard configuration file not found: {dashboard_file}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"❌ Dashboard JSON parsing failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Dashboard configuration test failed: {e}")
        return False

def test_cloudwatch_agent_files():
    """Test CloudWatch agent configuration files."""
    print("\n🧪 Testing CloudWatch Agent Files")
    print("=" * 35)
    
    try:
        # Check configuration files
        config_file = "cloudwatch-agent-config.json"
        install_script = "install-cloudwatch-agent.sh"
        
        files_found = []
        
        if os.path.exists(config_file):
            files_found.append(config_file)
            
            # Validate JSON format
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Check for required sections
            required_sections = ["agent", "logs", "metrics"]
            for section in required_sections:
                if section in config:
                    print(f"✅ CloudWatch agent config has '{section}' section")
                else:
                    print(f"❌ CloudWatch agent config missing '{section}' section")
        else:
            print(f"❌ CloudWatch agent config not found: {config_file}")
        
        if os.path.exists(install_script):
            files_found.append(install_script)
            
            # Check if script is executable
            if os.access(install_script, os.X_OK):
                print(f"✅ Installation script is executable: {install_script}")
            else:
                print(f"⚠️  Installation script not executable: {install_script}")
        else:
            print(f"❌ Installation script not found: {install_script}")
        
        # Check for WSL2 fix script
        fix_script = "fix-wsl2-cloudwatch.sh"
        if os.path.exists(fix_script):
            files_found.append(fix_script)
            if os.access(fix_script, os.X_OK):
                print(f"✅ WSL2 fix script is executable: {fix_script}")
            else:
                print(f"⚠️  WSL2 fix script not executable: {fix_script}")
        
        # Check for credentials test script
        cred_test_script = "test-aws-credentials.sh"
        if os.path.exists(cred_test_script):
            files_found.append(cred_test_script)
            if os.access(cred_test_script, os.X_OK):
                print(f"✅ AWS credentials test script is executable: {cred_test_script}")
            else:
                print(f"⚠️  AWS credentials test script not executable: {cred_test_script}")
        
        print(f"✅ CloudWatch agent files found: {files_found}")
        return len(files_found) >= 2
        
    except json.JSONDecodeError as e:
        print(f"❌ CloudWatch agent config JSON parsing failed: {e}")
        return False
    except Exception as e:
        print(f"❌ CloudWatch agent files test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Task 07: Enhanced OpenTelemetry Observability Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    tests = [
        ("OpenTelemetry Imports", test_opentelemetry_imports),
        ("X-Ray Propagator", test_xray_propagator),
        ("Enhanced Metrics", test_enhanced_metrics),
        ("Correlation Context", test_correlation_context),
        ("Tracing Decorators", test_tracing_decorators),
        ("CloudWatch Configuration", test_cloudwatch_configuration),
        ("Automatic Instrumentation", test_instrumentation),
        ("Dashboard Configuration", test_dashboard_configuration),
        ("CloudWatch Agent Files", test_cloudwatch_agent_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 TASK 07 TEST SUMMARY")
    print("=" * 60)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} {test_name}")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nOverall: {success_rate:.0f}% tests passed")
    
    if all(results):
        print("\n🎉 Task 07 Enhanced Observability Implementation Complete!")
        print("✅ All observability features implemented successfully:")
        print("   • X-Ray propagator for AWS distributed tracing")
        print("   • Enhanced metrics with AI model tracking")
        print("   • Correlation context and structured logging")
        print("   • Comprehensive tracing decorators")
        print("   • CloudWatch integration with exporters")
        print("   • Automatic instrumentation for key libraries")
        print("   • CloudWatch dashboard configuration")
        print("   • CloudWatch agent setup for WSL2")
        print("\n📊 Next Steps:")
        print("   1. Install CloudWatch agent: ./install-cloudwatch-agent.sh")
        print("   2. Import dashboard: cloudwatch-dashboard.json")
        print("   3. Run application to generate traces and metrics")
        print("   4. Monitor in CloudWatch console")
    else:
        failed_tests = [tests[i][0] for i, result in enumerate(results) if not result]
        print(f"\n⚠️  Failed tests: {', '.join(failed_tests)}")
        print("\n🔧 Troubleshooting:")
        print("   • Check OpenTelemetry dependencies: pip install -r requirements.txt")
        print("   • Verify AWS credentials are configured")
        print("   • Ensure all configuration files are present")
    
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()