# Jinja2 Template Support in KAG-LangGraph

KAG-LangGraph now supports using Jinja2 templates for LLM prompts, providing a flexible and maintainable way to manage prompt templates for different domains and use cases.

## Overview

The Jinja2 template system allows you to:
- Store prompts in separate markdown files for better organization
- Use variables and template logic for dynamic prompt generation
- Maintain consistent prompt structure across different domains
- Easily customize prompts without modifying code

## Installation

Jinja2 is included in the requirements and will be installed automatically:

```bash
pip install jinja2>=3.0.0
```

## Basic Usage

### 1. Enable Template Usage in Configuration

```yaml
# config.yaml
pipeline:
  components:
    extractor:
      type: "llm_extractor"
      enabled: true
      config:
        # Enable template usage
        use_template: true
        template_name: "ner.md"
        
        # Standard LLM configuration
        llm_provider: "openai"
        model: "gpt-3.5-turbo"
        api_key: "${OPENAI_API_KEY}"
        
        # Entity and relation types (passed to template)
        entity_types:
          - "Person"
          - "Organization"
          - "Location"
        relation_types:
          - "works_for"
          - "located_in"
```

### 2. Template File Structure

Templates are stored in `kag_langgraph/prompts/` directory. Here's the structure of `ner.md`:

```json
{
    "instruction": "You are an expert in named entity recognition. Please extract entities from the input that match the schema definition. If no entities of that type exist, please return an empty list. Please respond in JSON string format. You can refer to the example for extraction guidance.",
    "schema": {{ schema }},
    "example": [
        {
            "input": "Sample input text with entities...",
            "output": [
                {"name": "entity_name", "category": "EntityType"}
            ]
        }
    ],
    "input": "{{ input_text }}"
}
```

## Template Variables

The following variables are automatically available in templates:

| Variable | Type | Description |
|----------|------|-------------|
| `{{ schema }}` | JSON | The extraction schema object |
| `{{ input_text }}` | String | The input text to process |
| `{{ entity_types }}` | List | List of entity types from config |
| `{{ relation_types }}` | List | List of relation types from config |

### Custom Variables

You can pass additional variables through the extractor configuration:

```yaml
extractor:
  config:
    use_template: true
    template_name: "custom_ner.md"
    
    # Custom variables
    domain: "medical"
    language: "english"
    confidence_threshold: 0.8
```

Access them in templates:
```json
{
    "instruction": "Extract {{ domain }} entities in {{ language }}...",
    "confidence_threshold": {{ confidence_threshold }}
}
```

## Template Examples

### Medical Domain Template

Create `medical_ner.md`:

```json
{
    "instruction": "You are a medical expert specializing in named entity recognition. Extract medical entities from clinical text. Focus on accuracy and use standard medical terminology.",
    "schema": {{ schema }},
    "entity_types": {{ entity_types | tojson }},
    "example": [
        {
            "input": "Patient presents with fever and headache. Prescribed acetaminophen 500mg.",
            "output": [
                {"name": "fever", "category": "Symptom"},
                {"name": "headache", "category": "Symptom"},
                {"name": "acetaminophen", "category": "Medicine"},
                {"name": "500mg", "category": "Dosage"}
            ]
        }
    ],
    "input": "{{ input_text }}"
}
```

### Business Domain Template

Create `business_ner.md`:

```json
{
    "instruction": "Extract business-related entities from corporate documents. Focus on organizations, people, products, and business relationships.",
    "schema": {{ schema }},
    "domain_focus": "business",
    "example": [
        {
            "input": "Apple Inc. released the iPhone, designed by Jonathan Ive in Cupertino.",
            "output": [
                {"name": "Apple Inc.", "category": "Organization"},
                {"name": "iPhone", "category": "Product"},
                {"name": "Jonathan Ive", "category": "Person"},
                {"name": "Cupertino", "category": "Location"}
            ]
        }
    ],
    "input": "{{ input_text }}"
}
```

## Advanced Template Features

### Conditional Logic

```json
{
    "instruction": "Extract entities from {{ 'medical' if domain == 'healthcare' else 'general' }} text...",
    {% if entity_types %}
    "allowed_entities": {{ entity_types | tojson }},
    {% endif %}
    "input": "{{ input_text }}"
}
```

### Loops and Filters

```json
{
    "entity_examples": [
        {% for entity_type in entity_types %}
        "{{ entity_type }}"{% if not loop.last %},{% endif %}
        {% endfor %}
    ],
    "formatted_schema": {{ schema | tojson | indent(4) }}
}
```

## Template Management

### Creating New Templates

1. Create a new `.md` file in `kag_langgraph/prompts/`
2. Use Jinja2 syntax with `{{ variable }}` for substitutions
3. Ensure the output is valid JSON
4. Test with the template loader

### Template Validation

Use the provided test script to validate templates:

```bash
python test_template_standalone.py
```

### Template Organization

Organize templates by domain or use case:

```
kag_langgraph/prompts/
├── ner.md              # General NER
├── medical_ner.md      # Medical domain
├── business_ner.md     # Business domain
├── legal_ner.md        # Legal domain
├── triple.md           # Relation extraction
└── custom_domain.md    # Custom domain
```

## Configuration Examples

### Multi-Domain Pipeline

```yaml
# Medical pipeline
medical_pipeline:
  components:
    extractor:
      config:
        use_template: true
        template_name: "medical_ner.md"
        entity_types: ["Disease", "Symptom", "Medicine", "Dosage"]
        domain: "medical"

# Business pipeline  
business_pipeline:
  components:
    extractor:
      config:
        use_template: true
        template_name: "business_ner.md"
        entity_types: ["Organization", "Person", "Product", "Location"]
        domain: "business"
```

### Fallback Configuration

```yaml
extractor:
  config:
    use_template: true
    template_name: "custom_ner.md"
    
    # Fallback to traditional prompts if template fails
    entity_types: ["Person", "Organization", "Location"]
    relation_types: ["works_for", "located_in"]
```

## Best Practices

1. **Keep templates simple**: Focus on clear, concise prompts
2. **Use meaningful examples**: Provide relevant examples for your domain
3. **Validate JSON output**: Ensure templates produce valid JSON
4. **Test thoroughly**: Use the test scripts to validate templates
5. **Version control**: Keep templates in version control
6. **Document variables**: Comment on custom variables in templates
7. **Error handling**: The system falls back to traditional prompts if templates fail

## Troubleshooting

### Common Issues

1. **Template not found**: Check file path and name
2. **Invalid JSON**: Validate template output structure
3. **Variable errors**: Ensure all variables are defined
4. **Jinja2 syntax errors**: Check template syntax

### Debug Mode

Enable debug logging to see template rendering details:

```python
import logging
logging.getLogger('kag_langgraph.utils.template_loader').setLevel(logging.DEBUG)
```

## Migration from Traditional Prompts

To migrate existing configurations:

1. Set `use_template: true`
2. Specify `template_name`
3. Move custom prompt logic to template files
4. Test with existing data
5. Gradually customize templates for your domain

The system maintains backward compatibility - if template loading fails, it falls back to traditional prompt generation.
