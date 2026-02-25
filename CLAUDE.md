# CLAUDE.md

This file provides context for AI agents working on this codebase.

## Project Overview

**thesis-llms-multilayer-graph** is a knowledge graph construction + RAG chatbot system for financial document analysis. It has three main packages:

| Package | Purpose |
|---------|---------|
| `knowledge_graphs/` | Document processing pipeline: Scanner → Reader → Splitter → Extractor → Vectorizer → Writer |
| `rag/` | RAG chatbot: ReAct agent with Neo4j hybrid search (vector + text + entity + chunk) |
| `server/` | FastAPI REST API serving both the pipeline and the chatbot |

## Architecture

```
langgraph.json defines two LangGraph graphs:
  kag_pipeline  → run_server:graph    (KG construction pipeline)
  rag_chatbot   → rag:graph           (RAG chat agent)

run_server.py is the single entry point:
  - Creates the FastAPI app (server/api/app.py)
  - Loads pipeline config from configs/*.yaml
  - Compiles the LangGraph KG pipeline workflow
```

### Data Flow

```
Documents → knowledge_graphs pipeline → Neo4j (entities, relationships, embeddings)
                                              ↓
User question → rag/agent.py (ReAct) → rag/tools/ → rag/retrievers/ → Neo4j
                                              ↓
                                        Answer with citations
```

### Key Singletons

- `server.core.settings.get_settings()` — cached `Settings` instance (Pydantic BaseSettings from `.env`)
- `server.core.llm.create_chat_llm()` — factory for `ChatOpenAI` using centralized settings
- `server.core.database.Neo4jManager.get_instance()` — singleton Neo4j driver (connection pool)
- `rag.retrievers.get_retriever()` — singleton `Neo4jRetriever` combining search + graph mixins

## Package Details

### `knowledge_graphs/`

Pipeline components follow a registry pattern (`utils/registry.py`). Each is a subclass of `BaseComponent`:

- **Scanner** — discovers input files (supports `financebench_reader`, `csv_reader`, `file_scanner`)
- **Reader** — extracts text from PDF/DOCX/TXT/CSV
- **Splitter** — chunks text (semantic or length-based)
- **Extractor** — LLM-based NER → STD → TRP extraction (3-step)
- **Vectorizer** — embeddings via Gemini, Ollama, or sentence-transformers
- **Writer** — writes to Neo4j with SPG schema and edge properties

Pipeline state is defined in `models/pipeline_state.py`. The LangGraph executor is in `pipeline/langgraph_executor.py`.

### `rag/`

- `state.py` — `ChatState` TypedDict with `messages` (LangGraph message list)
- `agent.py` — builds a `create_react_agent` with hybrid search + MCP tools
- `graph.py` — simple `StateGraph`: agent → END. Exports `graph` for `langgraph.json`
- `tools/` — LangChain `@tool` functions wrapping retriever methods
- `retrievers/` — mixin-based: `Neo4jRetrieverBase` + `SearchMixin` + `GraphMixin` = `Neo4jRetriever`
- `prompts/` — Jinja2 markdown templates for the system prompt

The retriever supports 5 search strategies: vector similarity, typed vector, entity graph, semantic path, and question-aware subgraph. The hybrid search tool uses Reciprocal Rank Fusion across 4 strategies.

### `server/`

- `core/settings.py` — all env vars in one Pydantic model, eagerly validated on import
- `core/llm.py` — `create_chat_llm()` (moved from old `utils/llm_factory.py`)
- `core/database.py` — `Neo4jManager` singleton (moved from old `utils/neo4j_manager.py`)
- `core/config.py` — YAML pipeline config loading
- `core/tracing.py` — LangSmith setup
- `api/app.py` — `create_app()` factory with CORS, logging middleware, exception handlers
- `api/routes/` — `health`, `pipeline`, `config`, `auth`, `chat`, `graph`

## Commands

