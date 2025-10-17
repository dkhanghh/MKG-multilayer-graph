# KAG-LangGraph: A Portable Knowledge Graph Construction Pipeline

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

A portable, modular knowledge graph construction pipeline built with LangGraph, extracted and modernized from the original KAG (Knowledge Augmented Generation) framework.

## 🚀 Overview

KAG-LangGraph provides a complete pipeline for extracting structured knowledge graphs from unstructured documents. It replaces the original NetworkX-based workflow execution with LangGraph's more modern stateful workflow management, offering better error handling, progress tracking, and streaming capabilities.

### Key Features

- **🔄 Modern Workflow Engine**: Uses LangGraph instead of NetworkX for stateful workflow execution
- **🧩 Modular Architecture**: Clean component-based design with pluggable extractors, vectorizers, and writers
- **⚡ Multiple Execution Modes**: Synchronous, asynchronous, and streaming pipeline execution
- **📊 Progress Tracking**: Real-time progress monitoring with comprehensive metrics
- **🛠️ Flexible Configuration**: YAML-based configuration with environment variable support
- **🔍 Multiple Extractors**: Supports LLM-based, regex-based, and keyword-based entity extraction
- **📝 Multiple Output Formats**: JSON, CSV, and Neo4j database outputs
- **🧪 Comprehensive Testing**: Full test coverage with component and integration tests

## 📦 Installation

### Requirements

- Python 3.8+
- Required packages: `pydantic`, `langgraph`, `sentence-transformers` (optional)

### Install Dependencies

```bash
# Using uv (recommended)
uv pip install pydantic langgraph

# Optional: For embedding-based vectorization
uv pip install sentence-transformers

# Optional: For advanced splitting and NLP features
uv pip install nltk spacy
```

## 🏗️ Pipeline Architecture

The KAG-LangGraph pipeline follows a clean six-stage architecture:

```
Scanner → Reader → Splitter → Extractor → Vectorizer → Writer
```

### Component Descriptions

1. **Scanner**: Discovers and filters input files
   - `FileScanner`: Process single files
   - `DirectoryScanner`: Recursively scan directories
   - `URLScanner`: Fetch content from URLs
   - `PatternScanner`: Advanced file pattern matching

2. **Reader**: Extracts text from various document formats
   - `TXTReader`: Plain text files
   - `PDFReader`: PDF documents (requires `PyPDF2`)
   - `DOCXReader`: Word documents (requires `python-docx`)
   - `MixedReader`: Auto-detects file types

3. **Splitter**: Breaks documents into manageable chunks
   - `LengthSplitter`: Character/word-based splitting
   - `SentenceSplitter`: Sentence-aware splitting (requires `nltk`)
   - `SemanticSplitter`: Semantic similarity-based splitting

4. **Extractor**: Extracts entities and relationships
   - `LLMExtractor`: Uses LLMs (OpenAI/Ollama) for extraction
   - `RegexExtractor`: Pattern-based extraction
   - `KeywordExtractor`: Predefined keyword matching

5. **Vectorizer**: Creates embeddings for semantic search
   - `EmbeddingVectorizer`: Local sentence transformers
   - `OpenAIVectorizer`: OpenAI's embedding API
   - `NoOpVectorizer`: Skip vectorization

6. **Writer**: Outputs the knowledge graph
   - `JSONWriter`: JSON format output
   - `CSVWriter`: CSV files for nodes and edges
   - `Neo4jWriter`: Direct database integration

## 🎯 Quick Start

### Basic Usage

```python
from kag_langgraph.pipeline import PipelineWorkflow

# Simple configuration
config = {
    "pipeline": {
        "components": {
            "scanner": {"type": "file_scanner", "enabled": True},
            "reader": {"type": "txt_reader", "enabled": True},
            "splitter": {"type": "length_splitter", "enabled": True},
            "extractor": {
                "type": "regex_extractor",
                "enabled": True,
                "config": {
                    "patterns": {
                        "email": r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
                    }
                }
            },
            "vectorizer": {"type": "no_op_vectorizer", "enabled": True},
            "writer": {
                "type": "json_writer",
                "enabled": True,
                "config": {"output_path": "./output/knowledge_graph.json"}
            }
        }
    }
}

# Run pipeline
workflow = PipelineWorkflow(config=config)
results = workflow.run_pipeline("./documents/my_document.txt")
print(f"Knowledge graph saved to: {results['output_path']}")
```

### Using Configuration Files

```python
from kag_langgraph.pipeline import PipelineWorkflow

# Load from YAML configuration
workflow = PipelineWorkflow(config_path="./config.yaml")
results = workflow.run_pipeline("./documents/")
```

### Streaming Execution

```python
# Monitor progress in real-time
for update in workflow.stream_pipeline("./documents/"):
    component = update.get("current_component", "unknown")
    progress = update.get("progress", 0.0)
    print(f"{component}: {progress:.1%} complete")
```

