"""
FastAPI server for KAG-LangGraph pipeline.

This module provides a REST API server to run the KAG-LangGraph workflow
with support for synchronous, asynchronous, and streaming execution modes.
"""

import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.info("python-dotenv not available, using system environment variables")

# LangSmith tracing imports
try:
    from langsmith import Client, traceable
    from langsmith.wrappers import wrap_openai
    import langchain
    from langchain.callbacks import LangChainTracer
    HAS_LANGSMITH = True
    logger.info("LangSmith tracing available")
except ImportError as e:
    logger.warning(f"LangSmith not available: {e}")
    HAS_LANGSMITH = False
    # Create dummy decorator for when LangSmith is not available
    def traceable(name=None, **kwargs):
        def decorator(func):
            return func
        return decorator

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    from knowledge_graphs.pipeline.langgraph_executor import LangGraphExecutor, PipelineWorkflow
    from knowledge_graphs.models.pipeline_state import PipelineStateManager
    from knowledge_graphs.pipeline.batch_processor import BatchPipelineProcessor, process_directory_in_batches
    HAS_KAG_LANGGRAPH = True
except ImportError as e:
    logger.warning(f"KAG-LangGraph components not available: {e}")
    HAS_KAG_LANGGRAPH = False
    # Create dummy classes for development
    class LangGraphExecutor:
        def __init__(self, config):
            self.config = config

    class PipelineWorkflow:
        def __init__(self, config=None, config_path=None):
            self.config = config or {}

        def run_pipeline(self, input_path, **kwargs):
            return {
                "pipeline_id": "dummy-id",
                "status": "error",
                "input_path": input_path,
                "output_path": None,
                "metrics": {},
                "errors": ["KAG-LangGraph components not available"],
                "execution_summary": {"error": "Missing dependencies"}
            }

        async def arun_pipeline(self, input_path, **kwargs):
            return self.run_pipeline(input_path, **kwargs)

        def stream_pipeline(self, input_path, **kwargs):
            yield {
                "error": "KAG-LangGraph components not available",
                "timestamp": datetime.utcnow().isoformat()
            }

        def get_pipeline_info(self):
            return {
                "components": {},
                "workflow_nodes": 0
            }


# Default configuration for the pipeline
DEFAULT_CONFIG = {
    "pipeline": {
        "components": {
            "scanner": {
                "type": "file_scanner",
                "enabled": True
            },
            "reader": {
                "type": "txt_reader",
                "enabled": True
            },
            "splitter": {
                "type": "semantic_splitter",
                "enabled": True,
                "config": {
                    "model_name": "jhu-clsp/mmBERT-small",
                    "similarity_threshold": 0.95,
                    "min_chunk_length": 100,
                    "max_chunk_length": 500
                }
            },
            "extractor": {
                "type": "llm_extractor",
                "enabled": True,
                "config": {
                    "llm_provider": "openai",
                    "model": "gpt-5-mini",
                    "temperature": 1,
                    "max_tokens": 4096,
                    "use_template": True,
                    "extraction_schema": "knowledge_graphs/schema/financebench_spg.schema",
                    "batch_size": 5
                }
            },
            "vectorizer": {
                "type": "gemini_vectorizer",        # "type": "openai_vectorizer",
                "model": "gemini-embedding-001",    # "model": "text-embedding-embeddinggemma-300m",
                                                    # "api_key": "lm-studio",
                                                    # "base_url": "https://llm.duykhangh.net/v1",
                "max_tokens": 4096,
                "embed_nodes": True,
                "embed_edges": True,
                "batch_size": 100,                  # Paid Tier 1 optimal batch size
                "max_retries": 3,                   # Retry up to 3 times on rate limit
                "retry_delay": 10,                  # Initial delay: 10s (then 20s, 40s with exponential backoff)
                "enabled": True
            },
            "writer": {
                "type": "neo4j_writer",
                "enabled": True,
                "config": {
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "neo4j@openspg",
                    "database": "financebench1",
                    "clear_database": True
                }
            }
        }
    }
}

