#!/usr/bin/env python3
"""
Test script for the KAG-LangGraph Pipeline Server.

This script tests the various endpoints of the server to ensure they work correctly.
"""

import requests
import json
import time
import tempfile
import os
from pathlib import Path

# Server configuration
SERVER_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed: {data['status']}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Make sure it's running.")
        return False
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return False

def test_get_config():
    """Test getting the default configuration."""
    print("Testing get config...")
    try:
        response = requests.get(f"{SERVER_URL}/pipeline/config")
        if response.status_code == 200:
            data = response.json()
            print("✓ Config retrieved successfully")
            print(f"  Components: {list(data['config']['pipeline']['components'].keys())}")
            return True
        else:
            print(f"✗ Get config failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Get config error: {e}")
        return False

def test_list_components():
    """Test listing available components."""
    print("Testing list components...")
    try:
        response = requests.get(f"{SERVER_URL}/pipeline/components")
        if response.status_code == 200:
            data = response.json()
            print("✓ Components listed successfully")
            print(f"  Total components: {data['total_components']}")
            return True
        else:
            print(f"✗ List components failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ List components error: {e}")
        return False

def create_test_file():
    """Create a temporary test file."""
    test_content = """
    This is a test document for the KAG-LangGraph pipeline.
    
    It contains some sample text with an email address: test@example.com
    And a phone number: (555) 123-4567
    
    The pipeline should extract entities and relationships from this text.
    """
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_file.write(test_content)
    temp_file.close()
    
    return temp_file.name

def test_run_pipeline():
    """Test running the pipeline synchronously."""
    print("Testing pipeline run...")
    
    # Create test file
    test_file = create_test_file()
    
    try:
        # Test basic pipeline run
        response = requests.post(
            f"{SERVER_URL}/pipeline/run",
            json={
                "input_path": test_file,
                "output_path": "./output/test_output.json"
            },
            timeout=60  # Give it time to process
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Pipeline run successful")
            print(f"  Pipeline ID: {data['pipeline_id']}")
            print(f"  Status: {data['status']}")
            print(f"  Output path: {data.get('output_path', 'N/A')}")
            return True
        else:
            print(f"✗ Pipeline run failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Pipeline run error: {e}")
        return False
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass

def test_upload_and_run():
    """Test uploading a file and running the pipeline."""
    print("Testing upload and run...")
    
    # Create test file
    test_file = create_test_file()
    
    try:
        with open(test_file, 'rb') as f:
            response = requests.post(
                f"{SERVER_URL}/pipeline/upload-and-run",
                files={"file": f},
                timeout=60
            )
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Upload and run successful")
            print(f"  Pipeline ID: {data['pipeline_id']}")
            print(f"  Status: {data['status']}")
            return True
        else:
            print(f"✗ Upload and run failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Upload and run error: {e}")
        return False
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass

def test_stream_pipeline():
    """Test streaming pipeline execution."""
    print("Testing pipeline streaming...")
    
    # Create test file
    test_file = create_test_file()
    
    try:
        response = requests.post(
            f"{SERVER_URL}/pipeline/stream",
            json={"input_path": test_file},
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            print("✓ Pipeline streaming started")
            
            # Read a few updates
            updates_received = 0
            for line in response.iter_lines():
                if line and updates_received < 5:  # Limit to avoid hanging
                    if line.startswith(b'data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            print(f"  Update: {data.get('current_component', 'unknown')} - {data.get('status', 'unknown')}")
                            updates_received += 1
                        except json.JSONDecodeError:
                            pass
                elif updates_received >= 5:
                    break
            
            print("✓ Pipeline streaming completed")
            return True
        else:
            print(f"✗ Pipeline streaming failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Pipeline streaming error: {e}")
        return False
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass

def main():
    """Run all tests."""
    print("=" * 50)
    print("KAG-LangGraph Pipeline Server Test Suite")
    print("=" * 50)
    
    tests = [
        test_health_check,
        test_get_config,
        test_list_components,
        test_run_pipeline,
        test_upload_and_run,
        test_stream_pipeline
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print()
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
        
        time.sleep(1)  # Brief pause between tests
    
    print()
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the server logs for details.")
        return 1

if __name__ == "__main__":
    exit(main())
