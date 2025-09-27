#!/usr/bin/env python3
"""
Standalone test script for Jinja2 template loading functionality.

This script tests the template loader without importing the full kag_langgraph package.
"""

import json
import sys
from pathlib import Path

# Test the template loader functionality directly
def test_jinja2_template():
    """Test Jinja2 template loading directly."""
    print("Testing Jinja2 Template Loading (Standalone)")
    print("=" * 50)
    
    try:
        from jinja2 import Environment, FileSystemLoader
        print("✓ Jinja2 is available")
    except ImportError:
        print("✗ Jinja2 not installed")
        return False
    
    # Set up template directory
    template_dir = Path(__file__).parent / "kag_langgraph" / "prompts"
    print(f"Template directory: {template_dir}")
    
    if not template_dir.exists():
        print(f"✗ Template directory does not exist: {template_dir}")
        return False
    
    # List template files
    template_files = list(template_dir.glob("*.md"))
    print(f"✓ Found {len(template_files)} template files: {[f.name for f in template_files]}")
    
    # Test loading ner.md template
    ner_template_path = template_dir / "ner.md"
    if not ner_template_path.exists():
        print("✗ ner.md template not found")
        return False
    
    print("\n--- Testing ner.md template ---")
    
    # Read template content
    with open(ner_template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    print("Template content (first 200 chars):")
    print(template_content[:200] + "..." if len(template_content) > 200 else template_content)
    
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )
    
    try:
        template = env.get_template("ner.md")
        print("✓ Template loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load template: {e}")
        return False
    
    # Test rendering with sample data
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
    
    sample_input = "John Smith works at Microsoft in Seattle."
    
    try:
        rendered = template.render(
            schema=json.dumps(sample_schema, indent=2),
            input_text=sample_input,
            entity_types=["Person", "Organization", "Location"],
            relation_types=["works_for", "located_in"]
        )
        
        print("✓ Template rendered successfully")
        print("\nRendered output:")
        print("-" * 30)
        print(rendered)
        print("-" * 30)
        
        # Validate JSON structure
        try:
            parsed = json.loads(rendered)
            print("✓ Rendered output is valid JSON")
            print(f"✓ JSON keys: {list(parsed.keys())}")
            
            # Check expected structure
            expected_keys = ["instruction", "schema", "example", "input"]
            missing_keys = [key for key in expected_keys if key not in parsed]
            if missing_keys:
                print(f"✗ Missing expected keys: {missing_keys}")
                return False
            else:
                print("✓ All expected keys present")
            
            # Check that input was substituted
            if parsed.get("input") == sample_input:
                print("✓ Input text correctly substituted")
            else:
                print(f"✗ Input text not substituted correctly")
                print(f"  Expected: {sample_input}")
                print(f"  Got: {parsed.get('input')}")
                return False
            
        except json.JSONDecodeError as e:
            print(f"✗ Rendered output is not valid JSON: {e}")
            return False
        
    except Exception as e:
        print(f"✗ Failed to render template: {e}")
        return False
    
    return True


def test_template_variations():
    """Test template with different variable combinations."""
    print("\n\nTesting Template Variations")
    print("=" * 40)
    
    try:
        from jinja2 import Environment, FileSystemLoader
        
        template_dir = Path(__file__).parent / "kag_langgraph" / "prompts"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("ner.md")
        
        test_cases = [
            {
                "name": "Medical domain",
                "schema": {"entities": ["Disease", "Symptom", "Medicine"]},
                "input_text": "The patient has fever and takes aspirin for headache.",
                "entity_types": ["Disease", "Symptom", "Medicine"],
                "relation_types": ["treats", "causes", "symptom_of"]
            },
            {
                "name": "Business domain",
                "schema": {"entities": ["Company", "Person", "Product"]},
                "input_text": "Apple Inc. released the iPhone, designed by Jonathan Ive.",
                "entity_types": ["Company", "Person", "Product"],
                "relation_types": ["released", "designed_by", "works_for"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest case {i}: {test_case['name']}")
            
            try:
                rendered = template.render(
                    schema=json.dumps(test_case["schema"], indent=2),
                    input_text=test_case["input_text"],
                    entity_types=test_case["entity_types"],
                    relation_types=test_case["relation_types"]
                )
                
                # Validate JSON
                parsed = json.loads(rendered)
                print(f"✓ Test case {i} rendered and parsed successfully")
                
                # Check input substitution
                if parsed.get("input") == test_case["input_text"]:
                    print(f"✓ Input correctly substituted")
                else:
                    print(f"✗ Input substitution failed")
                    return False
                
            except Exception as e:
                print(f"✗ Test case {i} failed: {e}")
                return False
        
        print("✓ All variation tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Template variation testing failed: {e}")
        return False


if __name__ == "__main__":
    print("Standalone Jinja2 Template Test for KAG-LangGraph")
    print("=" * 60)
    
    success = True
    success &= test_jinja2_template()
    success &= test_template_variations()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
        print("\nJinja2 template loading is working correctly.")
        print("You can now use templates in your extractor configuration:")
        print("  use_template: true")
        print("  template_name: 'ner.md'")
    else:
        print("✗ Some tests failed!")
        sys.exit(1)
