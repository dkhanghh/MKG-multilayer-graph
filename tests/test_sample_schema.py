#!/usr/bin/env python3
"""
Test script for parsing the sample.schema file from kag_langgraph/schema/sample.schema
"""

import sys
from pathlib import Path

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_graphs.components.extractor import LLMExtractor
from knowledge_graphs.components.base import ComponentConfig

def test_sample_schema_parsing():
    """Test parsing the sample.schema file."""
    print("Testing sample.schema file parsing...")
    
    schema_path = "./kag_langgraph/schema/sample.schema"
    
    # Test configuration with the sample schema file
    config_dict = {
        "llm_provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": "test-key",
        "extraction_schema": schema_path
    }
    
    try:
        # Create extractor with schema file
        config = ComponentConfig(type="llm_extractor", config=config_dict)
        extractor = LLMExtractor(config)
        
        print(f"✓ Sample schema file parsed successfully")
        print(f"  Schema file: {schema_path}")
        print(f"  Entity types found: {len(extractor.entity_types)}")
        print(f"  Entity types: {extractor.entity_types}")
        
        # Verify expected entity types are present
        expected_entities = [
            "Chunk", "ArtificialObject", "Astronomy", "Building", "Creature",
            "Concept", "Date", "GeographicLocation", "Keyword", "Medicine",
            "NaturalScience", "Organization", "Person", "Others"
        ]
        
        found_entities = set(extractor.entity_types)
        expected_entities_set = set(expected_entities)
        
        missing_entities = expected_entities_set - found_entities
        extra_entities = found_entities - expected_entities_set
        
        if missing_entities:
            print(f"  ⚠️  Missing entities: {missing_entities}")
        else:
            print(f"  ✓ All expected entities found")
            
        if extra_entities:
            print(f"  ℹ️  Extra entities found: {extra_entities}")
        
        # Test the extraction schema structure
        schema = extractor.extraction_schema
        print(f"\n  Schema structure:")
        print(f"    Type: {schema.get('type', 'N/A')}")
        print(f"    Required fields: {schema.get('required', [])}")
        
        if 'properties' in schema:
            properties = schema['properties']
            print(f"    Properties: {list(properties.keys())}")
            
            # Check entities schema
            if 'entities' in properties:
                entities_schema = properties['entities']
                if 'items' in entities_schema and 'properties' in entities_schema['items']:
                    entity_props = entities_schema['items']['properties']
                    if 'type' in entity_props and 'enum' in entity_props['type']:
                        enum_types = entity_props['type']['enum']
                        print(f"    Entity enum types: {len(enum_types)} types")
                        print(f"    First few types: {enum_types[:5]}")
        
        return True
        
    except Exception as e:
        print(f"✗ Sample schema parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schema_content_direct():
    """Test parsing schema content directly from the file."""
    print("\nTesting direct schema content parsing...")
    
    schema_path = "./kag_langgraph/schema/sample.schema"
    
    try:
        # Read the schema file content
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_content = f.read()
        
        print(f"  Schema file size: {len(schema_content)} characters")
        print(f"  Schema file lines: {len(schema_content.splitlines())} lines")
        
        # Test configuration with schema content
        config_dict = {
            "llm_provider": "openai",
            "model": "gpt-3.5-turbo",
            "api_key": "test-key",
            "extraction_schema": schema_content
        }
        
        config = ComponentConfig(type="llm_extractor", config=config_dict)
        extractor = LLMExtractor(config)
        
        print(f"✓ Schema content parsed successfully")
        print(f"  Entity types found: {len(extractor.entity_types)}")
        print(f"  Entity types: {extractor.entity_types}")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema content parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schema_parsing_details():
    """Test detailed parsing to understand the schema structure."""
    print("\nTesting detailed schema parsing...")
    
    schema_path = "./kag_langgraph/schema/sample.schema"
    
    try:
        # Create a minimal extractor to test the parsing function directly
        config = ComponentConfig(type="llm_extractor", config={"api_key": "test"})
        extractor = LLMExtractor(config)
        
        # Test the parsing function directly
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Call the parsing method directly
        result = extractor._parse_domain_schema_content(content)
        
        print(f"✓ Direct parsing method test")
        print(f"  Parsing result type: {type(result)}")
        print(f"  Parsing result: {result}")
        print(f"  Entity types after parsing: {extractor.entity_types}")
        
        # Analyze the content line by line
        lines = content.strip().split('\n')
        entity_lines = [line for line in lines if line.strip().endswith(': EntityType')]
        
        print(f"\n  Content analysis:")
        print(f"    Total lines: {len(lines)}")
        print(f"    Entity definition lines: {len(entity_lines)}")
        print(f"    Entity definitions found:")
        
        for i, line in enumerate(entity_lines[:5]):  # Show first 5
            line = line.strip()
            entity_full = line.replace(': EntityType', '')
            if '(' in entity_full:
                entity_name = entity_full.split('(')[0]
                chinese_name = entity_full.split('(')[1].rstrip(')')
                print(f"      {i+1}. {entity_name} ({chinese_name})")
            else:
                print(f"      {i+1}. {entity_full}")
        
        if len(entity_lines) > 5:
            print(f"      ... and {len(entity_lines) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"✗ Detailed parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all schema parsing tests."""
    print("=" * 70)
    print("Sample Schema Parsing Test Suite")
    print("=" * 70)
    
    # Check if schema file exists
    schema_path = Path("./kag_langgraph/schema/sample.schema")
    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        print("   Please make sure the file exists")
        return 1
    
    print(f"✓ Schema file found: {schema_path}")
    print(f"  File size: {schema_path.stat().st_size} bytes")
    
    tests = [
        test_sample_schema_parsing,
        test_schema_content_direct,
        test_schema_parsing_details
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("🎉 All schema parsing tests passed!")
        print("\nThe sample.schema file is correctly parsed and ready to use!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())
