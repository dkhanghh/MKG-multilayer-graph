#!/usr/bin/env python3
"""
Test script for domain schema parsing functionality.
"""

import sys
from pathlib import Path

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_graphs.components.extractor import LLMExtractor
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.pipeline_state import PipelineState

def test_schema_parsing():
    """Test the domain schema parsing functionality."""
    print("Testing domain schema parsing...")
    
    # Test configuration with schema file
    config_dict = {
        "llm_provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": "test-key",
        "extraction_schema": "./test_domain.schema"
    }

    try:
        # Create extractor with schema file
        config = ComponentConfig(type="llm_extractor", config=config_dict)
        extractor = LLMExtractor(config)
        
        print(f"✓ Schema file parsed successfully")
        print(f"  Entity types found: {len(extractor.entity_types)}")
        print(f"  Entity types: {extractor.entity_types}")
        
        # Verify expected entity types are present
        expected_entities = [
            "Chunk", "ArtificialObject", "Astronomy", "Building", "Creature",
            "Concept", "Date", "GeographicLocation", "Keyword", "Medicine",
            "NaturalScience", "Organization", "Person", "Others"
        ]
        
        missing_entities = set(expected_entities) - set(extractor.entity_types)
        if missing_entities:
            print(f"  ⚠️  Missing entities: {missing_entities}")
        else:
            print(f"  ✓ All expected entities found")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema parsing failed: {e}")
        return False

def test_schema_content_parsing():
    """Test parsing schema from content string."""
    print("\nTesting schema content parsing...")
    
    schema_content = """namespace DomainKG

Person(人物): EntityType
     properties:
        name(姓名): Text
            index: TextAndVector

Organization(组织): EntityType
     properties:
        name(名称): Text
            index: TextAndVector
"""
    
    config_dict = {
        "llm_provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": "test-key",
        "extraction_schema": schema_content
    }

    try:
        config = ComponentConfig(type="llm_extractor", config=config_dict)
        extractor = LLMExtractor(config)
        
        print(f"✓ Schema content parsed successfully")
        print(f"  Entity types: {extractor.entity_types}")
        
        expected = ["Person", "Organization"]
        if set(expected).issubset(set(extractor.entity_types)):
            print(f"  ✓ Expected entities found")
        else:
            print(f"  ⚠️  Some expected entities missing")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema content parsing failed: {e}")
        return False

def test_default_behavior():
    """Test that default behavior still works."""
    print("\nTesting default behavior...")
    
    config_dict = {
        "llm_provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": "test-key"
    }

    try:
        config = ComponentConfig(type="llm_extractor", config=config_dict)
        extractor = LLMExtractor(config)
        
        print(f"✓ Default configuration works")
        print(f"  Default entity types: {extractor.entity_types}")
        
        return True
        
    except Exception as e:
        print(f"✗ Default configuration failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Domain Schema Parsing Test Suite")
    print("=" * 60)
    
    tests = [
        test_schema_parsing,
        test_schema_content_parsing,
        test_default_behavior
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())
