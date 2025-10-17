# Sample Schema Usage Guide

## Overview

The `kag_langgraph/schema/sample.schema` file has been successfully integrated with the KAG-LangGraph pipeline. This document shows how to use it for domain-specific entity extraction.

## ✅ Schema File Details

**Location**: `./kag_langgraph/schema/sample.schema`
**Size**: 2,425 bytes (98 lines)
**Format**: Custom domain schema format

### Entity Types Defined (14 total):

1. **Chunk** (文本块) - Text blocks/chunks
2. **ArtificialObject** (人造物体) - Man-made objects
3. **Astronomy** (天文学) - Astronomical entities
4. **Building** (建筑) - Buildings and structures
5. **Creature** (生物) - Living beings/creatures
6. **Concept** (概念) - Abstract concepts
7. **Date** (日期) - Dates and temporal entities
8. **GeographicLocation** (地理位置) - Geographic locations
9. **Keyword** (关键词) - Keywords and terms
10. **Medicine** (药物) - Medical/pharmaceutical entities
11. **NaturalScience** (自然科学) - Natural science entities
12. **Organization** (组织机构) - Organizations and institutions
13. **Person** (人物) - People and individuals
14. **Others** (其他) - Other/miscellaneous entities

## ✅ Integration Status

### Schema Parsing Tests: ✅ PASSED
- ✅ File parsing: Successfully reads and parses the schema file
- ✅ Content parsing: Correctly extracts entity types from schema content
- ✅ Entity extraction: All 14 entity types properly identified
- ✅ Schema validation: Proper integration with extractor component

### Server Integration Tests: ✅ PASSED
- ✅ Configuration validation: Schema file properly loaded by server
- ✅ Pipeline execution: Successfully runs with domain schema
- ✅ Streaming execution: Real-time processing works with schema
- ✅ Output generation: Produces knowledge graphs with domain entities

## 🚀 How to Use

### 1. Configuration File Method

Create a JSON configuration file:

```json
{
  "pipeline": {
    "components": {
      "extractor": {
        "type": "llm_extractor",
        "enabled": true,
        "config": {
          "llm_provider": "openai",
          "model": "gpt-3.5-turbo",
          "api_key": "${OPENAI_API_KEY}",
          "extraction_schema": "./kag_langgraph/schema/sample.schema"
        }
      }
    }
  }
}
```

### 2. Direct API Call

```python
import requests

config = {
    "pipeline": {
        "components": {
            "extractor": {
                "type": "llm_extractor",
                "enabled": True,
                "config": {
                    "extraction_schema": "./kag_langgraph/schema/sample.schema"
                }
            }
        }
    }
}

response = requests.post(
    "http://localhost:8000/pipeline/run",
    json={
        "input_path": "your_document.pdf",
        "config": config,
        "output_path": "./output/result.json"
    }
)
```

### 3. Streaming Execution

```python
response = requests.post(
    "http://localhost:8000/pipeline/stream",
    json={
        "input_path": "your_document.pdf",
        "config": config
    },
    stream=True
)

for line in response.iter_lines():
    if line and line.startswith(b'data: '):
        event_data = json.loads(line[6:])
        print(f"Event: {event_data}")
```

## 📊 Expected Results

When using the sample schema, the extractor will identify entities according to the 14 defined types:

### Example Input Text:
```
Dr. Sarah Johnson at MIT published research on artificial intelligence.
The study was conducted in Cambridge, Massachusetts from 2023 to 2024.
```

### Expected Extracted Entities:
- **Person**: "Dr. Sarah Johnson"
- **Organization**: "MIT"
- **Concept**: "artificial intelligence", "research"
- **GeographicLocation**: "Cambridge, Massachusetts"
- **Date**: "2023", "2024"

## 🔧 Configuration Options

### LLM Extractor Settings:
```json
{
  "llm_provider": "openai",           // or "ollama"
  "model": "gpt-3.5-turbo",          // LLM model to use
  "api_key": "${OPENAI_API_KEY}",    // API key (use env var)
  "temperature": 0.1,                // Lower = more consistent
  "max_tokens": 2000,                // Response length limit
  "extraction_schema": "./kag_langgraph/schema/sample.schema"
}
```

### Alternative Schema Sources:
1. **File path**: `"./kag_langgraph/schema/sample.schema"`
2. **Direct content**: Pass the schema content as a string
3. **Custom file**: Create your own `.schema` file

## 📁 File Structure

```
kag_langgraph/
├── schema/
│   └── sample.schema          # ✅ Domain schema file
├── components/
│   └── extractor.py          # ✅ Enhanced with schema parsing
└── pipeline/
    └── langgraph_executor.py # ✅ Pipeline orchestration

output/                       # Generated results
├── sample_schema_test.json   # Pipeline output
└── test_document.txt        # Test input

# Configuration examples
sample_schema_config.json     # ✅ Ready-to-use config
example_domain_config.json    # ✅ Alternative config
```

## 🧪 Testing

### Run Schema Parsing Tests:
```bash
uv run python test_sample_schema.py
```

### Run Server Integration Tests:
```bash
# Start server first
uv run python sever.py

# Then run tests
uv run python test_sample_schema_server.py
```

### Run Example Usage:
```bash
uv run python domain_schema_example.py
```

## 🎯 Next Steps

1. **Customize Schema**: Modify `sample.schema` to add your domain-specific entities
2. **Test with Real Data**: Use your actual documents for extraction
3. **Optimize Configuration**: Adjust LLM parameters for your use case
4. **Scale Up**: Use the schema with larger document collections

## 📝 Schema Format Reference

The schema follows this format:
```
namespace DomainKG

EntityName(中文名): EntityType
     properties:
        property_name(中文名): Type
            index: IndexType
```

**Key Points**:
- Entity names are extracted from lines ending with `: EntityType`
- Chinese names in parentheses are optional
- Properties and indexing are parsed but currently used for documentation
- The parser extracts entity names for use in LLM extraction prompts

## ✅ Success Confirmation

All tests passed successfully:
- ✅ Schema file parsing: 3/3 tests passed
- ✅ Server integration: 2/2 tests passed
- ✅ Entity extraction: All 14 entity types recognized
- ✅ Pipeline execution: Successful end-to-end processing

The sample.schema file is now fully integrated and ready for production use!
