# KAG-LangGraph Pipeline Server

REST API server for running KAG-LangGraph knowledge extraction pipelines.

## Quick Start

```bash
# From project root
python run_server.py

# Or with uvicorn (recommended for development)
uvicorn run_server:app --reload

# Or as executable
./run_server.py

# Or with startup script
./start_server.sh

# Or with custom host/port
SERVER_HOST=0.0.0.0 SERVER_PORT=8080 python run_server.py

# Or with custom pipeline config
PIPELINE_CONFIG_PATH=configs/my_pipeline.yaml python run_server.py
```

## Directory Structure

```
server/
├── api/                         # API Layer
│   ├── app.py                   # FastAPI app factory
│   ├── models/                  # Pydantic models
│   │   ├── requests.py          # Request models
│   │   └── responses.py         # Response models
│   └── routes/                  # Route modules
│       ├── health.py            # Health check endpoints
│       ├── pipeline.py          # Pipeline execution endpoints
│       └── config.py            # Configuration endpoints
├── core/                        # Core Utilities
│   ├── config.py                # Configuration management
│   ├── tracing.py               # LangSmith tracing setup
│   └── logging_config.py        # Logging configuration
└── utils/                       # Helper Utilities
    └── helpers.py               # Helper functions
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### Health
- `GET /` - API information
- `GET /health` - Health check

### Pipeline Execution
- `POST /pipeline/run` - Run pipeline synchronously
- `POST /pipeline/run-batch` - Run pipeline in batches
- `POST /pipeline/run-async` - Run pipeline asynchronously
- `POST /pipeline/stream` - Stream pipeline execution
- `POST /pipeline/upload-and-run` - Upload file and run

### Configuration
- `GET /pipeline/config` - Get default configuration
- `GET /pipeline/components` - List available components

## Environment Variables

```bash
SERVER_HOST=0.0.0.0              # Server host
SERVER_PORT=8000                 # Server port
SERVER_RELOAD=false              # Auto-reload on code changes
LOG_LEVEL=info                   # Logging level

# LangSmith Tracing (optional)
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=kag-langgraph-server
```

## Example Usage

```bash
# Run pipeline
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"input_path": "./data/financebench"}'

# Run in batches
curl -X POST http://localhost:8000/pipeline/run-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "./data/financebench",
    "batch_size": 10
  }'

# Get configuration
curl http://localhost:8000/pipeline/config
```

## Development

Run with auto-reload:
```bash
uvicorn run_server:app --reload --log-level debug

# Or with startup script
./start_server.sh --reload --log-level debug
```

## Configuration

### Environment Variables

- **Server Configuration**:
  - `SERVER_HOST` - Host to bind to (default: `0.0.0.0`)
  - `SERVER_PORT` - Port to listen on (default: `8000`)
  - `SERVER_RELOAD` - Enable auto-reload (default: `false`)
  - `LOG_LEVEL` - Logging level (default: `info`)

- **Pipeline Configuration**:
  - `PIPELINE_CONFIG_PATH` - Path to pipeline YAML config (default: `configs/financebench_pipeline.yaml`)
  - Supports environment variable substitution in YAML: `${VAR_NAME}` or `${VAR_NAME:default_value}`

### Pipeline Config File

The server loads pipeline configuration from a YAML file specified by `PIPELINE_CONFIG_PATH`.

**Example** (`configs/financebench_pipeline.yaml`):
```yaml
components:
  extractor:
    type: "llm_extractor"
    enabled: true
    config:
      llm_provider: "openai"
      model: "gpt-4"
      api_key: "${OPENAI_API_KEY}"  # Environment variable substitution

  writer:
    type: "neo4j_writer"
    enabled: true
    config:
      uri: "${NEO4J_URI:bolt://localhost:7687}"  # With default value
      username: "${NEO4J_USERNAME}"
      password: "${NEO4J_PASSWORD}"
```

**Fallback**: If config file is not found, uses `DEFAULT_CONFIG` from `server/core/config.py`.

## Architecture

The server uses a modular architecture with clear separation of concerns:

- **Entry Point**: `run_server.py` at project root serves as a thin wrapper
- **API Layer**: `server/api/` contains FastAPI routes, models, and app factory
- **Core Layer**: `server/core/` provides configuration, tracing, and logging
- **Utils Layer**: `server/utils/` contains helper functions

This structure provides:
- ✅ Clean separation of concerns
- ✅ Easy to test and maintain
- ✅ Modular and extensible
- ✅ Professional project layout
