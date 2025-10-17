# Project Reorganization Plan

## Current Issues

1. **Root directory clutter**: 30+ test files and scripts in root
2. **Documentation scattered**: Multiple .md files in root instead of docs/
3. **Mixed concerns**: Debug scripts, test files, and production code mixed
4. **Duplicate files**: Multiple test files for similar functionality
5. **No clear structure**: Hard to find specific files

---

## Proposed New Structure

```
thesis-llms-multilayer-graph/
├── README.md                          # Main project README
├── LICENSE                            # License file
├── requirements.txt                   # Python dependencies
├── setup.py                           # Package setup
├── pytest.ini                         # Pytest configuration
├── langgraph.json                     # LangGraph configuration
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
│
├── docs/                              # 📚 All Documentation
│   ├── README.md                      # Docs index
│   ├── setup/
│   │   ├── installation.md            # Setup instructions
│   │   └── configuration.md           # Configuration guide
│   ├── guides/
│   │   ├── financebench_preprocessing.md  # FinanceBench guide
│   │   ├── batch_processing.md        # Batch processing guide
│   │   ├── batch_size.md              # Batch size explanation
│   │   ├── gemini_api_limits.md       # API limits analysis
│   │   ├── retry_logic.md             # Retry implementation
│   │   └── vector_search.md           # Vector search guide
│   ├── api/
│   │   ├── extractor_capabilities.md  # Extractor API docs
│   │   ├── jinja2_templates.md        # Template system docs
│   │   └── server_usage.md            # Server API usage
│   ├── architecture/
│   │   ├── kag_langgraph.md           # Architecture overview
│   │   ├── langsmith_integration.md   # LangSmith setup
│   │   └── sample_schema_usage.md     # Schema examples
│   └── results/
│       ├── gemini_vectorizer_tests.md # Test results
│       ├── scanner_tests.md           # Scanner results
│       └── neo4j_labels_example.md    # Neo4j examples
│
├── configs/                           # ⚙️ Configuration Files
│   ├── financebench_pipeline.yaml     # FinanceBench config
│   └── config.py                      # Python config module
│
├── knowledge_graphs/                  # 🧠 Core Pipeline
│   ├── __init__.py
│   ├── components/                    # Pipeline components
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── scanner.py
│   │   ├── reader.py
│   │   ├── financebench_reader.py     # Custom reader
│   │   ├── splitter.py
│   │   ├── extractor.py
│   │   ├── vectorizer.py
│   │   └── writer.py
│   ├── models/                        # Data models
│   │   ├── __init__.py
│   │   ├── chunk.py
│   │   ├── graph.py
│   │   └── pipeline_state.py
│   ├── pipeline/                      # Pipeline execution
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── langgraph_executor.py
│   │   └── batch_processor.py
│   ├── prompts/                       # LLM prompts
│   │   ├── ner.md                     # Named entity recognition
│   │   ├── std.md                     # Standardization
│   │   ├── trp.md                     # Triple extraction
│   │   └── kn.md                      # Knowledge normalization
│   ├── schema/                        # Graph schemas
│   │   ├── financebench.schema        # Original schema
│   │   ├── financebench_spg.schema    # SPG schema
│   │   └── sample.schema              # Sample schema
│   └── utils/                         # Utilities
│       ├── __init__.py
│       ├── llm_client.py
│       ├── registry.py
│       └── template_loader.py
│
├── chatbot_graphs/                    # 💬 RAG Chatbot
│   ├── README.md                      # Chatbot documentation
│   ├── .env.example                   # Chatbot env template
│   ├── rag_graph.py                   # Main RAG implementation
│   ├── GEMINI_EMBEDDINGS.md           # Embeddings guide
│   ├── test_llm_connection.py         # Connection test
│   └── test_llm_simple.py             # Simple LLM test
│
├── agents/                            # 🤖 Agent Implementations
│   └── rag_agent.py                   # RAG agent
│
├── data/                              # 📁 Data Files
│   ├── financebench/                  # FinanceBench dataset
│   │   └── financebench_id_*.txt      # Financial documents
│   └── output/                        # Pipeline outputs
│       └── .gitkeep
│
├── scripts/                           # 🔧 Utility Scripts
│   ├── debug/                         # Debug scripts
│   │   ├── debug_extraction.py
│   │   ├── debug_edge_creation.py
│   │   └── check_trp_invocation.py
│   ├── utilities/                     # Helper scripts
│   │   ├── delete_empty_chunks.py
│   │   └── inspect_neo4j_schema.py
│   └── servers/
│       ├── server.py                  # Main server
│       └── start_server.sh            # Server startup script
│
├── tests/                             # 🧪 All Tests
│   ├── README.md                      # Testing guide
│   ├── conftest.py                    # Pytest configuration
│   │
│   ├── unit/                          # Unit tests
│   │   ├── test_components.py
│   │   ├── test_schema_parsing.py
│   │   └── test_template_loading.py
│   │
│   ├── integration/                   # Integration tests
│   │   ├── test_extractor_and_vectorizer.py
│   │   ├── test_langsmith_integration.py
│   │   ├── test_sample_schema.py
│   │   └── test_server.py
│   │
│   ├── e2e/                           # End-to-end tests
│   │   ├── test_financebench_extraction.py
│   │   ├── test_batch_processing.py
│   │   └── test_hybrid_search.py
│   │
│   └── component_tests/               # Component-specific tests
│       ├── test_scanner_*.py
│       ├── test_gemini_vectorizer.py
│       ├── test_mmbert_splitter.py
│       ├── test_extraction.py
│       ├── test_vector_*.py
│       ├── test_ollama_entity.py
│       ├── test_rate_limit_threshold.py
│       ├── test_retry_logic.py
│       ├── test_embedding_dim.py
│       ├── test_format_issue.py
│       ├── test_json_extraction.py
│       ├── test_lower_threshold.py
│       ├── test_check_entities.py
│       └── test_template_*.py
│
├── examples/                          # 📖 Example Code
│   ├── basic_pipeline.py              # Basic usage
│   ├── advanced_example.py            # Advanced usage
│   ├── domain_schema_example.py       # Schema examples
│   ├── template_usage_example.py      # Template examples
│   ├── config.yaml                    # Example config
│   └── config_with_templates.yaml     # Template config
│
├── utils/                             # 🛠️ Global Utilities
│   └── helpers.py                     # Helper functions
│
└── main.py                            # 🚀 Main Entry Point
```

