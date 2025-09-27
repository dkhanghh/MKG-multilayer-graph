#!/usr/bin/env python3
"""
Test script for using the sample.schema file with the server.
This demonstrates end-to-end usage of domain schema parsing.
"""

import json
import requests
import os
import time
from pathlib import Path

# Server configuration
SERVER_URL = "http://localhost:8000"

def create_sample_schema_config():
    """Create a configuration that uses the sample.schema file."""
    return {
        "pipeline": {
            "components": {
                "scanner": {
                    "type": "file_scanner",
                    "enabled": True
                },
                "reader": {
                    "type": "pdf_reader",
                    "enabled": True
                },
                "splitter": {
                    "type": "semantic_splitter",
                    "enabled": True,
                    "config": {
                        "chunk_size": 1000,
                        "chunk_overlap": 100
                    }
                },
                "extractor": {
                    "type": "llm_extractor",
                    "enabled": True,
                    "config": {
                        "llm_provider": "openai",
                        "model": "gpt-3.5-turbo",
                        "api_key": os.getenv("OPENAI_API_KEY", "test-api-key"),
                        "temperature": 0.1,
                        "max_tokens": 2000,
                        "extraction_schema": "./kag_langgraph/schema/sample.schema"
                    }
                },
                "vectorizer": {
                    "type": "no_op_vectorizer",
                    "enabled": True
                },
                "writer": {
                    "type": "json_writer",
                    "enabled": True,
                    "config": {
                        "output_path": "./output/sample_schema_test.json",
                        "pretty_print": True,
                        "include_metadata": True
                    }
                }
            }
        }
    }

