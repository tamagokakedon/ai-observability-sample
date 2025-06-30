#!/usr/bin/env python3
"""Test RAG service connection and Knowledge Base functionality."""

import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment_setup():
    """Test environment variables and configuration."""
    print("🔧 Testing Environment Setup")
    print("=" * 40)
    
    required_env_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 
        'AWS_DEFAULT_REGION',
        'KNOWLEDGE_BASE_ID',
        'S3_BUCKET_NAME',
        'BEDROCK_MODEL_ID'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            # Hide sensitive values
            if 'KEY' in var or 'SECRET' in var:
                display_value = f"{'*' * (len(value) - 4)}{value[-4:]}" if len(value) > 4 else "****"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment configuration.")
        return False
    
    return True

def test_rag_service_init():
    """Test RAG service initialization."""
    print("\n🧪 Testing RAG Service Initialization")
    print("=" * 45)
    
    try:
        from services.rag_service import RAGService
        
        # Initialize service
        rag_service = RAGService()
        
        # Get service info
        service_info = rag_service.get_service_info()
        
        print(f"✅ RAGService initialized successfully")
        print(f"📊 Service Info:")
        for key, value in service_info.items():
            print(f"   • {key}: {value}")
        
        return rag_service, service_info
        
    except Exception as e:
        print(f"❌ Failed to initialize RAGService: {e}")
        return None, None

def test_knowledge_base_connection(rag_service):
    """Test Knowledge Base connection."""
    print("\n🔗 Testing Knowledge Base Connection")
    print("=" * 40)
    
    try:
        if not rag_service:
            print("❌ RAG service not available")
            return False
        
        # Test connection
        connection_result = rag_service.test_connection()
        
        print(f"Connection Result:")
        for key, value in connection_result.items():
            print(f"   • {key}: {value}")
        
        if connection_result.get('success'):
            print("✅ Knowledge Base connection successful")
            return True
        else:
            print("❌ Knowledge Base connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False

def test_recipe_search(rag_service):
    """Test recipe search functionality."""
    print("\n🔍 Testing Recipe Search")
    print("=" * 30)
    
    if not rag_service:
        print("❌ RAG service not available")
        return False
    
    test_queries = ["chickensote", "チキンソテー", "chicken", "テスト"]
    
    for query in test_queries:
        print(f"\n🔎 Searching for: '{query}'")
        try:
            result = rag_service.search_recipe(query)
            
            print(f"   Recipe Found: {result.get('recipe_found', False)}")
            print(f"   Confidence: {result.get('confidence', 0):.2f}")
            print(f"   Answer: {result.get('answer', '')[:100]}...")
            print(f"   Sources: {len(result.get('sources', []))} documents")
            print(f"   Processing Time: {result.get('processing_time', 0):.2f}s")
            
            if result.get('error'):
                print(f"   ⚠️  Error: {result['error']}")
                
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
    
    return True

def test_bedrock_service():
    """Test Bedrock service separately."""
    print("\n🤖 Testing Bedrock Service")
    print("=" * 30)
    
    try:
        from services.bedrock_service import BedrockService
        
        bedrock_service = BedrockService()
        
        # Test simple prompt
        test_prompt = "これはテストです。'test successful'と回答してください。"
        
        response = bedrock_service.invoke_model(
            prompt=test_prompt,
            max_tokens=100,
            temperature=0.1
        )
        
        print(f"✅ Bedrock service working")
        print(f"📝 Test response: {str(response)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Bedrock service failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 RAG Service Connection Test")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Test 1: Environment setup
    env_ok = test_environment_setup()
    
    # Test 2: Bedrock service
    bedrock_ok = test_bedrock_service()
    
    # Test 3: RAG service initialization
    rag_service, service_info = test_rag_service_init()
    
    # Test 4: Knowledge Base connection
    if rag_service:
        kb_ok = test_knowledge_base_connection(rag_service)
        
        # Test 5: Recipe search
        if kb_ok:
            search_ok = test_recipe_search(rag_service)
        else:
            print("\n⚠️  Skipping recipe search test due to connection failure")
            search_ok = False
    else:
        print("\n⚠️  Skipping connection and search tests due to initialization failure")
        kb_ok = False
        search_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Environment Setup: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Bedrock Service: {'✅ PASS' if bedrock_ok else '❌ FAIL'}")
    print(f"RAG Service Init: {'✅ PASS' if rag_service else '❌ FAIL'}")
    print(f"Knowledge Base: {'✅ PASS' if kb_ok else '❌ FAIL'}")
    print(f"Recipe Search: {'✅ PASS' if search_ok else '❌ FAIL'}")
    
    if all([env_ok, bedrock_ok, rag_service, kb_ok, search_ok]):
        print("\n🎉 All tests passed! RAG system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        
        # Provide troubleshooting suggestions
        print("\n🔧 Troubleshooting Suggestions:")
        if not env_ok:
            print("   • Check your .env file configuration")
            print("   • Ensure all required AWS credentials are set")
        if not bedrock_ok:
            print("   • Verify AWS Bedrock access and model permissions")
            print("   • Check AWS region configuration")
        if not rag_service:
            print("   • Check LangChain installation")
            print("   • Verify Python dependencies")
        if not kb_ok:
            print("   • Verify Knowledge Base ID is correct")
            print("   • Check S3 bucket access permissions")
            print("   • Ensure Knowledge Base is properly indexed")
        if not search_ok:
            print("   • Check if PDFs are properly indexed in Knowledge Base")
            print("   • Verify PDF content is searchable")

if __name__ == "__main__":
    main()