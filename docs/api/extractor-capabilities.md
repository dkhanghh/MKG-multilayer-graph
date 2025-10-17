# Knowledge Graph Extractor Components

This document describes the capabilities of the extractor components in the KAG-LangGraph pipeline. Extractors are responsible for extracting structured knowledge (entities and relationships) from text chunks.

## Overview

The extraction system provides three types of extractors, each designed for different use cases:

1. **LLMExtractor** - AI-powered extraction using Large Language Models
2. **RegexExtractor** - Pattern-based extraction using regular expressions
3. **KeywordExtractor** - Dictionary-based extraction using predefined keywords

## LLMExtractor

The LLMExtractor uses Large Language Models to intelligently extract entities and relationships from text.

### Capabilities

- **Intelligent Entity Recognition**: Automatically identifies entities like Person, Organization, Location, and Concept
- **Relationship Extraction**: Discovers semantic relationships between entities (works_for, located_in, related_to, part_of)
- **Contextual Understanding**: Leverages LLM comprehension for nuanced extraction
- **Custom Schema Support**: Supports domain-specific schemas via `.schema` files
- **Template-based Prompting**: Uses Jinja2 templates for consistent prompt generation
- **Batch Processing**: Processes multiple chunks in parallel for efficiency
- **Entity Deduplication**: Merges duplicate entities across chunks
- **Confidence Scoring**: Assigns confidence scores to extracted relationships

### Configuration Options

```json
{
  "llm_provider": "openai",           // LLM provider (openai, ollama)
  "model": "gpt-3.5-turbo",          // Model name
  "api_key": "your-api-key",         // API key for provider
  "temperature": 0.1,                // Generation temperature
  "max_tokens": 2000,                // Maximum response tokens
  "entity_types": [                  // Types of entities to extract
    "Person", "Organization", "Location", "Concept"
  ],
  "relation_types": [                // Types of relationships to extract
    "works_for", "located_in", "related_to", "part_of"
  ],
  "extraction_schema": {},           // Custom extraction schema
  "batch_size": 5,                   // Parallel processing batch size
  "use_template": false,             // Enable Jinja2 templates
  "template_name": "ner.md"          // Template file name
}
```

### Domain Schema Support

The LLMExtractor supports custom domain schemas in a special format:

```
namespace DomainKG

EntityType(中文名): EntityType
     properties:
        property_name(中文名): Type
            index: IndexType
```

### Output Format

Creates SubGraph objects containing:
- **Nodes**: Entities with IDs, names, types, descriptions, and properties
- **Edges**: Relationships with source/target IDs, relation types, and confidence scores
- **Metadata**: Extraction method, model used, and extraction statistics

### Use Cases

- General-purpose knowledge extraction from documents
- Domain-specific entity extraction with custom schemas
- Research paper analysis
- Legal document processing
- Medical text analysis

## RegexExtractor

The RegexExtractor uses regular expression patterns to find structured entities in text.

### Capabilities

- **Pattern Matching**: Finds entities using customizable regex patterns
- **Built-in Patterns**: Pre-configured patterns for emails, phone numbers, and URLs
- **Case Sensitivity Control**: Optional case-sensitive matching
- **Position Tracking**: Records match positions in source text
- **High Performance**: Fast extraction for large text volumes

### Configuration Options

```json
{
  "patterns": {                      // Entity type to regex pattern mapping
    "email": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
    "phone": "\\b(?:\\+?1[-.\\s]?)?\\(?([0-9]{3})\\)?[-.\\s]?([0-9]{3})[-.\\s]?([0-9]{4})\\b",
    "url": "https?://(?:[-\\w.])+(?:\\:[0-9]+)?(?:/(?:[\\w/_.])*(?:\\?(?:[\\w&=%.])*)?(?:\\#(?:[\\w.])*)?)?",
    "custom_pattern": "your-regex-here"
  },
  "case_sensitive": false            // Case sensitivity toggle
}
```

### Output Format

Creates SubGraph objects with:
- **Nodes**: Pattern-matched entities with match positions
- **Properties**: Pattern used, match start/end positions
- **No Relationships**: Only extracts entities, not relationships

### Use Cases

- Contact information extraction (emails, phones)
- URL and link extraction
- Date and time parsing
- ID number extraction (SSN, license plates, etc.)
- Structured data extraction from formatted text

## KeywordExtractor

The KeywordExtractor finds predefined keywords and phrases in text.

### Capabilities

- **Dictionary Matching**: Finds exact matches for predefined terms
- **Word Boundary Control**: Optional word boundary enforcement
- **Case Sensitivity Control**: Configurable case matching
- **Multiple Categories**: Organizes keywords by entity types
- **Position Tracking**: Records keyword positions in text

### Configuration Options

```json
{
  "keywords": {                      // Entity type to keyword list mapping
    "Technology": ["AI", "Machine Learning", "Python"],
    "Company": ["Google", "Microsoft", "Apple"],
    "Product": ["iPhone", "Windows", "Chrome"]
  },
  "case_sensitive": false,           // Case sensitivity toggle
  "word_boundaries": true            // Require word boundaries
}
```

### Output Format

Creates SubGraph objects with:
- **Nodes**: Keyword matches as entities
- **Properties**: Matched keyword, match positions
- **No Relationships**: Only extracts entities

### Use Cases

- Technical term extraction
- Company/product name recognition
- Domain-specific vocabulary extraction
- Compliance keyword detection
- Brand mention tracking

## Common Features

All extractors share these capabilities:

### Pipeline Integration
- Process chunks from pipeline state
- Return updated state with extracted subgraphs
- Handle batch processing for efficiency

### Error Handling
- Graceful failure handling for individual chunks
- Detailed error logging
- Continue processing despite individual failures

### Source Tracking
- Link extracted entities to source chunks
- Preserve source file and page number information
- Enable traceability of extracted knowledge

### Extensibility
- Plugin architecture via component registry
- Easy addition of new extractor types
- Configurable through JSON schemas

## Usage Examples

### LLMExtractor with Custom Schema
```python
config = {
    "llm_provider": "openai",
    "model": "gpt-4",
    "entity_types": ["Researcher", "Institution", "Publication"],
    "relation_types": ["authored", "affiliated_with", "cites"],
    "extraction_schema": "research.schema"
}
```

### RegexExtractor for Contact Info
```python
config = {
    "patterns": {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}-\d{3}-\d{4}\b"
    }
}
```

### KeywordExtractor for Technology Terms
```python
config = {
    "keywords": {
        "AI_Technology": ["neural network", "deep learning", "transformer"],
        "Programming": ["Python", "JavaScript", "React"]
    },
    "word_boundaries": True
}
```

## Vectorizer Support

The extractor components integrate with vectorizer components to create embeddings:

### GeminiVectorizer
- Uses Google Gemini's embedding models (e.g., gemini-embedding-001)
- High-quality embeddings with good multilingual support
- Uses the latest `google-genai` package
- Requires `GOOGLE_API_KEY` environment variable
- Configurable batch processing and text templates

Example configuration:
```python
vectorizer_config = {
    "model": "gemini-embedding-001",
    "api_key": "your-google-api-key",
    "batch_size": 100,
    "embed_nodes": True,
    "embed_edges": False,
    "node_text_template": "{name} is a {type}. {description}",
    "edge_text_template": "{source} {relation} {target}"
}
```

## Performance Considerations

- **LLMExtractor**: Slower but most accurate, API costs apply
- **RegexExtractor**: Very fast, suitable for large volumes
- **KeywordExtractor**: Fast, good for known vocabularies

Choose the appropriate extractor based on your accuracy needs, performance requirements, and available resources.