def create_test_document():
    """Create a test document with content that matches our schema entities."""
    content = """
    Research Paper: Advances in Artificial Intelligence and Machine Learning
    
    Dr. Sarah Johnson, a leading researcher at MIT, has published groundbreaking work on 
    artificial neural networks. Her research focuses on developing new algorithms for 
    natural language processing and computer vision applications.
    
    MIT (Massachusetts Institute of Technology), located in Cambridge, Massachusetts, 
    is one of the world's premier research institutions. The university was founded in 1861 
    and has been at the forefront of technological innovation for over 150 years.
    
    The research involves collaboration with several organizations including:
    - Google Research (Mountain View, California)
    - Microsoft Research (Redmond, Washington) 
    - Stanford University (Stanford, California)
    
    Key concepts explored in this work include:
    - Deep learning architectures
    - Transformer models
    - Attention mechanisms
    - Transfer learning
    
    The study was conducted from January 2023 to December 2023, with funding from 
    the National Science Foundation. The research has potential applications in 
    medical diagnosis, autonomous vehicles, and robotics.
    
    Important keywords: artificial intelligence, machine learning, neural networks, 
    deep learning, natural language processing, computer vision.
    
    The building where this research takes place is the Ray and Maria Stata Center, 
    a modern architectural marvel designed by Frank Gehry.
    """
    
    # Create output directory if it doesn't exist
    os.makedirs("./output", exist_ok=True)
    
    # Create test file
    test_file = Path("./output/test_document.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(test_file)

def test_server_health():
    """Test if the server is running."""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def test_schema_configuration():
    """Test the server with sample schema configuration."""
    print("Testing sample schema configuration with server...")
    
    # Create test document
    document_path = create_test_document()
    
    try:
        # Create configuration
        config = create_sample_schema_config()
        
        print(f"  Using document: {document_path}")
        print(f"  Using schema: ./kag_langgraph/schema/sample.schema")
        
        # Test the configuration endpoint first
        config_response = requests.post(
            f"{SERVER_URL}/pipeline/config",
            json=config,
            timeout=30
        )
        
        if config_response.status_code == 200:
            print("  ✓ Configuration validated successfully")
        else:
            print(f"  ⚠️  Configuration validation returned: {config_response.status_code}")
        
        # Run the pipeline
        print("  Running pipeline...")
        response = requests.post(
            f"{SERVER_URL}/pipeline/run",
            json={
                "input_path": document_path,
                "config": config,
                "output_path": "./output/sample_schema_result.json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print("  ✓ Pipeline execution successful!")
            print(f"    Pipeline ID: {result.get('pipeline_id', 'N/A')}")
            print(f"    Status: {result.get('status', 'N/A')}")
            print(f"    Output: {result.get('output_path', 'N/A')}")
            
            # Analyze results if available
            output_path = result.get('output_path')
            if output_path and os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                
                print(f"    Results analysis:")
                if 'subgraphs' in output_data:
                    total_entities = sum(len(sg.get('nodes', [])) for sg in output_data['subgraphs'])
                    total_relations = sum(len(sg.get('edges', [])) for sg in output_data['subgraphs'])
                    print(f"      Total entities: {total_entities}")
                    print(f"      Total relationships: {total_relations}")
                    
                    # Show entity types found
                    entity_types = set()
                    for sg in output_data['subgraphs']:
                        for node in sg.get('nodes', []):
                            if 'type' in node:
                                entity_types.add(node['type'])
                    
                    if entity_types:
                        print(f"      Entity types found: {sorted(entity_types)}")
                    
                    # Show some example entities
                    if output_data['subgraphs'] and output_data['subgraphs'][0].get('nodes'):
                        print(f"      Example entities:")
                        for node in output_data['subgraphs'][0]['nodes'][:3]:
                            name = node.get('name', 'N/A')
                            entity_type = node.get('type', 'N/A')
                            print(f"        - {name} ({entity_type})")
            
            return True
        else:
            print(f"  ✗ Pipeline execution failed: {response.status_code}")
            print(f"    Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ Test failed with error: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(document_path):
            os.remove(document_path)

def test_streaming_with_schema():
    """Test streaming execution with sample schema."""
    print("\nTesting streaming execution with sample schema...")
    
    document_path = create_test_document()
    
    try:
        config = create_sample_schema_config()
        
        print("  Starting streaming execution...")
        response = requests.post(
            f"{SERVER_URL}/pipeline/stream",
            json={
                "input_path": document_path,
                "config": config,
                "output_path": "./output/sample_schema_stream.json"
            },
            stream=True,
            timeout=120
        )
        
        if response.status_code == 200:
            print("  ✓ Streaming started successfully")
            
            # Process streaming response
            events_received = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                            events_received += 1
                            
                            if events_received <= 3:  # Show first few events
                                event_type = data.get('type', 'unknown')
                                print(f"    Event {events_received}: {event_type}")
                                
                                if 'data' in data and 'component' in data['data']:
                                    component = data['data']['component']
                                    print(f"      Component: {component}")
                            
                            # Stop after reasonable number of events for testing
                            if events_received >= 10:
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
            print(f"  ✓ Received {events_received} streaming events")
            return True
        else:
            print(f"  ✗ Streaming failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Streaming test failed: {e}")
        return False
    finally:
        if os.path.exists(document_path):
            os.remove(document_path)

def main():
    """Run sample schema server tests."""
    print("=" * 70)
    print("Sample Schema Server Integration Test")
    print("=" * 70)
    
    # Check prerequisites
    if not test_server_health():
        print("❌ Server is not running. Please start the server first:")
        print("   uv run python sever.py")
        return 1
    
    print("✓ Server is running")
    
    # Check if schema file exists
    schema_path = Path("./kag_langgraph/schema/sample.schema")
    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return 1
    
    print(f"✓ Schema file found: {schema_path}")
    
    # Run tests
    tests = [
        test_schema_configuration,
        test_streaming_with_schema
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 70)
    
    if passed == len(tests):
        print("🎉 All sample schema server tests passed!")
        print("\nThe sample.schema file is working perfectly with the server!")
        print("\nYou can now use this schema in your pipeline configurations:")
        print('  "extraction_schema": "./kag_langgraph/schema/sample.schema"')
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())
