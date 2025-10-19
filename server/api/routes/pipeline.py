"""Pipeline execution endpoints."""
import json
import os
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from server.api.models import PipelineRequest, PipelineResponse
from server.core.config import DEFAULT_CONFIG
from server.core.tracing import traceable
from server.utils.helpers import convert_metrics_to_dict, add_tracing_metadata

# Import pipeline components
from knowledge_graphs.pipeline.langgraph_executor import PipelineWorkflow
from knowledge_graphs.pipeline.batch_processor import process_directory_in_batches

router = APIRouter()


@router.post("/run", response_model=PipelineResponse)
@traceable(name="pipeline_run_sync")
async def run_pipeline(request: PipelineRequest):
    """
    Run the pipeline synchronously on the provided input.

    Args:
        request: Pipeline execution request

    Returns:
        Pipeline execution results

    Raises:
        HTTPException: If pipeline execution fails
    """
    try:
        # Add tracing metadata
        add_tracing_metadata("synchronous", request)

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
        response = PipelineResponse(
            pipeline_id=results["pipeline_id"],
            status=results["status"],
            input_path=results["input_path"],
            output_path=results.get("output_path"),
            metrics=convert_metrics_to_dict(results.get("metrics")),
            errors=results.get("errors", []),
            execution_summary=results.get("execution_summary"),
            timestamp=datetime.utcnow().isoformat()
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-batch", response_model=PipelineResponse)
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

    Raises:
        HTTPException: If batch processing fails
    """
    try:
        # Add tracing metadata
        add_tracing_metadata("batch", request)

        # Use custom config if provided, otherwise use default
        config = request.config if request.config else DEFAULT_CONFIG.copy()

        # Update output path if provided
        if request.output_path:
            config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path

        # Use batch processor
        results = process_directory_in_batches(
            request.input_path,
            config,
            batch_size=request.batch_size
        )

        # Convert to response model
        response = PipelineResponse(
            pipeline_id=results["pipeline_id"],
            status=results["status"],
            input_path=results["input_path"],
            output_path=results.get("output_path"),
            metrics=convert_metrics_to_dict(results.get("metrics")),
            errors=results.get("errors", []),
            execution_summary=results.get("execution_summary"),
            timestamp=datetime.utcnow().isoformat()
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-async", response_model=PipelineResponse)
@traceable(name="pipeline_run_async")
async def run_pipeline_async(request: PipelineRequest):
    """
    Run the pipeline asynchronously on the provided input.

    Args:
        request: Pipeline execution request

    Returns:
        Pipeline execution results

    Raises:
        HTTPException: If async pipeline execution fails
    """
    try:
        # Add tracing metadata
        add_tracing_metadata("asynchronous", request)

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
        response = PipelineResponse(
            pipeline_id=results["pipeline_id"],
            status=results["status"],
            input_path=results["input_path"],
            output_path=results.get("output_path"),
            metrics=convert_metrics_to_dict(results.get("metrics")),
            errors=results.get("errors", []),
            execution_summary=results.get("execution_summary"),
            timestamp=datetime.utcnow().isoformat()
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
@traceable(name="pipeline_stream")
async def stream_pipeline(request: PipelineRequest):
    """
    Stream pipeline execution with real-time progress updates.

    Args:
        request: Pipeline execution request

    Returns:
        Streaming response with pipeline updates

    Raises:
        HTTPException: If streaming fails to start
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
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-run", response_model=PipelineResponse)
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

    Raises:
        HTTPException: If upload or execution fails
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
            pass  # Ignore cleanup errors

        # Convert to response model
        response = PipelineResponse(
            pipeline_id=results["pipeline_id"],
            status=results["status"],
            input_path=file.filename,  # Use original filename
            output_path=results.get("output_path"),
            metrics=convert_metrics_to_dict(results.get("metrics")),
            errors=results.get("errors", []),
            execution_summary=results.get("execution_summary"),
            timestamp=datetime.utcnow().isoformat()
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