# Pydantic models for API requests and responses
class PipelineRequest(BaseModel):
    """Request model for pipeline execution."""
    input_path: str = Field(..., description="Path to input file or directory")
    config: Optional[Dict[str, Any]] = Field(None, description="Custom pipeline configuration")
    output_path: Optional[str] = Field(None, description="Custom output path")
    batch_size: Optional[int] = Field(10, description="Number of files to process per batch (for directory processing)")

class PipelineResponse(BaseModel):
    """Response model for pipeline execution."""
    pipeline_id: str
    status: str
    input_path: str
    output_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    execution_summary: Optional[Dict[str, Any]] = None
    timestamp: str

class PipelineStatus(BaseModel):
    """Model for pipeline status information."""
    pipeline_id: str
    status: str
    current_component: Optional[str] = None
    progress: float = 0.0
    errors: List[str] = []
    timestamp: str

# Global storage for running pipelines (in production, use Redis or database)
running_pipelines: Dict[str, Dict[str, Any]] = {}

def setup_langsmith_tracing():
    """Setup LangSmith tracing configuration."""
    if not HAS_LANGSMITH:
        logger.info("LangSmith tracing disabled (not installed)")
        return None

    # Get LangSmith configuration from environment
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    langsmith_project = os.getenv("LANGSMITH_PROJECT", "kag-langgraph-server")
    langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    if not langsmith_api_key:
        logger.warning("LANGSMITH_API_KEY not set. LangSmith tracing disabled.")
        return None

    try:
        # Initialize LangSmith client
        client = Client(
            api_url=langsmith_endpoint,
            api_key=langsmith_api_key
        )

        # Set environment variables for LangChain integration
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        os.environ["LANGCHAIN_ENDPOINT"] = langsmith_endpoint
        os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key

        logger.info(f"LangSmith tracing enabled for project: {langsmith_project}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith: {e}")
        return None