---

## File Migration Plan

### Phase 1: Create New Directory Structure
```bash
mkdir -p data/financebench
mkdir -p data/output
mkdir -p scripts/debug
mkdir -p scripts/utilities
mkdir -p scripts/servers
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/e2e
mkdir -p tests/component_tests
mkdir -p docs/setup
mkdir -p docs/guides
mkdir -p docs/api
mkdir -p docs/architecture
mkdir -p docs/results
```

### Phase 2: Move Documentation Files
```bash
# Move all .md files from root to docs/guides/
mv BATCH_PROCESSING_GUIDE.md docs/guides/batch_processing.md
mv BATCH_PROCESSING_SUMMARY.md docs/guides/batch_processing_summary.md
mv BATCH_SIZE_EXPLAINED.md docs/guides/batch_size.md
mv FINANCEBENCH_PREPROCESSING_GUIDE.md docs/guides/financebench_preprocessing.md
mv GEMINI_API_RATE_LIMITS_ANALYSIS.md docs/guides/gemini_api_limits.md
mv GEMINI_VECTORIZER_TEST_RESULTS.md docs/results/gemini_vectorizer_tests.md
mv RETRY_LOGIC_IMPLEMENTATION.md docs/guides/retry_logic.md
mv SCANNER_TEST_RESULTS.md docs/results/scanner_tests.md
mv VECTOR_SEARCH_SUMMARY.md docs/guides/vector_search.md
mv neo4j_labels_example.md docs/results/neo4j_labels_example.md

# Move docs/ subdirectory files
# (keep them in docs/ but rename for consistency)
```

### Phase 3: Move Data Files
```bash
# Move FinanceBench data
mv financebench_data/ data/financebench/

# Move output directory
mv output/ data/output/
```

### Phase 4: Move Scripts
```bash
# Debug scripts
mv debug_extraction.py scripts/debug/
mv debug_edge_creation.py scripts/debug/
mv check_trp_invocation.py scripts/debug/

# Utility scripts
mv delete_empty_chunks.py scripts/utilities/
mv inspect_neo4j_schema.py scripts/utilities/

# Server scripts
mv server.py scripts/servers/
mv start_server.sh scripts/servers/
```

### Phase 5: Move Test Files
```bash
# E2E tests
mv test_financebench_extraction.py tests/e2e/
mv test_batch_processing.py tests/e2e/
mv test_hybrid_search.py tests/e2e/

# Component tests
mv test_scanner_*.py tests/component_tests/
mv test_gemini_vectorizer.py tests/component_tests/
mv test_mmbert_splitter.py tests/component_tests/
mv test_extraction.py tests/component_tests/
mv test_vector_*.py tests/component_tests/
mv test_ollama_entity.py tests/component_tests/
mv test_rate_limit_threshold.py tests/component_tests/
mv test_retry_logic.py tests/component_tests/
mv test_embedding_dim.py tests/component_tests/
mv test_format_issue.py tests/component_tests/
mv test_json_extraction.py tests/component_tests/
mv test_lower_threshold.py tests/component_tests/
mv test_check_entities.py tests/component_tests/

# Keep tests/test_*.py in tests/integration/ or tests/unit/ based on type
```

