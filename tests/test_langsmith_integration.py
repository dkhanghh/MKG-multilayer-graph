#!/usr/bin/env python3
"""
Test script for LangSmith integration with the KAG-LangGraph server.
"""

import os
import requests
import json
import time
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not available, using system environment variables")

# Server configuration
SERVER_URL = "http://localhost:8000"

def check_langsmith_config():
    """Check if LangSmith is properly configured."""
    print("Checking LangSmith configuration...")
    
    required_vars = ["LANGSMITH_API_KEY"]
    optional_vars = ["LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT"]
    
    config_status = {}
    
    for var in required_vars:
        value = os.getenv(var)
        config_status[var] = "✓ Set" if value else "✗ Missing"
        if value:
            print(f"  {var}: ✓ Set")
        else:
            print(f"  {var}: ✗ Missing (required)")
    
    for var in optional_vars:
        value = os.getenv(var)
        config_status[var] = f"✓ Set ({value})" if value else "- Default"
        if value:
            print(f"  {var}: ✓ Set ({value})")
        else:
            default_values = {
                "LANGSMITH_PROJECT": "kag-langgraph-server",
                "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com"
            }
            print(f"  {var}: - Using default ({default_values.get(var, 'N/A')})")
    
    # Check if all required variables are set
    all_required_set = all(os.getenv(var) for var in required_vars)
    
    if all_required_set:
        print("✓ LangSmith configuration is complete")
        return True
    else:
        print("⚠️  LangSmith configuration incomplete")
        print("\nTo enable LangSmith tracing, set the following environment variables:")
        print("export LANGSMITH_API_KEY='your-langsmith-api-key'")
        print("export LANGSMITH_PROJECT='kag-langgraph-server'  # optional")
        return False

def test_server_health():
    """Test if the server is running."""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def create_test_document():
    """Create a test document for pipeline execution."""
    content = """
    LangSmith Integration Test Document
    
    This document is used to test the LangSmith tracing integration with the KAG-LangGraph pipeline.
    
    Dr. Alice Johnson is a researcher at OpenAI working on large language models and AI safety.
    She has published several papers on transformer architectures and reinforcement learning from human feedback.
    
    OpenAI, founded in 2015, is an AI research company based in San Francisco, California.
    The company focuses on developing artificial general intelligence (AGI) that benefits humanity.
    
    Key concepts in this research include:
    - Natural language processing
    - Machine learning
    - Artificial intelligence
    - Neural networks
    - Deep learning
    
    The research was conducted from January 2024 to March 2024 with funding from various sources.
    """
    
    # Create output directory
    os.makedirs("./output", exist_ok=True)
    
    # Create test file
    test_file = Path("./output/langsmith_test_document.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(test_file)

def test_traced_pipeline_execution():
    """Test pipeline execution with LangSmith tracing."""
    print("\nTesting traced pipeline execution...")
    
    document_path = create_test_document()
    
    try:
        # Test synchronous execution
        print("  Testing synchronous execution...")
        response = requests.post(
            f"{SERVER_URL}/pipeline/run",
            json={
                "input_path": document_path,
                "output_path": "./output/langsmith_sync_test.json"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"    ✓ Sync execution successful (ID: {result.get('pipeline_id', 'N/A')})")
        else:
            print(f"    ✗ Sync execution failed: {response.status_code}")
            return False
        
        # Test asynchronous execution
        print("  Testing asynchronous execution...")
        response = requests.post(
            f"{SERVER_URL}/pipeline/run-async",
            json={
                "input_path": document_path,
                "output_path": "./output/langsmith_async_test.json"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"    ✓ Async execution successful (ID: {result.get('pipeline_id', 'N/A')})")
        else:
            print(f"    ✗ Async execution failed: {response.status_code}")
            return False
        
        # Test streaming execution
        print("  Testing streaming execution...")
        response = requests.post(
            f"{SERVER_URL}/pipeline/stream",
            json={
                "input_path": document_path,
                "output_path": "./output/langsmith_stream_test.json"
            },
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            events_count = 0
            for line in response.iter_lines():
                if line and line.startswith(b'data: '):
                    events_count += 1
                    if events_count >= 5:  # Stop after a few events
                        break
            print(f"    ✓ Streaming execution successful ({events_count} events received)")
        else:
            print(f"    ✗ Streaming execution failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"    ✗ Pipeline execution test failed: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(document_path):
            os.remove(document_path)

def test_upload_and_run_tracing():
    """Test upload and run with tracing."""
    print("\nTesting upload and run with tracing...")
    
    # Create test content
    test_content = "LangSmith upload test: Dr. Bob Smith works at Google Research on machine learning."
    
    try:
        # Test file upload and execution
        files = {"file": ("test_upload.txt", test_content, "text/plain")}
        response = requests.post(
            f"{SERVER_URL}/pipeline/upload-and-run",
            files=files,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ Upload and run successful (ID: {result.get('pipeline_id', 'N/A')})")
            return True
        else:
            print(f"  ✗ Upload and run failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Upload and run test failed: {e}")
        return False

def check_langsmith_traces():
    """Provide instructions for checking LangSmith traces."""
    print("\nChecking LangSmith traces...")
    
    langsmith_project = os.getenv("LANGSMITH_PROJECT", "kag-langgraph-server")
    
    if os.getenv("LANGSMITH_API_KEY"):
        print(f"  ✓ LangSmith is configured")
        print(f"  📊 View traces at: https://smith.langchain.com/")
        print(f"  📁 Project: {langsmith_project}")
        print(f"  🔍 Look for traces with names:")
        print(f"    - pipeline_run_sync")
        print(f"    - pipeline_run_async") 
        print(f"    - pipeline_stream")
        print(f"    - pipeline_upload_and_run")
        return True
    else:
        print(f"  ⚠️  LangSmith not configured - no traces will be generated")
        return False

def main():
    """Run LangSmith integration tests."""
    print("=" * 70)
    print("LangSmith Integration Test Suite")
    print("=" * 70)
    
    # Check LangSmith configuration
    langsmith_configured = check_langsmith_config()
    
    # Check if server is running
    if not test_server_health():
        print("\n❌ Server is not running. Please start the server first:")
        print("   uv run python sever.py")
        return 1
    
    print("\n✓ Server is running")
    
    # Run tests
    tests = [
        test_traced_pipeline_execution,
        test_upload_and_run_tracing
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
    
    # Check traces
    check_langsmith_traces()
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 70)
    
    if passed == len(tests):
        if langsmith_configured:
            print("🎉 All tests passed! LangSmith tracing is working.")
            print("\n📊 Check your LangSmith dashboard to see the traces:")
            print("   https://smith.langchain.com/")
        else:
            print("✅ All tests passed, but LangSmith is not configured.")
            print("   Set LANGSMITH_API_KEY to enable tracing.")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())
