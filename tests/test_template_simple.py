#!/usr/bin/env python3
"""
Simple test script for Jinja2 template loading functionality.

This script tests the template loader directly without importing the full package.
"""

import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import only the template loader module directly
from knowledge_graphs.utils.template_loader import TemplateLoader


def test_template_loading():
    """Test basic template loading functionality."""
    print("Testing Jinja2 Template Loading")
    print("=" * 40)
    
    # Get template loader
    try:
        loader = TemplateLoader()
        print(f"✓ Template loader initialized with directory: {loader.template_dir}")
    except Exception as e:
        print(f"✗ Failed to initialize template loader: {e}")
        return False
    
    # List available templates
    templates = loader.list_templates()
    print(f"✓ Found {len(templates)} templates: {templates}")
    
    # Test loading NER template
    template_name = "ner.md"
    if template_name in templates:
        print(f"\n--- Testing {template_name} ---")
        
        # Sample schema and input
        sample_schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        sample_input = "John Smith works at Microsoft in Seattle. He is a software engineer."
        
        try:
            # Render template
            rendered_prompt = loader.render_prompt_template(
                template_name=template_name,
                schema=sample_schema,
                input_text=sample_input
            )
            
            print("✓ Template rendered successfully")
            print("\nRendered prompt:")
            print("-" * 20)
            print(rendered_prompt)
            print("-" * 20)
            
            # Try to parse as JSON to validate structure
            try:
                parsed = json.loads(rendered_prompt)
                print("✓ Rendered prompt is valid JSON")
                print(f"✓ Contains keys: {list(parsed.keys())}")
                
                # Check if it has the expected structure
                if "instruction" in parsed and "input" in parsed:
                    print("✓ Template has expected structure")
                else:
                    print("✗ Template missing expected keys")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"✗ Rendered prompt is not valid JSON: {e}")
                return False
                
        except Exception as e:
            print(f"✗ Failed to render template: {e}")
            return False
    else:
        print(f"✗ Template {template_name} not found")
        return False
    
    return True


def test_template_variables():
    """Test template rendering with various variables."""
    print("\n\nTesting Template Variables")
    print("=" * 40)
    
    try:
        loader = TemplateLoader()
        
        # Test with different variable combinations
        test_cases = [
            {
                "name": "Basic variables",
                "schema": {"entities": ["Person", "Organization"]},
                "input_text": "Apple Inc. was founded by Steve Jobs.",
                "entity_types": ["Person", "Organization"],
                "relation_types": ["founded_by"]
            },
            {
                "name": "Medical domain",
                "schema": {"entities": ["Disease", "Symptom", "Medicine"]},
                "input_text": "The patient has fever and takes aspirin.",
                "entity_types": ["Disease", "Symptom", "Medicine"],
                "relation_types": ["treats", "causes"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest case {i}: {test_case['name']}")
            
            try:
                rendered = loader.render_prompt_template(
                    template_name="ner.md",
                    **test_case
                )
                
                # Validate JSON structure
                parsed = json.loads(rendered)
                print(f"✓ Test case {i} rendered successfully")
                
                # Check that input was substituted correctly
                if parsed.get("input") == test_case["input_text"]:
                    print(f"✓ Input text substituted correctly")
                else:
                    print(f"✗ Input text not substituted correctly")
                    print(f"  Expected: {test_case['input_text']}")
                    print(f"  Got: {parsed.get('input')}")
                
            except Exception as e:
                print(f"✗ Test case {i} failed: {e}")
                return False
        
        print("✓ All variable tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Template variable testing failed: {e}")
        return False


def test_error_handling():
    """Test error handling for missing templates and invalid variables."""
    print("\n\nTesting Error Handling")
    print("=" * 40)
    
    try:
        loader = TemplateLoader()
        
        # Test missing template
        try:
            loader.render_template("nonexistent.md", {})
            print("✗ Should have failed for missing template")
            return False
        except Exception:
            print("✓ Correctly handles missing template")
        
        # Test template existence check
        if loader.template_exists("ner.md"):
            print("✓ Template existence check works")
        else:
            print("✗ Template existence check failed")
            return False
        
        if not loader.template_exists("nonexistent.md"):
            print("✓ Correctly identifies non-existent template")
        else:
            print("✗ Should have returned False for non-existent template")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False


if __name__ == "__main__":
    print("KAG-LangGraph Jinja2 Template Loading Test")
    print("=" * 50)
    
    success = True
    
    # Run tests
    success &= test_template_loading()
    success &= test_template_variables()
    success &= test_error_handling()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\nTo use templates in your extractor configuration:")
        print("  use_template: true")
        print("  template_name: 'ner.md'")
        print("\nTemplate variables available:")
        print("  - {{ schema }} - JSON schema for extraction")
        print("  - {{ input_text }} - Input text to process")
        print("  - {{ entity_types }} - List of entity types")
        print("  - {{ relation_types }} - List of relation types")
    else:
        print("✗ Some tests failed!")
        sys.exit(1)
