#!/usr/bin/env python3
"""
Test script for Jinja2 template loading functionality.

This script demonstrates how to use the template loader to load and render
prompt templates from markdown files.
"""

import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_graphs.utils.template_loader import get_template_loader, load_prompt_template


def test_template_loading():
    """Test basic template loading functionality."""
    print("Testing Jinja2 Template Loading")
    print("=" * 40)
    
    # Get template loader
    try:
        loader = get_template_loader()
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
            rendered_prompt = load_prompt_template(
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


def test_extractor_integration():
    """Test template loading with extractor configuration."""
    print("\n\nTesting Extractor Integration")
    print("=" * 40)
    
    # Sample extractor config with template usage
    config = {
        "llm_provider": "openai",
        "model": "gpt-3.5-turbo",
        "use_template": True,
        "template_name": "ner.md",
        "entity_types": ["Person", "Organization", "Location"],
        "relation_types": ["works_for", "located_in"]
    }
    
    print("Sample extractor configuration:")
    print(json.dumps(config, indent=2))
    
    # Test template loading with extractor-style parameters
    try:
        sample_schema = {
            "entities": config["entity_types"],
            "relations": config["relation_types"]
        }
        
        rendered = load_prompt_template(
            template_name=config["template_name"],
            schema=sample_schema,
            input_text="Apple Inc. is headquartered in Cupertino, California.",
            entity_types=config["entity_types"],
            relation_types=config["relation_types"]
        )
        
        print("✓ Template rendered with extractor-style parameters")
        print("\nSample output (first 200 chars):")
        print(rendered[:200] + "..." if len(rendered) > 200 else rendered)
        
    except Exception as e:
        print(f"✗ Failed to render with extractor parameters: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("KAG-LangGraph Jinja2 Template Loading Test")
    print("=" * 50)
    
    success = True
    
    # Run tests
    success &= test_template_loading()
    success &= test_extractor_integration()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\nTo use templates in your extractor configuration:")
        print("  use_template: true")
        print("  template_name: 'ner.md'")
    else:
        print("✗ Some tests failed!")
        sys.exit(1)
