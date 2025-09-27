#!/usr/bin/env python3
"""
Example demonstrating Jinja2 template usage in KAG-LangGraph.

This example shows how to use templates for different domains and customize
prompt generation for specific use cases.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demonstrate_template_usage():
    """Demonstrate template usage without full pipeline."""
    print("KAG-LangGraph Jinja2 Template Usage Example")
    print("=" * 50)
    
    try:
        from jinja2 import Environment, FileSystemLoader
        
        # Set up template environment
        template_dir = project_root / "kag_langgraph" / "prompts"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        print(f"Template directory: {template_dir}")
        print(f"Available templates: {[f.name for f in template_dir.glob('*.md')]}")
        
        # Example 1: Medical Domain
        print("\n" + "=" * 30)
        print("Example 1: Medical Domain NER")
        print("=" * 30)
        
        medical_schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string", "enum": ["Disease", "Symptom", "Medicine", "Dosage"]}
                        }
                    }
                }
            }
        }
        
        medical_text = "Patient presents with acute myocardial infarction and hypertension. Prescribed metoprolol 50mg twice daily and aspirin 81mg once daily."
        
        template = env.get_template("ner.md")
        medical_prompt = template.render(
            schema=json.dumps(medical_schema, indent=2),
            input_text=medical_text,
            entity_types=["Disease", "Symptom", "Medicine", "Dosage"],
            relation_types=["treats", "causes", "prescribed_for"]
        )
        
        print("Medical prompt generated:")
        print("-" * 20)
        # Show first part of the prompt
        prompt_data = json.loads(medical_prompt)
        print(f"Instruction: {prompt_data['instruction'][:100]}...")
        print(f"Input: {prompt_data['input']}")
        print(f"Schema entities: {[item for item in prompt_data['schema']['properties']['entities']['items']['properties']['category']['enum']]}")
        
        # Example 2: Business Domain
        print("\n" + "=" * 30)
        print("Example 2: Business Domain NER")
        print("=" * 30)
        
        business_schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string", "enum": ["Organization", "Person", "Product", "Location"]}
                        }
                    }
                }
            }
        }
        
        business_text = "Apple Inc. announced the new iPhone 15 at their Cupertino headquarters. CEO Tim Cook presented the device to investors."
        
        business_prompt = template.render(
            schema=json.dumps(business_schema, indent=2),
            input_text=business_text,
            entity_types=["Organization", "Person", "Product", "Location"],
            relation_types=["announced", "presented_by", "located_at", "works_for"]
        )
        
        prompt_data = json.loads(business_prompt)
        print("Business prompt generated:")
        print("-" * 20)
        print(f"Instruction: {prompt_data['instruction'][:100]}...")
        print(f"Input: {prompt_data['input']}")
        print(f"Schema entities: {[item for item in prompt_data['schema']['properties']['entities']['items']['properties']['category']['enum']]}")
        
        # Example 3: Configuration-style usage
        print("\n" + "=" * 30)
        print("Example 3: Configuration Style")
        print("=" * 30)
        
        # Simulate extractor configuration
        config = {
            "use_template": True,
            "template_name": "ner.md",
            "llm_provider": "openai",
            "model": "gpt-3.5-turbo",
            "entity_types": ["Person", "Organization", "Location", "Event"],
            "relation_types": ["works_for", "located_in", "participated_in"],
            "domain": "news"
        }
        
        news_schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string", "enum": config["entity_types"]}
                        }
                    }
                }
            }
        }
        
        news_text = "President Biden met with European leaders in Brussels to discuss the NATO summit."
        
        news_prompt = template.render(
            schema=json.dumps(news_schema, indent=2),
            input_text=news_text,
            entity_types=config["entity_types"],
            relation_types=config["relation_types"],
            domain=config.get("domain", "general")
        )
        
        print("Configuration-based prompt:")
        print(f"Template: {config['template_name']}")
        print(f"Domain: {config.get('domain', 'general')}")
        print(f"Entity types: {config['entity_types']}")
        
        prompt_data = json.loads(news_prompt)
        print(f"Generated input: {prompt_data['input']}")
        
        return True
        
    except Exception as e:
        print(f"Error in template demonstration: {e}")
        return False


def show_configuration_examples():
    """Show configuration examples for different scenarios."""
    print("\n" + "=" * 50)
    print("Configuration Examples")
    print("=" * 50)
    
    configs = {
        "Medical Pipeline": {
            "pipeline": {
                "components": {
                    "extractor": {
                        "type": "llm_extractor",
                        "config": {
                            "use_template": True,
                            "template_name": "ner.md",
                            "llm_provider": "openai",
                            "model": "gpt-4",
                            "entity_types": ["Disease", "Symptom", "Medicine", "Dosage", "Procedure"],
                            "relation_types": ["treats", "causes", "prescribed_for", "performed_on"],
                            "domain": "medical",
                            "temperature": 0.1
                        }
                    }
                }
            }
        },
        
        "Business Intelligence": {
            "pipeline": {
                "components": {
                    "extractor": {
                        "type": "llm_extractor", 
                        "config": {
                            "use_template": True,
                            "template_name": "ner.md",
                            "llm_provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "entity_types": ["Company", "Person", "Product", "Financial_Metric", "Date"],
                            "relation_types": ["owns", "produces", "reports", "competes_with"],
                            "domain": "business",
                            "temperature": 0.2
                        }
                    }
                }
            }
        },
        
        "Legal Document Analysis": {
            "pipeline": {
                "components": {
                    "extractor": {
                        "type": "llm_extractor",
                        "config": {
                            "use_template": True,
                            "template_name": "ner.md",
                            "llm_provider": "openai",
                            "model": "gpt-4",
                            "entity_types": ["Legal_Entity", "Contract", "Clause", "Date", "Amount"],
                            "relation_types": ["party_to", "contains", "references", "supersedes"],
                            "domain": "legal",
                            "temperature": 0.05
                        }
                    }
                }
            }
        }
    }
    
    for name, config in configs.items():
        print(f"\n{name}:")
        print("-" * len(name))
        print(json.dumps(config, indent=2))


if __name__ == "__main__":
    success = demonstrate_template_usage()
    show_configuration_examples()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Template usage examples completed successfully!")
        print("\nNext steps:")
        print("1. Create your own domain-specific templates in kag_langgraph/prompts/")
        print("2. Configure your pipeline with use_template: true")
        print("3. Customize entity_types and relation_types for your domain")
        print("4. Test with your specific data")
    else:
        print("✗ Template usage examples failed!")
        sys.exit(1)