### Async Execution

```python
import asyncio

async def process_documents():
    workflow = PipelineWorkflow(config=config)
    results = await workflow.arun_pipeline("./documents/")
    return results

results = asyncio.run(process_documents())
```

## 📋 Configuration

### YAML Configuration Example

```yaml
pipeline:
  name: "Knowledge Graph Pipeline"
  components:
    scanner:
      type: "directory_scanner"
      enabled: true
      config:
        recursive: true
        file_patterns: ["*.txt", "*.pdf", "*.docx"]
    
    reader:
      type: "mixed_reader"
      enabled: true
      config:
        supported_types: ["txt", "pdf", "docx"]
    
    splitter:
      type: "semantic_splitter"
      enabled: true
      config:
        similarity_threshold: 0.8
        max_chunk_length: 2000
    
    extractor:
      type: "llm_extractor"
      enabled: true
      config:
        llm_provider: "openai"
        model: "gpt-3.5-turbo"
        api_key: "${OPENAI_API_KEY}"
        entity_types: ["Person", "Organization", "Location"]
    
    vectorizer:
      type: "embedding_vectorizer"
      enabled: true
      config:
        model_name: "all-MiniLM-L6-v2"
    
    writer:
      type: "json_writer"
      enabled: true
      config:
        output_path: "./output/knowledge_graph.json"
        pretty_print: true
```

### Environment Variables

Set your API keys and configuration:

```bash
export OPENAI_API_KEY="your-api-key-here"
export OLLAMA_BASE_URL="http://localhost:11434"  # For local Ollama
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
uv run tests/test_components.py

# Or run specific examples
uv run examples/basic_pipeline.py
uv run examples/advanced_example.py
```

## 📁 Project Structure

```
kag_langgraph/
├── __init__.py                 # Package exports
├── components/                 # Pipeline components
│   ├── base.py                # Abstract base classes
│   ├── scanner.py             # File/directory scanners
│   ├── reader.py              # Document readers
│   ├── splitter.py            # Text splitters
│   ├── extractor.py           # Entity/relation extractors
│   ├── vectorizer.py          # Embedding generators
│   └── writer.py              # Output writers
├── models/                     # Data models
│   ├── chunk.py               # Text chunk representation
│   ├── graph.py               # Knowledge graph models
│   └── pipeline_state.py      # Pipeline state management
├── pipeline/                   # Pipeline orchestration
│   ├── langgraph_executor.py  # LangGraph workflow executor
│   └── config.py              # Configuration management
└── utils/                      # Utilities
    ├── registry.py            # Component registry
    └── llm_client.py           # LLM client abstraction
```

## 🔧 Advanced Usage

### Custom Components

Create custom pipeline components by extending the base classes:

```python
from kag_langgraph.components.base import BaseExtractor
from kag_langgraph.models.pipeline_state import PipelineState

class MyCustomExtractor(BaseExtractor):
    def process(self, state: PipelineState) -> PipelineState:
        # Your custom extraction logic here
        chunks = state.get("split_chunks", [])
        subgraphs = []
        
        # Process chunks and create subgraphs
        # ...
        
        state["subgraphs"] = subgraphs
        return state

# Register your component
from kag_langgraph.utils.registry import ComponentRegistry
ComponentRegistry.register("my_extractor", MyCustomExtractor)
```

### Multiple Output Formats

Configure multiple writers for different output formats:

```python
config = {
    "pipeline": {
        "components": {
            # ... other components ...
            "writer": {
                "type": "multi_writer",  # Custom multi-output writer
                "config": {
                    "outputs": [
                        {"type": "json_writer", "path": "./output/graph.json"},
                        {"type": "csv_writer", "path": "./output/"},
                        {"type": "neo4j_writer", "uri": "bolt://localhost:7687"}
                    ]
                }
            }
        }
    }
}
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and development process.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built upon the original [KAG framework](https://github.com/OpenSPG/KAG) architecture
- Uses [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- Inspired by modern MLOps and data pipeline best practices

## 📚 Examples

Check out the `examples/` directory for more detailed usage examples:

- `basic_pipeline.py`: Simple document processing pipeline
- `advanced_example.py`: Complex multi-document processing with streaming
- `config.yaml`: Complete configuration file example

## 🔍 Troubleshooting

### Common Issues

1. **Missing dependencies**: Install optional dependencies based on your use case
2. **API key errors**: Ensure environment variables are properly set
3. **Memory issues**: Adjust batch sizes in configuration for large document sets
4. **Model downloads**: First run may take time to download transformer models

### Performance Tips

- Use `no_op_vectorizer` if you don't need embeddings
- Adjust chunk sizes based on your LLM's context window
- Enable parallel processing for large document sets
- Use streaming mode for real-time progress monitoring

For more help, please check our [Issues](https://github.com/your-repo/kag-langgraph/issues) or start a [Discussion](https://github.com/your-repo/kag-langgraph/discussions).