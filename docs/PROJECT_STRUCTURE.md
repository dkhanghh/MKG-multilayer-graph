# Project Structure

**Last Updated**: October 17, 2024

---

## 📂 Complete Directory Tree

```
thesis-llms-multilayer-graph/
│
├── 📄 Core Files (Root)
│   ├── README.md                           # Project overview
│   ├── LICENSE                             # MIT License
│   ├── requirements.txt                    # Python dependencies
│   ├── setup.py                            # Package setup
│   ├── pytest.ini                          # Pytest configuration
│   ├── langgraph.json                      # LangGraph configuration
│   ├── .env.example                        # Environment template
│   ├── .gitignore                          # Git ignore rules
│   └── main.py                             # Main entry point
│
├── 🧠 knowledge_graphs/                    # Core Knowledge Graph Pipeline
│   ├── __init__.py
│   ├── components/                         # Pipeline Components
│   │   ├── __init__.py
│   │   ├── base.py                         # Base component classes
│   │   ├── scanner.py                      # File scanner
│   │   ├── reader.py                       # Document readers
│   │   ├── financebench_reader.py          # FinanceBench reader
│   │   ├── splitter.py                     # Text splitters
│   │   ├── extractor.py                    # Entity/relationship extractors
│   │   ├── vectorizer.py                   # Embedding generators
│   │   └── writer.py                       # Graph writers (Neo4j)
│   ├── models/                             # Data Models
│   │   ├── __init__.py
│   │   ├── chunk.py                        # Chunk model
│   │   ├── graph.py                        # Graph models
│   │   └── pipeline_state.py               # Pipeline state
│   ├── pipeline/                           # Pipeline Execution
│   │   ├── __init__.py
│   │   ├── config.py                       # Configuration system
│   │   ├── langgraph_executor.py           # LangGraph executor
│   │   └── batch_processor.py              # Batch processing
│   ├── prompts/                            # LLM Prompts
│   │   ├── ner.md                          # Named entity recognition
│   │   ├── std.md                          # Standardization
│   │   ├── trp.md                          # Triple extraction
│   │   └── kn.md                           # Knowledge normalization
│   ├── schema/                             # Graph Schemas
│   │   ├── financebench.schema             # FinanceBench schema
│   │   ├── financebench_spg.schema         # SPG schema
│   │   └── sample.schema                   # Sample schema
│   └── utils/                              # Utilities
│       ├── __init__.py
│       ├── llm_client.py                   # LLM client wrapper
│       ├── registry.py                     # Component registry
│       └── template_loader.py              # Template loader
│
├── 💬 chatbot_graphs/                      # RAG Chatbot Implementation
│   ├── README.md                           # Chatbot documentation
│   ├── .env.example                        # Chatbot env template
│   ├── rag_graph.py                        # Main RAG graph
│   ├── GEMINI_EMBEDDINGS.md                # Embeddings guide
│   ├── test_llm_connection.py              # Connection test
│   └── test_llm_simple.py                  # Simple LLM test
│
├── 🤖 agents/                              # Agent Implementations
│   └── rag_agent.py                        # RAG agent
│
├── ⚙️ configs/                             # Configuration Files
│   ├── config.py                           # Python config
│   └── financebench_pipeline.yaml          # FinanceBench pipeline config
│
├── 📁 data/                                # Data Files
│   ├── financebench/                       # FinanceBench Dataset
│   │   ├── financebench_id_00005.txt
│   │   ├── financebench_id_00070.txt
│   │   └── ... (150 financial documents)
│   └── output/                             # Pipeline Outputs
│       └── .gitkeep
│
├── 📚 docs/                                # Documentation
│   ├── README.md                           # Documentation index
│   ├── guides/                             # User Guides
│   │   ├── batch_processing_guide.md       # Batch processing guide
│   │   ├── batch_processing_summary.md     # Batch processing summary
│   │   ├── batch_size_explained.md         # Batch size explanation
│   │   ├── financebench_preprocessing.md   # FinanceBench preprocessing
│   │   ├── gemini_api_limits.md            # Gemini API limits
│   │   ├── retry_logic.md                  # Retry logic
│   │   └── vector_search.md                # Vector search guide
│   ├── api/                                # API Documentation
│   │   ├── extractor-capabilities.md       # Extractor API
│   │   ├── jinja2_templates.md             # Template system
│   │   └── server_usage.md                 # Server API
│   ├── architecture/                       # Architecture Documentation
│   │   ├── KAG_LANGGRAPH_README.md         # Architecture overview
│   │   ├── LANGSMITH_INTEGRATION.md        # LangSmith integration
│   │   └── SAMPLE_SCHEMA_USAGE.md          # Schema usage
│   ├── results/                            # Test Results & Examples
│   │   ├── gemini_vectorizer_tests.md      # Vectorizer test results
│   │   ├── scanner_tests.md                # Scanner test results
│   │   └── neo4j_labels_example.md         # Neo4j label examples
│   └── setup/                              # Setup Guides
│       └── SERVER_SETUP_SUMMARY.md         # Server setup
│
├── 🔧 scripts/                             # Utility Scripts
│   ├── debug/                              # Debug Scripts
│   │   ├── check_trp_invocation.py         # Check TRP invocation
│   │   ├── debug_edge_creation.py          # Debug edge creation
│   │   └── debug_extraction.py             # Debug extraction
│   ├── utilities/                          # Helper Scripts
│   │   ├── delete_empty_chunks.py          # Cleanup utility
│   │   └── inspect_neo4j_schema.py         # Neo4j inspector
│   └── servers/                            # Server Scripts
│       ├── server.py                       # Main server
│       └── start_server.sh                 # Startup script
│
├── 🧪 tests/                               # Test Suite
│   ├── README.md                           # Testing guide
│   ├── e2e/                                # End-to-End Tests
│   │   ├── test_batch_processing.py        # Batch processing test
│   │   ├── test_financebench_extraction.py # FinanceBench E2E test
│   │   └── test_hybrid_search.py           # Hybrid search test
│   ├── component_tests/                    # Component-Specific Tests
│   │   ├── test_check_entities.py          # Entity check test
│   │   ├── test_embedding_dim.py           # Embedding dimension test
│   │   ├── test_extraction.py              # Extraction test
│   │   ├── test_gemini_vectorizer.py       # Gemini vectorizer test
│   │   ├── test_mmbert_splitter.py         # MMBert splitter test
│   │   ├── test_scanner_*.py               # Scanner tests
│   │   ├── test_vector_*.py                # Vector search tests
│   │   └── ... (20+ component tests)
│   ├── integration/                        # Integration Tests
│   │   └── .gitkeep                        # (Ready for integration tests)
│   └── unit/                               # Unit Tests
│       └── .gitkeep                        # (Ready for unit tests)
│
├── 📖 examples/                            # Example Code
│   ├── basic_pipeline.py                   # Basic usage
│   ├── advanced_example.py                 # Advanced usage
│   ├── domain_schema_example.py            # Schema examples
│   ├── template_usage_example.py           # Template examples
│   ├── config.yaml                         # Example config
│   └── config_with_templates.yaml          # Template config
│
└── 🛠️ utils/                               # Global Utilities
    └── helpers.py                          # Helper functions
```

