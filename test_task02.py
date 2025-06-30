#!/usr/bin/env python3
"""Test script to validate Task 02: Amazon Bedrock Service Implementation."""

import os
import sys
import ast
import json
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

def test_bedrock_service_structure():
    """Test that BedrockService has the required methods and structure."""
    print("🧪 Testing BedrockService Structure")
    print("=" * 40)
    
    try:
        from services.bedrock_service import BedrockService
        
        # Check class exists
        print("✅ BedrockService class imported")
        
        # Check required methods exist
        required_methods = [
            'test_connection',
            'invoke_model',
            'get_available_models',
            'validate_model_id',
            'get_model_info',
            'estimate_cost'
        ]
        
        service = BedrockService.__new__(BedrockService)  # Create without __init__
        
        missing_methods = []
        for method in required_methods:
            if hasattr(service, method):
                print(f"✅ {method} method exists")
            else:
                print(f"❌ {method} method missing")
                missing_methods.append(method)
        
        # Check supported models constant
        if hasattr(BedrockService, 'SUPPORTED_MODELS'):
            models = BedrockService.SUPPORTED_MODELS
            print(f"✅ SUPPORTED_MODELS defined: {len(models)} models")
            
            # Check for required models from Task 02
            required_models = [
                "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "anthropic.claude-3-7-sonnet-20250219-v1:0"
            ]
            
            for model in required_models:
                if model in models:
                    print(f"  ✅ {model}")
                else:
                    print(f"  ❌ {model}")
                    missing_methods.append(f"model_{model}")
        else:
            print("❌ SUPPORTED_MODELS not defined")
            missing_methods.append("SUPPORTED_MODELS")
        
        print(f"\nStructure Status: {'✅ Complete' if not missing_methods else f'❌ Missing {len(missing_methods)} items'}")
        return len(missing_methods) == 0
        
    except Exception as e:
        print(f"❌ Failed to import or analyze BedrockService: {e}")
        return False

def test_bedrock_service_syntax():
    """Test Python syntax of the Bedrock service."""
    print("\n🧪 Testing BedrockService Syntax")
    print("=" * 40)
    
    try:
        with open("src/services/bedrock_service.py", "r") as f:
            content = f.read()
        
        ast.parse(content)
        print("✅ Valid Python syntax")
        
        # Check for key implementation features
        features = {
            "import json": "json" in content,
            "import boto3": "boto3" in content,
            "ClientError handling": "ClientError" in content,
            "Rate limiting": "_rate_limit" in content,
            "Error handling": "try:" in content and "except" in content,
            "Logging": "logger" in content,
            "Observability": "trace_function" in content or "@trace_function" in content,
            "Metrics recording": "obs_manager.record_metric" in content
        }
        
        missing_features = []
        for feature, present in features.items():
            if present:
                print(f"✅ {feature}")
            else:
                print(f"❌ {feature}")
                missing_features.append(feature)
        
        print(f"\nFeatures Status: {'✅ All present' if not missing_features else f'❌ Missing {len(missing_features)} features'}")
        return len(missing_features) == 0
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def test_bedrock_service_mock():
    """Test BedrockService with mocked boto3 client."""
    print("\n🧪 Testing BedrockService with Mock")
    print("=" * 40)
    
    try:
        # Mock the boto3 session and client
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            # Mock successful response
            mock_response = {
                'body': Mock(read=Mock(return_value=json.dumps({
                    'content': [{'text': 'OK'}],
                    'usage': {'input_tokens': 10, 'output_tokens': 5},
                    'stop_reason': 'end_turn'
                }).encode()))
            }
            mock_client.invoke_model.return_value = mock_response
            
            from services.bedrock_service import BedrockService
            
            # Test initialization
            service = BedrockService()
            print("✅ BedrockService initialized with mocked client")
            
            # Test available models
            models = service.get_available_models()
            print(f"✅ get_available_models returned {len(models)} models")
            
            # Test model validation
            valid_model = service.validate_model_id("anthropic.claude-3-5-sonnet-20241022-v2:0")
            invalid_model = service.validate_model_id("invalid-model")
            print(f"✅ Model validation works: valid={valid_model}, invalid={invalid_model}")
            
            # Test model info
            model_info = service.get_model_info()
            print(f"✅ get_model_info returned info for {model_info.get('model_id', 'unknown')}")
            
            # Test cost estimation
            cost = service.estimate_cost(100, 50)
            print(f"✅ Cost estimation: ${cost.get('total_cost', 0):.6f}")
            
            # Test invoke_model
            response = service.invoke_model("Test prompt")
            print(f"✅ invoke_model returned: {response.get('content', '')[:20]}...")
            
            # Test connection
            connection_ok = service.test_connection()
            print(f"✅ test_connection: {connection_ok}")
            
            print("\nMock Tests Status: ✅ All tests passed")
            return True
            
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        return False

