#!/usr/bin/env python3
"""
Example demonstrating how to use domain schema with the KAG-LangGraph pipeline.

This example shows how to:
1. Use a custom domain schema file
2. Configure the LLM extractor with the schema
3. Run the pipeline with domain-specific entity extraction
"""

import json
import requests
import os
from pathlib import Path

# Server configuration
SERVER_URL = "http://localhost:8000"

def create_domain_config():
    """Create a configuration that uses the domain schema."""
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
                        "api_key": os.getenv("OPENAI_API_KEY", "your-api-key-here"),
                        "temperature": 0.1,
                        "max_tokens": 2000,
                        "extraction_schema": "./test_domain.schema"
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
                        "output_path": "./output/domain_knowledge_graph.json",
                        "pretty_print": True,
                        "include_metadata": True
                    }
                }
            }
        }
    }

def create_sample_document():
    """Create a sample document for testing."""
    sample_content = """
    Dr. John Smith is a renowned researcher at Stanford University, specializing in artificial intelligence and machine learning.
    He has published numerous papers on natural language processing and computer vision.
    
    Stanford University, located in California, is one of the leading research institutions in the world.
    The university was founded in 1885 and has produced many notable alumni including tech entrepreneurs and Nobel Prize winners.
    
    Dr. Smith's recent work focuses on developing new algorithms for medical image analysis, particularly in the field of radiology.
    His research has potential applications in early cancer detection and treatment planning.
    
    The research is funded by the National Science Foundation and involves collaboration with several medical institutions,
    including Johns Hopkins Hospital and Mayo Clinic.
    """
    
    # Create a temporary file
    temp_file = Path("sample_document.txt")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(sample_content)
    
    return str(temp_file)

def test_domain_extraction():
    """Test the domain schema extraction."""
    print("Testing domain schema extraction...")
    
    # Create sample document
    document_path = create_sample_document()
    
    try:
        # Create configuration with domain schema
        config = create_domain_config()
        
        # Run pipeline with domain schema
        response = requests.post(
            f"{SERVER_URL}/pipeline/run",
            json={
                "input_path": document_path,
                "config": config,
                "output_path": "./output/domain_test_output.json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Domain extraction successful!")
            print(f"  Pipeline ID: {result['pipeline_id']}")
            print(f"  Status: {result['status']}")
            print(f"  Output: {result.get('output_path', 'N/A')}")
            
            # Check if output file exists and show some results
            output_path = result.get('output_path')
            if output_path and os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    output_data = json.load(f)
                
                print(f"\n  Results Summary:")
                if 'subgraphs' in output_data:
                    total_entities = sum(len(sg.get('nodes', [])) for sg in output_data['subgraphs'])
                    total_relations = sum(len(sg.get('edges', [])) for sg in output_data['subgraphs'])
                    print(f"    Total entities extracted: {total_entities}")
                    print(f"    Total relationships extracted: {total_relations}")
                    
                    # Show some example entities
                    if output_data['subgraphs']:
                        first_subgraph = output_data['subgraphs'][0]
                        if 'nodes' in first_subgraph and first_subgraph['nodes']:
                            print(f"    Example entities:")
                            for node in first_subgraph['nodes'][:3]:  # Show first 3
                                print(f"      - {node.get('name', 'N/A')} ({node.get('type', 'N/A')})")
            
            return True
        else:
            print(f"✗ Domain extraction failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Domain extraction error: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(document_path):
            os.remove(document_path)

def test_schema_content_extraction():
    """Test extraction with schema content directly."""
    print("\nTesting schema content extraction...")
    
    # Create sample document
    document_path = create_sample_document()
    
    # Define schema content directly
    schema_content = """namespace DomainKG

Person(人物): EntityType
     properties:
        name(姓名): Text
            index: TextAndVector

Organization(组织): EntityType
     properties:
        name(名称): Text
            index: TextAndVector

GeographicLocation(地理位置): EntityType
     properties:
        name(名称): Text
            index: TextAndVector
"""
    
    try:
        config = create_domain_config()
        # Replace schema file with content
        config["pipeline"]["components"]["extractor"]["config"]["extraction_schema"] = schema_content
        
        response = requests.post(
            f"{SERVER_URL}/pipeline/run",
            json={
                "input_path": document_path,
                "config": config,
                "output_path": "./output/schema_content_test.json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Schema content extraction successful!")
            print(f"  Pipeline ID: {result['pipeline_id']}")
            return True
        else:
            print(f"✗ Schema content extraction failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Schema content extraction error: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(document_path):
            os.remove(document_path)

def main():
    """Run domain schema examples."""
    print("=" * 60)
    print("Domain Schema Integration Example")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not running. Please start the server first:")
            print("   uv run python sever.py")
            return 1
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   uv run python sever.py")
        return 1
    
    print("✓ Server is running")
    
    # Check if schema file exists
    if not os.path.exists("./test_domain.schema"):
        print("❌ Domain schema file not found: ./test_domain.schema")
        print("   Please make sure the schema file exists")
        return 1
    
    print("✓ Domain schema file found")
    
    # Run tests
    tests = [
        test_domain_extraction,
        test_schema_content_extraction
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 60)
    
    if passed == len(tests):
        print("🎉 All domain schema tests passed!")
        print("\nYou can now use domain schemas in your pipeline configurations!")
        return 0
    else:
        print("❌ Some tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    exit(main())