### Phase 6: Update Import Paths
After moving files, update import statements in:
- All moved test files (update relative imports)
- Configuration files (update file paths)
- Server files (update data paths)

### Phase 7: Update Configuration Files
```yaml
# Update configs/financebench_pipeline.yaml
components:
  scanner:
    config:
      input_paths:
        - "./data/financebench"  # Updated path
```

### Phase 8: Update .gitignore
```gitignore
# Add to .gitignore
data/output/
data/financebench/*
!data/financebench/.gitkeep
__pycache__/
*.pyc
.env
.venv/
.pytest_cache/
.DS_Store
```

---

## Benefits of New Structure

### 1. **Clear Separation of Concerns**
- Production code: `knowledge_graphs/`, `chatbot_graphs/`, `agents/`
- Tests: `tests/` with subdirectories by type
- Scripts: `scripts/` for utilities
- Data: `data/` for inputs/outputs
- Docs: `docs/` for all documentation

### 2. **Easy Navigation**
```bash
# Find tests
cd tests/component_tests/

# Find documentation
cd docs/guides/

# Run scripts
cd scripts/utilities/
```

### 3. **Better Git Management**
- Clear .gitignore patterns
- Organized commit history
- Easy to track changes by directory

### 4. **Professional Structure**
- Follows Python best practices
- Similar to popular open-source projects
- Easy onboarding for new developers

### 5. **Scalability**
- Easy to add new components
- Clear place for new tests
- Organized documentation growth

---

## Files to Keep in Root

```
thesis-llms-multilayer-graph/
├── README.md              # Project overview
├── LICENSE                # License
├── requirements.txt       # Dependencies
├── setup.py               # Package setup
├── pytest.ini             # Test configuration
├── langgraph.json         # LangGraph config
├── .env.example           # Environment template
├── .gitignore             # Git ignore
└── main.py                # Main entry point
```

---

## Quick Migration Script

```bash
#!/bin/bash
# File: reorganize_project.sh

echo "Creating new directory structure..."
mkdir -p data/{financebench,output}
mkdir -p scripts/{debug,utilities,servers}
mkdir -p tests/{unit,integration,e2e,component_tests}
mkdir -p docs/{setup,guides,api,architecture,results}

echo "Moving documentation..."
mv *_GUIDE.md docs/guides/ 2>/dev/null
mv *_SUMMARY.md docs/guides/ 2>/dev/null
mv *_EXPLAINED.md docs/guides/ 2>/dev/null
mv *_ANALYSIS.md docs/guides/ 2>/dev/null
mv *_RESULTS.md docs/results/ 2>/dev/null
mv *_IMPLEMENTATION.md docs/guides/ 2>/dev/null
mv neo4j_labels_example.md docs/results/ 2>/dev/null

echo "Moving data..."
mv financebench_data data/financebench 2>/dev/null
mv output data/ 2>/dev/null

echo "Moving scripts..."
mv debug_*.py scripts/debug/ 2>/dev/null
mv check_*.py scripts/debug/ 2>/dev/null
mv delete_*.py scripts/utilities/ 2>/dev/null
mv inspect_*.py scripts/utilities/ 2>/dev/null
mv server.py scripts/servers/ 2>/dev/null
mv start_server.sh scripts/servers/ 2>/dev/null

echo "Moving tests..."
mv test_financebench_*.py tests/e2e/ 2>/dev/null
mv test_batch_*.py tests/e2e/ 2>/dev/null
mv test_hybrid_*.py tests/e2e/ 2>/dev/null
mv test_scanner_*.py tests/component_tests/ 2>/dev/null
mv test_*.py tests/component_tests/ 2>/dev/null

echo "Reorganization complete!"
echo "Remember to update import paths in moved files."
```

---

## Post-Migration Checklist

- [ ] Run migration script
- [ ] Update import paths in all moved files
- [ ] Update configuration file paths
- [ ] Update .gitignore
- [ ] Test that all imports work
- [ ] Run test suite: `pytest tests/`
- [ ] Update documentation links
- [ ] Commit changes with descriptive message
- [ ] Update README.md with new structure

---

## Rollback Plan

If issues occur:
```bash
git stash  # Stash current changes
git checkout HEAD~1  # Go back to previous commit
# Or restore specific files
```

Keep a backup before reorganizing:
```bash
tar -czf project_backup_$(date +%Y%m%d).tar.gz .
```
