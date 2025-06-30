#!/usr/bin/env python3
"""Debug RAG search functionality in detail."""

import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging to see more details
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def debug_rag_search():
    """Debug RAG search step by step."""
    print("🔍 Debugging RAG Search for 'chickensote'")
    print("=" * 50)
    
    try:
        # Import services
        from services.rag_service import RAGService
        from services.bedrock_service import BedrockService
        import settings
        
        print(f"✅ Successfully imported services")
        
        # Check settings
        print(f"\n📋 Current Settings:")
        print(f"   KNOWLEDGE_BASE_ID: {getattr(settings, 'KNOWLEDGE_BASE_ID', 'Not set')}")
        print(f"   S3_BUCKET_NAME: {getattr(settings, 'S3_BUCKET_NAME', 'Not set')}")
        print(f"   AWS_DEFAULT_REGION: {getattr(settings, 'AWS_DEFAULT_REGION', 'Not set')}")
        print(f"   BEDROCK_MODEL_ID: {getattr(settings, 'BEDROCK_MODEL_ID', 'Not set')}")
        
        # Initialize RAG service
        print(f"\n🔧 Initializing RAG Service...")
        rag_service = RAGService()
        
        # Check service availability
        is_available = rag_service.is_available()
        print(f"   RAG Service Available: {is_available}")
        
        service_info = rag_service.get_service_info()
        print(f"   LangChain Available: {service_info.get('langchain_available')}")
        print(f"   Retriever Configured: {service_info.get('retriever_configured')}")
        print(f"   QA Chain Configured: {service_info.get('qa_chain_configured')}")
        
        if not is_available:
            print(f"❌ RAG service is not available. Cannot proceed with search.")
            
            # Test connection details
            connection_result = rag_service.test_connection()
            print(f"\n🔗 Connection Test Details:")
            for key, value in connection_result.items():
                print(f"   {key}: {value}")
            return
        
        # Test search with multiple variations
        search_terms = ["chickensote", "チキンソテー", "chicken sote", "chicken"]
        
        for term in search_terms:
            print(f"\n🔎 Testing search for: '{term}'")
            print("-" * 30)
            
            try:
                result = rag_service.search_recipe(term)
                
                print(f"   Recipe Found: {result.get('recipe_found', False)}")
                print(f"   Confidence: {result.get('confidence', 0):.3f}")
                print(f"   Recipe Name: {result.get('recipe_name', 'N/A')}")
                print(f"   Answer Length: {len(result.get('answer', ''))}")
                print(f"   Sources Count: {len(result.get('sources', []))}")
                print(f"   Processing Time: {result.get('processing_time', 0):.2f}s")
                print(f"   Query Used: {result.get('query_used', 'N/A')}")
                
                # Show partial answer
                answer = result.get('answer', '')
                if answer:
                    print(f"   Answer Preview: {answer[:100]}...")
                
                # Show source details
                sources = result.get('sources', [])
                if sources:
                    print(f"   📚 Source Details:")
                    for i, source in enumerate(sources[:2], 1):  # Show first 2 sources
                        content = source.get('content', '')
                        metadata = source.get('metadata', {})
                        print(f"      Source {i}:")
                        print(f"        Content Length: {len(content)}")
                        print(f"        Content Preview: {content[:100]}...")
                        print(f"        Metadata: {metadata}")
                else:
                    print(f"   ⚠️ No sources returned from Knowledge Base")
                
                if result.get('error'):
                    print(f"   ❌ Error: {result['error']}")
                    
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()

def test_bedrock_directly():
    """Test Bedrock service directly."""
    print(f"\n🤖 Testing Bedrock Service Directly")
    print("=" * 40)
    
    try:
        from services.bedrock_service import BedrockService
        
        bedrock = BedrockService()
        
        # Test simple query
        test_prompt = """以下の情報を基に、chickensoteという料理について教えてください。

情報がない場合は「情報が見つかりません」と回答してください。
シンプルに回答してください。"""
        
        response = bedrock.invoke_model(
            prompt=test_prompt,
            max_tokens=200,
            temperature=0.1
        )
        
        print(f"✅ Bedrock response received")
        print(f"   Response type: {type(response)}")
        print(f"   Response: {response}")
        
    except Exception as e:
        print(f"❌ Bedrock test failed: {e}")
        import traceback
        traceback.print_exc()

def test_knowledge_base_retriever():
    """Test Knowledge Base retriever directly if available."""
    print(f"\n📚 Testing Knowledge Base Retriever Directly")
    print("=" * 45)
    
    try:
        import settings
        from langchain_community.retrievers import AmazonKnowledgeBasesRetriever
        
        if not settings.KNOWLEDGE_BASE_ID or settings.KNOWLEDGE_BASE_ID == "your_knowledge_base_id_here":
            print("❌ Knowledge Base ID not properly configured")
            return
        
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=settings.KNOWLEDGE_BASE_ID,
            retrieval_config={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3,
                    "overrideSearchType": "HYBRID"
                }
            },
            region_name=settings.AWS_DEFAULT_REGION
        )
        
        # Test direct retrieval
        test_queries = ["chickensote", "chicken", "チキンソテー"]
        
        for query in test_queries:
            print(f"\n🔍 Direct retrieval for: '{query}'")
            try:
                docs = retriever.get_relevant_documents(query)
                print(f"   Retrieved documents: {len(docs)}")
                
                for i, doc in enumerate(docs, 1):
                    content = getattr(doc, 'page_content', str(doc))
                    metadata = getattr(doc, 'metadata', {})
                    print(f"   Document {i}:")
                    print(f"     Content length: {len(content)}")
                    print(f"     Content preview: {content[:100]}...")
                    print(f"     Metadata: {metadata}")
                    
            except Exception as e:
                print(f"   ❌ Retrieval failed: {e}")
    
    except Exception as e:
        print(f"❌ Retriever test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🐛 RAG Search Debug Tool")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test 1: Bedrock service
    test_bedrock_directly()
    
    # Test 2: Knowledge Base retriever
    test_knowledge_base_retriever()
    
    # Test 3: RAG service search
    debug_rag_search()
    
    print(f"\n🏁 Debug complete")