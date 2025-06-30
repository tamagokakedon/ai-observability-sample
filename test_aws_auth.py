#!/usr/bin/env python3
"""Test AWS authentication and services."""

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_aws_credentials():
    """Test AWS credentials."""
    print("🔐 Testing AWS Credentials")
    print("=" * 30)
    
    try:
        # Test STS (Security Token Service) to verify credentials
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ AWS Authentication successful!")
        print(f"   Account: {identity.get('Account', 'Unknown')}")
        print(f"   User/Role: {identity.get('Arn', 'Unknown')}")
        return True
        
    except NoCredentialsError:
        print("❌ No AWS credentials found")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ AWS Authentication failed: {error_code}")
        print(f"   Error: {error_message}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_bedrock_access():
    """Test Bedrock service access."""
    print(f"\n🤖 Testing Bedrock Access")
    print("=" * 25)
    
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Try to list foundation models (this should work with minimal permissions)
        bedrock_general = boto3.client('bedrock', region_name='us-east-1')
        models = bedrock_general.list_foundation_models()
        
        print(f"✅ Bedrock access successful!")
        print(f"   Available models: {len(models.get('modelSummaries', []))}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ Bedrock access failed: {error_code}")
        print(f"   Error: {error_message}")
        
        if error_code == 'UnrecognizedClientException':
            print("   💡 This usually means invalid AWS credentials")
        elif error_code == 'AccessDeniedException':
            print("   💡 This means valid credentials but insufficient permissions")
            
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_knowledge_base_access():
    """Test Knowledge Base access."""
    print(f"\n📚 Testing Knowledge Base Access")
    print("=" * 35)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        kb_id = os.getenv('KNOWLEDGE_BASE_ID')
        if not kb_id or kb_id == 'your_knowledge_base_id_here':
            print("❌ Knowledge Base ID not configured")
            print("   Please set KNOWLEDGE_BASE_ID in .env file")
            return False
        
        # Test Knowledge Base access
        bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        
        # Try a simple retrieve operation
        response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': 'test query'
            }
        )
        
        print(f"✅ Knowledge Base access successful!")
        print(f"   Knowledge Base ID: {kb_id}")
        print(f"   Retrieved results: {len(response.get('retrievalResults', []))}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ Knowledge Base access failed: {error_code}")
        print(f"   Error: {error_message}")
        
        if error_code == 'UnrecognizedClientException':
            print("   💡 This usually means invalid AWS credentials")
        elif error_code == 'ResourceNotFoundException':
            print("   💡 Knowledge Base ID not found - check KNOWLEDGE_BASE_ID setting")
        elif error_code == 'AccessDeniedException':
            print("   💡 Valid credentials but insufficient permissions for Knowledge Base")
            
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_s3_access():
    """Test S3 bucket access."""
    print(f"\n📦 Testing S3 Bucket Access")
    print("=" * 28)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if not bucket_name or bucket_name == 'your_recipe_bucket_here':
            print("❌ S3 bucket name not configured")
            print("   Please set S3_BUCKET_NAME in .env file")
            return False
        
        s3 = boto3.client('s3')
        
        # Try to list objects in the bucket
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
        
        objects = response.get('Contents', [])
        print(f"✅ S3 bucket access successful!")
        print(f"   Bucket: {bucket_name}")
        print(f"   Objects found: {len(objects)}")
        
        # Look for chickensote.pdf specifically
        chickensote_found = False
        for obj in objects:
            key = obj['Key']
            print(f"   • {key}")
            if 'chickensote' in key.lower():
                chickensote_found = True
                print(f"     ⭐ Found chickensote-related file!")
        
        if not chickensote_found:
            print(f"   ⚠️  chickensote.pdf not found in bucket")
            
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ S3 access failed: {error_code}")
        print(f"   Error: {error_message}")
        
        if error_code == 'NoSuchBucket':
            print("   💡 Bucket does not exist - check S3_BUCKET_NAME setting")
        elif error_code == 'AccessDenied':
            print("   💡 Valid credentials but insufficient permissions for S3")
            
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 AWS Authentication and Services Test")
    print("=" * 45)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    print(f"\n📋 Environment Variables:")
    print(f"   AWS_ACCESS_KEY_ID: {'SET' if os.getenv('AWS_ACCESS_KEY_ID') else 'NOT SET'}")
    print(f"   AWS_SECRET_ACCESS_KEY: {'SET' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
    print(f"   AWS_DEFAULT_REGION: {os.getenv('AWS_DEFAULT_REGION', 'NOT SET')}")
    print(f"   KNOWLEDGE_BASE_ID: {os.getenv('KNOWLEDGE_BASE_ID', 'NOT SET')}")
    print(f"   S3_BUCKET_NAME: {os.getenv('S3_BUCKET_NAME', 'NOT SET')}")
    
    # Run tests
    tests = [
        ("AWS Credentials", test_aws_credentials),
        ("Bedrock Access", test_bedrock_access),
        ("Knowledge Base Access", test_knowledge_base_access),
        ("S3 Bucket Access", test_s3_access)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n" + "=" * 45)
    print("📊 TEST SUMMARY")
    print("=" * 45)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"\n🎉 All tests passed! AWS setup is working correctly.")
        print(f"The RAG service should now be able to search chickensote.pdf")
    else:
        print(f"\n⚠️  {total_count - success_count}/{total_count} tests failed.")
        print(f"\n🔧 Next Steps:")
        if not results[0][1]:  # AWS Credentials failed
            print(f"   1. Set valid AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        if not results[2][1]:  # Knowledge Base failed
            print(f"   2. Set correct KNOWLEDGE_BASE_ID in .env")
        if not results[3][1]:  # S3 failed
            print(f"   3. Set correct S3_BUCKET_NAME and ensure chickensote.pdf exists")

if __name__ == "__main__":
    main()