# Multilayer Graph RAG: Knowledge Graph Construction & Retrieval-Augmented Generation

A full-stack system for building knowledge graphs from financial documents and querying them with a RAG chatbot. Built on LangGraph, Neo4j, and FastAPI.

## What It Does

```
Documents (PDF/CSV/TXT) → KG Pipeline → Neo4j SPG Knowledge Graph
                                                    ↓
                     User Question → ReAct Agent → Hybrid Search → Answer
```

**Knowledge Graph Pipeline** — Processes financial documents through a 6-stage LangGraph workflow (Scanner → Reader → Splitter → Extractor → Vectorizer → Writer) to build a Semantic Property Graph in Neo4j.

**RAG Chatbot** — A ReAct agent that answers financial questions using hybrid retrieval (vector similarity + keyword + entity graph + chunk text search) fused with Reciprocal Rank Fusion.

**REST API** — FastAPI server exposing both the pipeline and chatbot, with JWT auth, CORS, and a React frontend.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Neo4j 5+ (or use Docker)

### Installation

```bash
# Clone and install
git clone https://github.com/duykhang2211/thesis-llms-multilayer-graph.git
cd thesis-llms-multilayer-graph
uv sync

# With optional dependencies (Gemini embeddings, evaluation tools, etc.)
uv sync --extra gemini --extra dev --extra eval
```

### Configuration

```bash
# Copy and edit environment variables
cp .env.example .env
# Edit .env with your API keys and Neo4j credentials
```

Key variables to set:
- `NEO4J_PASSWORD` — your Neo4j password
- `OPENAI_API_KEY` — for LLM extraction and chat
- `GOOGLE_API_KEY` — for Gemini embeddings (if using `gemini` provider)

### Run

```bash
# Start the server
uv run python run_server.py

# Or with hot reload
uv run uvicorn run_server:app --reload

# Or with LangGraph dev server
uv run langgraph dev
```

### Docker

```bash
# Start Neo4j + backend + frontend
docker compose up -d

# Access:
#   Backend API:  http://localhost:8000/docs
#   Frontend:     http://localhost:3000
#   Neo4j:        http://localhost:7474
```

## Project Structure

```
thesis-llms-multilayer-graph/
├── knowledge_graphs/          # KG construction pipeline
│   ├── components/            #   Scanner, Reader, Splitter, Extractor, Vectorizer, Writer
│   ├── models/                #   Chunk, SubGraph, Node, Edge, PipelineState
│   ├── pipeline/              #   LangGraph executor, batch processors
│   ├── prompts/               #   LLM extraction prompt templates
│   ├── schema/                #   SPG schema definitions
│   └── utils/                 #   Component registry, LLM client, template loader
├── rag/                       # RAG chatbot
│   ├── agent.py               #   ReAct agent with tool binding
│   ├── graph.py               #   LangGraph workflow (agent → END)
│   ├── state.py               #   ChatState definition
│   ├── tools/                 #   Neo4j search tools, MCP integration
│   ├── retrievers/            #   Neo4j retriever (vector + text + entity + graph)
│   └── prompts/               #   System prompt templates (Jinja2)
├── server/                    # FastAPI server
│   ├── api/                   #   Routes, middleware, exception handlers
│   │   └── routes/            #     health, pipeline, config, auth, chat, graph
│   └── core/                  #   Settings, LLM factory, Neo4j manager, tracing
│       ├── settings.py        #     Centralized Pydantic settings
│       ├── llm.py             #     ChatOpenAI factory
│       ├── database.py        #     Neo4j singleton manager
│       └── config.py          #     YAML pipeline config loader
├── tests/                     # Test suite (unit, e2e, component)
├── web/                       # React frontend (Vite)
├── configs/                   # Pipeline YAML configurations
├── notebooks/                 # Evaluation & exploration notebooks
├── examples/                  # Example scripts and configs
├── docs/                      # Documentation and guides
├── langgraph.json             # LangGraph graph registry
├── pyproject.toml             # Project metadata and dependencies
├── docker-compose.yml         # Docker services (Neo4j + backend + frontend)
├── Dockerfile                 # Backend container
└── run_server.py              # Main entry point
```

## Architecture

### Three Packages

| Package | Description | Entry Point |
|---------|-------------|-------------|
| `knowledge_graphs` | Document → KG pipeline with 6 pluggable components | `LangGraphExecutor` |
| `rag` | RAG chatbot with ReAct agent and 5 retrieval strategies | `rag:graph` |
| `server` | FastAPI REST API with JWT auth, centralized settings | `run_server:app` |

### LangGraph Graphs

Defined in `langgraph.json`:

- **`kag_pipeline`** (`run_server:graph`) — Multi-stage document processing pipeline
- **`rag_chatbot`** (`rag:graph`) — ReAct agent chat workflow

### Retrieval Strategies

The RAG chatbot supports 5 search strategies via `rag/retrievers/`:

1. **Vector similarity search** — semantic matching on entity embeddings
2. **Typed vector search** — type-filtered search (SPG-aware)
3. **Entity graph search** — relationship traversal with auto-expansion
4. **Semantic path search** — multi-hop path discovery between entities
5. **Question-aware subgraph retrieval** — intelligent subgraph extraction

The default **hybrid search** tool fuses 4 strategies using Reciprocal Rank Fusion (RRF).

### Pipeline Components

```
Scanner → Reader → Splitter → Extractor → Vectorizer → Writer
```

Each component is pluggable via YAML config (see `configs/`). The extractor uses a 3-step LLM pipeline: Named Entity Recognition → Standardization → Triple Extraction.

## Development

### Testing

```bash
# Unit tests
uv run pytest tests/unit/ -v

# All tests with coverage
uv run pytest --cov-report=term-missing

# Specific test
uv run pytest tests/unit/test_llm_factory.py -v
```

### Code Quality

```bash
uv run black knowledge_graphs/ rag/ server/ tests/
uv run isort knowledge_graphs/ rag/ server/ tests/
uv run flake8 knowledge_graphs/ rag/ server/
```

### Configuration

Pipeline behavior is controlled by YAML files in `configs/`:

- `financebench_pipeline.yaml` — FinanceBench financial statement processing
- `vn30_pipeline.yaml` — VN30 Vietnamese stock market data

All environment settings are centralized in `server/core/settings.py` using Pydantic BaseSettings. See `.env.example` for the full list.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/pipeline/run` | POST | Run KG pipeline on a document |
| `/pipeline/run-batch` | POST | Batch document processing |
| `/chat/chat` | POST | Send message to RAG chatbot |
| `/graph/data` | GET | Get graph visualization data |
| `/docs` | GET | Swagger API documentation |

## Tech Stack

- **LangGraph** — stateful workflow orchestration
- **LangChain** — LLM integration (OpenAI, Gemini, Ollama)
- **Neo4j** — graph database with vector index support
- **FastAPI** — REST API with async support
- **Pydantic v2** — settings validation and data models
- **React + Vite** — frontend web application
- **Docker** — containerized deployment

## License

Apache 2.0 License — see [LICENSE](LICENSE) for details.