def check_fastapi_dependency():
    """Check if FastAPI is available."""
    if not HAS_FASTAPI:
        raise ImportError(
            "FastAPI is required to run the server. Install with: pip install fastapi uvicorn"
        )

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    check_fastapi_dependency()

    # Setup LangSmith tracing
    langsmith_client = setup_langsmith_tracing()

    app = FastAPI(
        title="KAG-LangGraph Pipeline Server",
        description="REST API server for running KAG-LangGraph knowledge extraction pipelines",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Store LangSmith client in app state for access in endpoints
    app.state.langsmith_client = langsmith_client

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app

app = create_app() if HAS_FASTAPI else None

if HAS_FASTAPI:
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "KAG-LangGraph Pipeline Server",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "kag-langgraph-server"
        }

    @app.post("/pipeline/run", response_model=PipelineResponse)
    @traceable(name="pipeline_run_sync")
    async def run_pipeline(request: PipelineRequest):
        """
        Run the pipeline synchronously on the provided input.

        Args:
            request: Pipeline execution request

        Returns:
            Pipeline execution results
        """
        try:
            # Add tracing metadata
            if HAS_LANGSMITH:
                try:
                    from langsmith import get_current_run_tree
                    run_tree = get_current_run_tree()
                    if run_tree:
                        run_tree.add_metadata({
                            "execution_mode": "synchronous",
                            "server_version": "1.0.0",
                            "input_path": request.input_path,
                            "output_path": request.output_path,
                            "has_custom_config": request.config is not None
                        })
                except Exception as e:
                    logger.debug(f"Failed to add tracing metadata: {e}")

            # Use custom config if provided, otherwise use default
            config = request.config if request.config else DEFAULT_CONFIG.copy()

            # Update output path if provided
            if request.output_path:
                config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path

            # Create pipeline workflow
            workflow = PipelineWorkflow(config=config)

            # Run pipeline
            results = workflow.run_pipeline(request.input_path)

            # Convert to response model
            metrics = results.get("metrics")
            if metrics and hasattr(metrics, 'dict'):
                metrics = metrics.dict()
            elif metrics and not isinstance(metrics, dict):
                metrics = dict(metrics) if hasattr(metrics, '__dict__') else {}

            response = PipelineResponse(
                pipeline_id=results["pipeline_id"],
                status=results["status"],
                input_path=results["input_path"],
                output_path=results.get("output_path"),
                metrics=metrics,
                errors=results.get("errors", []),
                execution_summary=results.get("execution_summary"),
                timestamp=datetime.utcnow().isoformat()
            )

            return response

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/pipeline/run-batch", response_model=PipelineResponse)
    @traceable(name="pipeline_run_batch")
    async def run_pipeline_batch(request: PipelineRequest):
        """
        Run the pipeline on a directory processing files in batches.

        This endpoint processes files in batches to avoid memory issues
        when dealing with large numbers of files.

        Args:
            request: Pipeline execution request with batch_size parameter

        Returns:
            Aggregated pipeline execution results from all batches
        """
        try:
            # Add tracing metadata
            if HAS_LANGSMITH:
                try:
                    from langsmith import get_current_run_tree
                    run_tree = get_current_run_tree()
                    if run_tree:
                        run_tree.add_metadata({
                            "execution_mode": "batch",
                            "batch_size": request.batch_size,
                            "server_version": "1.0.0",
                            "input_path": request.input_path,
                            "output_path": request.output_path,
                            "has_custom_config": request.config is not None
                        })
                except Exception as e:
                    logger.debug(f"Failed to add tracing metadata: {e}")

            # Use custom config if provided, otherwise use default
            config = request.config if request.config else DEFAULT_CONFIG.copy()

            # Update output path if provided
            if request.output_path:
                config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path

            # Use batch processor
            logger.info(f"Starting batch processing with batch_size={request.batch_size}")
            results = process_directory_in_batches(
                request.input_path,
                config,
                batch_size=request.batch_size
            )

            # Convert to response model
            metrics = results.get("metrics")
            if metrics and hasattr(metrics, 'dict'):
                metrics = metrics.dict()
            elif metrics and not isinstance(metrics, dict):
                metrics = dict(metrics) if hasattr(metrics, '__dict__') else {}

            response = PipelineResponse(
                pipeline_id=results["pipeline_id"],
                status=results["status"],
                input_path=results["input_path"],
                output_path=results.get("output_path"),
                metrics=metrics,
                errors=results.get("errors", []),
                execution_summary=results.get("execution_summary"),
                timestamp=datetime.utcnow().isoformat()
            )

            return response

        except Exception as e:
            logger.error(f"Batch pipeline execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/pipeline/run-async", response_model=PipelineResponse)
    @traceable(name="pipeline_run_async")
    async def run_pipeline_async(request: PipelineRequest):
        """
        Run the pipeline asynchronously on the provided input.

        Args:
            request: Pipeline execution request

        Returns:
            Pipeline execution results
        """
        try:
            # Add tracing metadata
            if HAS_LANGSMITH:
                try:
                    from langsmith import get_current_run_tree
                    run_tree = get_current_run_tree()
                    if run_tree:
                        run_tree.add_metadata({
                            "execution_mode": "asynchronous",
                            "server_version": "1.0.0",
                            "input_path": request.input_path,
                            "output_path": request.output_path,
                            "has_custom_config": request.config is not None
                        })
                except Exception as e:
                    logger.debug(f"Failed to add tracing metadata: {e}")

            # Use custom config if provided, otherwise use default
            config = request.config if request.config else DEFAULT_CONFIG.copy()

            # Update output path if provided
            if request.output_path:
                config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path

            # Create pipeline workflow
            workflow = PipelineWorkflow(config=config)

            # Run pipeline asynchronously
            results = await workflow.arun_pipeline(request.input_path)

            # Convert to response model
            metrics = results.get("metrics")
            if metrics and hasattr(metrics, 'dict'):
                metrics = metrics.dict()
            elif metrics and not isinstance(metrics, dict):
                metrics = dict(metrics) if hasattr(metrics, '__dict__') else {}

            response = PipelineResponse(
                pipeline_id=results["pipeline_id"],
                status=results["status"],
                input_path=results["input_path"],
                output_path=results.get("output_path"),
                metrics=metrics,
                errors=results.get("errors", []),
                execution_summary=results.get("execution_summary"),
                timestamp=datetime.utcnow().isoformat()
            )

            return response

        except Exception as e:
            logger.error(f"Async pipeline execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/pipeline/stream")
    @traceable(name="pipeline_stream")
    async def stream_pipeline(request: PipelineRequest):
        """
        Stream pipeline execution with real-time progress updates.

        Args:
            request: Pipeline execution request

        Returns:
            Streaming response with pipeline updates
        """
        try:
            # Use custom config if provided, otherwise use default
            config = request.config if request.config else DEFAULT_CONFIG.copy()

            # Update output path if provided
            if request.output_path:
                config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path

            # Create pipeline workflow
            workflow = PipelineWorkflow(config=config)

            async def generate_stream():
                """Generate streaming updates."""
                try:
                    for update in workflow.stream_pipeline(request.input_path):
                        # Convert update to JSON and yield
                        yield f"data: {json.dumps(update)}\n\n"
                except Exception as e:
                    error_update = {
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(error_update)}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream"
                }
            )

        except Exception as e:
            logger.error(f"Streaming pipeline execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/pipeline/upload-and-run", response_model=PipelineResponse)
    @traceable(name="pipeline_upload_and_run")
    async def upload_and_run_pipeline(
        file: UploadFile = File(...),
        config: Optional[str] = None
    ):
        """
        Upload a file and run the pipeline on it.

        Args:
            file: Uploaded file
            config: Optional JSON string with custom pipeline configuration

        Returns:
            Pipeline execution results
        """
        try:
            # Create temporary file
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, file.filename)

            # Save uploaded file
            with open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)

            # Parse config if provided
            pipeline_config = DEFAULT_CONFIG.copy()
            if config:
                try:
                    custom_config = json.loads(config)
                    pipeline_config.update(custom_config)
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON config: {e}")

            # Create pipeline workflow
            workflow = PipelineWorkflow(config=pipeline_config)

            # Run pipeline
            results = workflow.run_pipeline(temp_file_path)

            # Clean up temporary file
            try:
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            except OSError:
                logger.warning(f"Failed to clean up temporary file: {temp_file_path}")

            # Convert to response model
            metrics = results.get("metrics")
            if metrics and hasattr(metrics, 'dict'):
                metrics = metrics.dict()
            elif metrics and not isinstance(metrics, dict):
                metrics = dict(metrics) if hasattr(metrics, '__dict__') else {}

            response = PipelineResponse(
                pipeline_id=results["pipeline_id"],
                status=results["status"],
                input_path=file.filename,  # Use original filename instead of temp path
                output_path=results.get("output_path"),
                metrics=metrics,
                errors=results.get("errors", []),
                execution_summary=results.get("execution_summary"),
                timestamp=datetime.utcnow().isoformat()
            )

            return response

        except Exception as e:
            logger.error(f"Upload and run pipeline failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/pipeline/config")
    async def get_default_config():
        """
        Get the default pipeline configuration.

        Returns:
            Default pipeline configuration
        """
        return {"config": DEFAULT_CONFIG}

    @app.get("/pipeline/components")
    async def list_components():
        """
        List available pipeline components.

        Returns:
            Available components by type
        """
        try:
            # Create a temporary workflow to get component information
            workflow = PipelineWorkflow(config=DEFAULT_CONFIG)
            info = workflow.get_pipeline_info()

            return {
                "components": info["components"],
                "total_components": info["workflow_nodes"]
            }

        except Exception as e:
            logger.error(f"Failed to list components: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Legacy support - expose the compiled workflow for langgraph dev
try:
    executor = LangGraphExecutor(config=DEFAULT_CONFIG)
    graph = executor.compiled_workflow
except Exception as e:
    logger.warning(f"Failed to create legacy graph export: {e}")
    graph = None

def main():
    """
    Main function to start the server.

    This function can be called directly or used as an entry point.
    """
    if not HAS_FASTAPI:
        print("Error: FastAPI is not installed.")
        print("Please install it with: pip install fastapi uvicorn")
        return

    # Configuration from environment variables
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    reload = os.getenv("SERVER_RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting KAG-LangGraph Pipeline Server on {host}:{port}")
    logger.info(f"API documentation available at: http://{host}:{port}/docs")

    # Start the server
    uvicorn.run(
        "server:app",  # Module and app variable
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()