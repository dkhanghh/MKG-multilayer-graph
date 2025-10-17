# KAG-LangGraph: Portable Knowledge Graph Construction Pipeline

A simplified, portable version of the KAG (Knowledge Augmented Generation) pipeline that uses LangGraph instead of NetworkX for workflow orchestration.

## Overview

KAG-LangGraph provides a complete pipeline for converting documents into knowledge graphs:

```
Documents → Scanner → Reader → Splitter → Extractor → Vectorizer → Writer → Knowledge Graph
```

### Key Features

- 🔄 **Stateful Workflows**: Uses LangGraph for robust, stateful pipeline execution
- 📚 **Multi-format Support**: Process PDF, DOCX, TXT, and other document formats  
- 🤖 **LLM Integration**: Extract knowledge using OpenAI, Ollama, or other LLM providers
- 🔌 **Pluggable Components**: Easy to extend and customize pipeline components
- 💾 **Multiple Output Formats**: Export to JSON, CSV, Neo4j, or custom formats
- ⚡ **High Performance**: Parallel processing and efficient resource utilization
- 🛠️ **Easy Configuration**: YAML-based configuration system

## Quick Start

### Installation

```bash
pip install -r requirements.txt
pip install -e .
```

### Basic Usage

1. **Create a configuration file** (`config.yaml`):

```yaml
pipeline:
  components:
    scanner:
      type: "file_scanner"
    reader:
      type: "pdf_reader"
    splitter:
      type: "semantic_splitter"
      chunk_size: 1000
      chunk_overlap: 200
    extractor:
      type: "llm_extractor"
      model: "gpt-4"
      api_key: "${OPENAI_API_KEY}"
    vectorizer:
      type: "embedding_vectorizer" 
      model: "all-MiniLM-L6-v2"
    writer:
      type: "json_writer"
      output_path: "./output/knowledge_graph.json"
```

2. **Run the pipeline**:

```python
from kag_langgraph import LangGraphExecutor, load_config

# Load configuration
config = load_config("config.yaml")

# Create and run pipeline
executor = LangGraphExecutor(config)
result = executor.run("path/to/your/document.pdf")

print(f"Generated knowledge graph with {len(result.nodes)} nodes and {len(result.edges)} edges")
```

## Pipeline Components

### Scanner
Discovers and processes input files:
- `FileScanner`: Process single files
- `DirectoryScanner`: Process entire directories
- Support for filtering by file type, size, etc.

### Reader
Extracts text content from documents:
- `PDFReader`: Extract text from PDF files
- `TXTReader`: Process plain text files  
- `DOCXReader`: Handle Microsoft Word documents
- Preserves document structure and metadata

### Splitter
Breaks documents into manageable chunks:
- `LengthSplitter`: Split by character/token count
- `SemanticSplitter`: Intelligent splitting using embeddings
- Configurable chunk size and overlap

### Extractor
Extracts structured knowledge from text:
- `LLMExtractor`: Use language models for entity/relation extraction
- Customizable prompts and schemas
- Support for multiple LLM providers

### Vectorizer
Creates embeddings for semantic search:
- `EmbeddingVectorizer`: Generate text embeddings
- Multiple embedding models supported
- Batch processing for efficiency

### Writer
Outputs knowledge graphs in various formats:
- `JSONWriter`: Export to JSON format
- `CSVWriter`: Export nodes/edges as CSV files
- `Neo4jWriter`: Direct integration with Neo4j database

## Configuration

The pipeline uses YAML configuration files for easy customization:

```yaml
pipeline:
  # Global pipeline settings
  max_workers: 4
  batch_size: 100
  
  # Component configurations
  components:
    extractor:
      type: "llm_extractor"
      model: "gpt-4"
      temperature: 0.1
      max_tokens: 2000
      extraction_schema:
        entities:
          - "Person"
          - "Organization" 
          - "Location"
        relations:
          - "works_for"
          - "located_in"
          - "founded_by"
```

## Examples

See the `examples/` directory for complete working examples:

- `basic_pipeline.py`: Simple document processing
- `batch_processing.py`: Process multiple documents
- `custom_components.py`: Create custom pipeline components
- `neo4j_integration.py`: Export to Neo4j database

## Architecture

Built on modern Python technologies:

- **LangGraph**: Stateful workflow orchestration
- **LangChain**: LLM integration and utilities
- **Pydantic**: Type-safe data models
- **Click**: Command-line interface
- **AsyncIO**: Efficient asynchronous processing

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black knowledge_graphs/
flake8 knowledge_graphs/
```

## License

Apache 2.0 License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For questions and support:

- GitHub Issues: [Create an issue](https://github.com/your-org/kag-langgraph/issues)
- Documentation: [Full docs](https://kag-langgraph.readthedocs.io/)
## Project Structure

```
thesis-llms-multilayer-graph/
├── knowledge_graphs/      # Core knowledge graph pipeline
├── chatbot_graphs/        # RAG chatbot implementation
├── agents/                # Agent implementations
├── data/                  # Data files
│   ├── financebench/      # FinanceBench dataset
│   └── output/            # Pipeline outputs
├── scripts/               # Utility scripts
│   ├── debug/             # Debug scripts
│   ├── utilities/         # Helper scripts
│   └── servers/           # Server scripts
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   └── component_tests/   # Component tests
├── docs/                  # Documentation
│   ├── guides/            # User guides
│   ├── api/               # API documentation
│   └── architecture/      # Architecture docs
├── configs/               # Configuration files
├── examples/              # Example code
└── utils/                 # Global utilities
```

See [docs/README.md](docs/README.md) for complete documentation.