### Development

```bash
# Install dependencies (uses uv)
uv sync

# Install with optional deps
uv sync --extra dev --extra gemini

# Run the FastAPI server
uv run python run_server.py

# Run with uvicorn directly (hot reload)
uv run uvicorn run_server:app --reload

# Run LangGraph dev server
uv run langgraph dev
```

### Testing

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_llm_factory.py -v

# Run with coverage report
uv run pytest tests/unit/ --cov-report=term-missing
```

### Formatting & Linting

```bash
uv run black knowledge_graphs/ rag/ server/ tests/
uv run isort knowledge_graphs/ rag/ server/ tests/
uv run flake8 knowledge_graphs/ rag/ server/
uv run mypy knowledge_graphs/ rag/ server/
```

### Docker

```bash
# Start all services (Neo4j + backend + frontend)
docker compose up -d

# Backend only
docker compose up backend -d
```

## Environment Variables

All settings live in `.env` (see `.env.example`). Key variables:

| Variable | Default | Used By |
|----------|---------|---------|
| `NEO4J_URI` | `bolt://localhost:7687` | database.py, retrievers |
| `NEO4J_PASSWORD` | (required) | database.py |
| `NEO4J_DATABASE` | `neo4j` | database.py |
| `OPENAI_API_KEY` | — | pipeline LLM |
| `CHAT_OPENAI_API_KEY` | falls back to `OPENAI_API_KEY` | chat LLM |
| `CHAT_OPENAI_BASE_URL` | — | custom LLM endpoint |
| `CHAT_LLM_MODEL` | `gpt-4o-mini` | chat LLM |
| `GOOGLE_API_KEY` | — | Gemini embeddings |
| `EMBEDDING_PROVIDER` | `gemini` | vectorizer |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | vectorizer |
| `PIPELINE_CONFIG_PATH` | `configs/financebench_pipeline.yaml` | pipeline |
| `SECRET_KEY` | `change-me-in-production` | JWT auth |
| `MCP_SERVER_URL` | — | MCP tools |

## Code Conventions

- **Python 3.11+** required. Tested on 3.11 and 3.12.
- **Black** formatter, 100 char line length.
- **isort** with black profile.
- **Relative imports** inside packages (`from .state import ChatState`), absolute for cross-package (`from server.core.llm import create_chat_llm`).
- **Pydantic v2** for all models and settings.
- **Type hints** encouraged but not enforced (`disallow_untyped_defs = false` in mypy).
- Tests use **pytest** with **pytest-mock** for patching. Fixtures in `tests/conftest.py`.
- Test files follow `test_*.py` pattern, classes `Test*`, functions `test_*`.

## Import Map (Cross-Package)

```
rag/agent.py          → server.core.llm.create_chat_llm
rag/retrievers/base.py → server.core.database.Neo4jManager
rag/tools/graph.py    → rag.retrievers.get_retriever
rag/tools/search.py   → rag.retrievers.get_retriever
server/api/routes/chat.py  → rag.agent.get_react_agent
server/api/routes/graph.py → rag.retrievers.get_retriever
run_server.py         → server.api.app.create_app
                      → knowledge_graphs.pipeline.langgraph_executor.LangGraphExecutor
```

## Common Pitfalls

- **`langgraph.json` paths resolve from project root** — a `src/` layout would break `langgraph dev`.
- **`Settings` validates eagerly on import** — missing required env vars will crash at startup, not at first use. Always set `NEO4J_PASSWORD` even in tests (see `conftest.py`).
- **Neo4jManager is a singleton** — call `Neo4jManager.reset()` between tests to avoid state leaking.
- **Embedding dimension must match Neo4j index** — Gemini uses 3072-dim, sentence-transformers uses 768-dim. Mismatch causes silent search failures.
- **MCP tools are optional** — `_load_mcp_tools()` in `rag/agent.py` catches ImportError gracefully.
