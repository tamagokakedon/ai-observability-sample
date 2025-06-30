#!/usr/bin/env python3
"""Test script to validate Task 01: Project Setup and Dependencies."""

import os
import sys
import ast
from pathlib import Path

def test_project_structure():
    """Test that the project structure matches Task 01 requirements."""
    print("🧪 Testing Project Structure (Task 01)")
    print("=" * 50)
    
    # Required files from Task 01
    required_files = [
        "requirements.txt",
        ".env.example",
        "src/app.py",
        "src/settings.py",
        "src/services/bedrock_service.py",
        "src/services/web_scraper.py", 
        "src/services/recipe_detector.py",
        "src/services/rag_service.py",
        "src/utils/config.py",
        "src/utils/observability.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    # Check __init__.py files
    init_files = [
        "src/services/__init__.py",
        "src/utils/__init__.py"
    ]
    
    for init_file in init_files:
        if os.path.exists(init_file):
            print(f"✅ {init_file}")
        else:
            print(f"❌ {init_file}")
            missing_files.append(init_file)
    
    print(f"\nStructure Status: {'✅ Complete' if not missing_files else f'❌ Missing {len(missing_files)} files'}")
    return len(missing_files) == 0

def test_dependencies():
    """Test that dependencies are properly specified."""
    print("\n🧪 Testing Dependencies")
    print("=" * 30)
    
    required_deps = [
        "streamlit",
        "langchain", 
        "boto3",
        "requests",
        "beautifulsoup4",
        "python-dotenv",
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-exporter-cloudwatch-logs"
    ]
    
    try:
        with open("requirements.txt", "r") as f:
            requirements_content = f.read()
        
        missing_deps = []
        for dep in required_deps:
            if dep in requirements_content:
                print(f"✅ {dep}")
            else:
                print(f"❌ {dep}")
                missing_deps.append(dep)
        
        print(f"\nDependencies Status: {'✅ Complete' if not missing_deps else f'❌ Missing {len(missing_deps)} deps'}")
        return len(missing_deps) == 0
        
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def test_configuration():
    """Test configuration files."""
    print("\n🧪 Testing Configuration")
    print("=" * 30)
    
    # Test .env.example
    if os.path.exists(".env.example"):
        print("✅ .env.example exists")
        with open(".env.example", "r") as f:
            env_content = f.read()
        
        required_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY", 
            "AWS_DEFAULT_REGION",
            "BEDROCK_MODEL_ID",
            "KNOWLEDGE_BASE_ID",
            "S3_BUCKET_NAME"
        ]
        
        missing_vars = []
        for var in required_vars:
            if var in env_content:
                print(f"  ✅ {var}")
            else:
                print(f"  ❌ {var}")
                missing_vars.append(var)
        
        env_status = len(missing_vars) == 0
    else:
        print("❌ .env.example not found")
        env_status = False
    
    return env_status

def test_python_syntax():
    """Test that all Python files have valid syntax."""
    print("\n🧪 Testing Python Syntax")
    print("=" * 30)
    
    python_files = [
        "src/settings.py",
        "src/app.py",
        "src/services/bedrock_service.py",
        "src/services/web_scraper.py",
        "src/services/recipe_detector.py", 
        "src/services/rag_service.py",
        "src/utils/config.py",
        "src/utils/observability.py"
    ]
    
    syntax_errors = []
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    ast.parse(f.read())
                print(f"✅ {file_path}")
            except SyntaxError as e:
                print(f"❌ {file_path}: {e}")
                syntax_errors.append(file_path)
        else:
            print(f"⚠️  {file_path}: File not found")
    
    print(f"\nSyntax Status: {'✅ All valid' if not syntax_errors else f'❌ {len(syntax_errors)} errors'}")
    return len(syntax_errors) == 0

def test_imports():
    """Test basic imports work."""
    print("\n🧪 Testing Basic Imports")
    print("=" * 30)
    
    # Add src to path
    sys.path.insert(0, os.path.join(os.getcwd(), "src"))
    
    try:
        # Test settings import
        import settings
        print("✅ settings module")
        
        # Test utils imports
        from utils.config import setup_logging, validate_aws_config
        print("✅ utils.config module")
        
        from utils.observability import obs_manager
        print("✅ utils.observability module")
        
        # Test service imports
        from services.bedrock_service import BedrockService
        from services.web_scraper import WebScraperService
        from services.recipe_detector import RecipeDetectorService
        from services.rag_service import RAGService
        print("✅ All service modules")
        
        print("\nImport Status: ✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_task01_deliverables():
    """Check Task 01 deliverables from the markdown file."""
    print("\n🧪 Testing Task 01 Deliverables")
    print("=" * 40)
    
    deliverables = {
        "requirements.txt created": os.path.exists("requirements.txt"),
        ".env.example created": os.path.exists(".env.example"),
        "src/ directory structure created": os.path.exists("src") and os.path.isdir("src"),
        "Basic configuration files set up": (
            os.path.exists("src/settings.py") and 
            os.path.exists("src/utils/config.py")
        )
    }
    
    all_complete = True
    for deliverable, status in deliverables.items():
        if status:
            print(f"✅ {deliverable}")
        else:
            print(f"❌ {deliverable}")
            all_complete = False
    
    print(f"\nDeliverables Status: {'✅ All complete' if all_complete else '❌ Some incomplete'}")
    return all_complete

if __name__ == "__main__":
    print("🧪 Task 01 Validation: Project Setup and Dependencies")
    print("=" * 60)
    
    tests = [
        ("Project Structure", test_project_structure),
        ("Dependencies", test_dependencies),
        ("Configuration", test_configuration),
        ("Python Syntax", test_python_syntax),
        ("Basic Imports", test_imports),
        ("Task 01 Deliverables", test_task01_deliverables)
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
    print("📊 SUMMARY")
    print("=" * 60)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} {test_name}")
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nOverall: {success_rate:.0f}% tests passed")
    
    if all(results):
        print("\n🎉 Task 01 implementation is complete and ready!")
        print("Next: Implement Task 02 (Bedrock Service)")
    else:
        print(f"\n⚠️  {len([r for r in results if not r])} test(s) failed")
    
    sys.exit(0 if all(results) else 1)