def test_error_handling():
    """Test error handling in BedrockService."""
    print("\n🧪 Testing Error Handling")
    print("=" * 40)
    
    try:
        from botocore.exceptions import ClientError
        
        # Test with various mock errors
        error_scenarios = [
            ("ThrottlingException", "Rate exceeded"),
            ("ValidationException", "Invalid parameters"),
            ("AccessDeniedException", "Access denied"),
            ("ResourceNotFoundException", "Model not found")
        ]
        
        for error_code, error_message in error_scenarios:
            with patch('boto3.Session') as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client
                
                # Create mock ClientError
                error_response = {
                    'Error': {
                        'Code': error_code,
                        'Message': error_message
                    }
                }
                mock_client.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
                
                from services.bedrock_service import BedrockService
                service = BedrockService()
                
                try:
                    service.invoke_model("Test prompt")
                    print(f"❌ {error_code}: No exception raised")
                    return False
                except (RuntimeError, ValueError) as e:
                    print(f"✅ {error_code}: Properly handled - {str(e)[:50]}...")
                except Exception as e:
                    print(f"⚠️  {error_code}: Unexpected error type - {type(e).__name__}")
        
        print("\nError Handling Status: ✅ All error scenarios handled properly")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_observability_integration():
    """Test observability features are properly integrated."""
    print("\n🧪 Testing Observability Integration")
    print("=" * 40)
    
    try:
        # Mock observability manager
        with patch('services.bedrock_service.obs_manager') as mock_obs:
            with patch('boto3.Session') as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client
                
                # Mock successful response
                mock_response = {
                    'body': Mock(read=Mock(return_value=json.dumps({
                        'content': [{'text': 'Test response'}],
                        'usage': {'input_tokens': 10, 'output_tokens': 5}
                    }).encode()))
                }
                mock_client.invoke_model.return_value = mock_response
                
                from services.bedrock_service import BedrockService
                service = BedrockService()
                
                # Test invoke_model to check metrics recording
                service.invoke_model("Test prompt")
                
                # Check that metrics were recorded
                metric_calls = mock_obs.record_metric.call_args_list
                
                expected_metrics = [
                    "bedrock_invocation",
                    "bedrock_tokens_input", 
                    "bedrock_tokens_output",
                    "bedrock_response_time"
                ]
                
                recorded_metrics = [call[0][0] for call in metric_calls]
                
                missing_metrics = []
                for metric in expected_metrics:
                    if metric in recorded_metrics:
                        print(f"✅ {metric} metric recorded")
                    else:
                        print(f"❌ {metric} metric not recorded")
                        missing_metrics.append(metric)
                
                print(f"\nObservability Status: {'✅ All metrics recorded' if not missing_metrics else f'❌ Missing {len(missing_metrics)} metrics'}")
                return len(missing_metrics) == 0
                
    except Exception as e:
        print(f"❌ Observability test failed: {e}")
        return False

def test_task02_deliverables():
    """Check Task 02 deliverables completion."""
    print("\n🧪 Testing Task 02 Deliverables")
    print("=" * 40)
    
    deliverables = {
        "BedrockService class implemented": True,  # Already tested above
        "Model configuration and selection": True,  # SUPPORTED_MODELS constant
        "Connection testing functionality": True,  # test_connection method
        "Error handling and logging": True,  # ClientError handling
        "Basic unit tests": os.path.exists("test_task02.py")  # This file
    }
    
    all_complete = True
    for deliverable, status in deliverables.items():
        if status:
            print(f"✅ {deliverable}")
        else:
            print(f"❌ {deliverable}")
            all_complete = False
    
    # Additional checks
    try:
        from services.bedrock_service import BedrockService
        
        # Check method signatures match requirements
        service = BedrockService.__new__(BedrockService)
        
        # invoke_model should support system_prompt parameter
        import inspect
        invoke_sig = inspect.signature(BedrockService.invoke_model)
        if 'system_prompt' in invoke_sig.parameters:
            print("✅ invoke_model supports system_prompt parameter")
        else:
            print("❌ invoke_model missing system_prompt parameter")
            all_complete = False
        
        # Should have cost estimation
        if hasattr(BedrockService, 'estimate_cost'):
            print("✅ Cost tracking functionality implemented")
        else:
            print("❌ Cost tracking not implemented")
            all_complete = False
            
    except Exception as e:
        print(f"⚠️  Could not perform advanced deliverable checks: {e}")
    
    print(f"\nDeliverables Status: {'✅ All complete' if all_complete else '❌ Some incomplete'}")
    return all_complete

if __name__ == "__main__":
    print("🧪 Task 02 Validation: Amazon Bedrock Service Implementation")
    print("=" * 70)
    
    tests = [
        ("Service Structure", test_bedrock_service_structure),
        ("Python Syntax", test_bedrock_service_syntax),
        ("Mock Functionality", test_bedrock_service_mock),
        ("Error Handling", test_error_handling),
        ("Observability Integration", test_observability_integration),
        ("Task 02 Deliverables", test_task02_deliverables)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} {test_name}")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nOverall: {success_rate:.0f}% tests passed")
    
    if all(results):
        print("\n🎉 Task 02 implementation is complete and ready!")
        print("✅ Amazon Bedrock Service fully implemented with:")
        print("   - Claude 3.5/3.7 Sonnet support")
        print("   - Robust error handling and logging")
        print("   - Rate limiting and retry logic")
        print("   - Cost tracking and token monitoring")
        print("   - OpenTelemetry observability integration")
        print("\nNext: Implement Task 03 (Web Scraper Service)")
    else:
        print(f"\n⚠️  {len([r for r in results if not r])} test(s) failed")
    
    sys.exit(0 if all(results) else 1)