---

## 📊 Quick Stats

| Category | Count | Location |
|----------|-------|----------|
| Documentation | 16 files | `docs/` |
| Guide Files | 7 files | `docs/guides/` |
| API Docs | 3 files | `docs/api/` |
| Architecture Docs | 3 files | `docs/architecture/` |
| Test Results | 3 files | `docs/results/` |
| Data Files | 150+ files | `data/financebench/` |
| Test Files | 25+ files | `tests/` |
| E2E Tests | 3 files | `tests/e2e/` |
| Component Tests | 20+ files | `tests/component_tests/` |
| Debug Scripts | 3 files | `scripts/debug/` |
| Utility Scripts | 2 files | `scripts/utilities/` |
| Server Scripts | 2 files | `scripts/servers/` |
| Core Components | 8 files | `knowledge_graphs/components/` |
| LLM Prompts | 4 files | `knowledge_graphs/prompts/` |
| Graph Schemas | 3 files | `knowledge_graphs/schema/` |

---

## 🎯 Key Directories Explained

### `knowledge_graphs/` - Core Pipeline
The heart of the project. Contains all pipeline components for building knowledge graphs from documents.

**Key files:**
- `components/extractor.py` - Extracts entities and relationships
- `components/financebench_reader.py` - Custom FinanceBench reader
- `prompts/trp.md` - Triple extraction prompt with SPG support

### `chatbot_graphs/` - RAG Chatbot
RAG (Retrieval Augmented Generation) chatbot implementation using the knowledge graph.

**Key files:**
- `rag_graph.py` - Main RAG implementation with hybrid search

### `data/` - All Data
Centralized location for all data files. Never commit data files to git.

**Structure:**
- `financebench/` - Input: FinanceBench financial documents
- `output/` - Output: Generated knowledge graphs and results

### `docs/` - Documentation
Comprehensive documentation organized by category.

**Categories:**
- `guides/` - How-to guides and tutorials
- `api/` - API reference documentation
- `architecture/` - System architecture and design
- `results/` - Test results and examples

### `scripts/` - Utilities
All utility scripts organized by purpose.

**Categories:**
- `debug/` - Debugging and troubleshooting scripts
- `utilities/` - Helper scripts for maintenance
- `servers/` - Server startup and management

### `tests/` - Test Suite
Comprehensive test suite organized by test type.

**Categories:**
- `e2e/` - End-to-end integration tests
- `component_tests/` - Individual component tests
- `integration/` - Cross-component integration tests
- `unit/` - Unit tests for individual functions

---

## 🚀 Quick Start

### Run Pipeline
```bash
# Basic pipeline
python main.py

# FinanceBench pipeline
python -m knowledge_graphs.pipeline.main --config configs/financebench_pipeline.yaml
```

### Run Tests
```bash
# All tests
pytest tests/

# Specific category
pytest tests/e2e/
pytest tests/component_tests/

# Specific test
pytest tests/e2e/test_financebench_extraction.py -v
```

### Run Server
```bash
cd scripts/servers
./start_server.sh
```

### Run Scripts
```bash
# Debug script
python scripts/debug/debug_extraction.py

# Utility script
python scripts/utilities/inspect_neo4j_schema.py
```

---

## 📝 Important Files

### Configuration
- `configs/financebench_pipeline.yaml` - FinanceBench pipeline configuration
- `.env.example` - Environment variables template
- `langgraph.json` - LangGraph server configuration

### Entry Points
- `main.py` - Main pipeline entry point
- `scripts/servers/server.py` - Server entry point
- `chatbot_graphs/rag_graph.py` - RAG chatbot entry point

### Documentation
- `README.md` - Project overview
- `docs/README.md` - Documentation index
- `docs/guides/financebench_preprocessing.md` - FinanceBench guide
- `REORGANIZATION_SUMMARY.md` - This reorganization summary

### Testing
- `tests/README.md` - Testing guide
- `pytest.ini` - Pytest configuration
- `tests/e2e/test_financebench_extraction.py` - FinanceBench E2E test

---

## 🔍 Finding Files

### By Purpose

**Documentation:**
```bash
find docs/ -name "*.md"
```

**Tests:**
```bash
find tests/ -name "test_*.py"
```

**Scripts:**
```bash
find scripts/ -name "*.py"
```

**Data:**
```bash
ls data/financebench/
```

### By Type

**Python files:**
```bash
find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*"
```

**Markdown files:**
```bash
find . -name "*.md"
```

**Configuration files:**
```bash
find . -name "*.yaml" -o -name "*.json" -o -name ".env*"
```

---

## 🎨 Color Legend

- 📄 Configuration & Core Files
- 🧠 Core Pipeline Components
- 💬 Chatbot & RAG System
- 🤖 AI Agents
- ⚙️ Configuration Files
- 📁 Data Storage
- 📚 Documentation
- 🔧 Utility Scripts
- 🧪 Test Suite
- 📖 Examples & Tutorials
- 🛠️ Global Utilities

---

**Structure Version**: 2.0 (Reorganized October 2024)
