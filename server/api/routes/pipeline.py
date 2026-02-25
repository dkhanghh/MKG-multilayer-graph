"""Pipeline execution endpoints."""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse

from server.api.exceptions import APIError, ValidationError
from server.api.models import PipelineRequest, PipelineResponse
from server.core.config import load_config
from server.core.tracing import traceable
from server.utils.helpers import convert_metrics_to_dict, add_tracing_metadata

from knowledge_graphs.pipeline.langgraph_executor import PipelineWorkflow
from knowledge_graphs.pipeline.batch_processor import process_directory_in_batches
from knowledge_graphs.pipeline.csv_batch_processor import process_csv_in_batches

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_response(results: dict, input_path: str | None = None) -> PipelineResponse:
    """Build a PipelineResponse from raw pipeline results."""
    return PipelineResponse(
        pipeline_id=results["pipeline_id"],
        status=results["status"],
        input_path=input_path or results["input_path"],
        output_path=results.get("output_path"),
        metrics=convert_metrics_to_dict(results.get("metrics")),
        errors=results.get("errors", []),
        execution_summary=results.get("execution_summary"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _resolve_config(request: PipelineRequest) -> dict:
    """Return the pipeline config from the request or the default."""
    return request.config if request.config else load_config()


@router.post("/run", response_model=PipelineResponse)
@traceable(name="pipeline_run_sync")
async def run_pipeline(request: PipelineRequest):
    """Run the pipeline synchronously on the provided input."""
    try:
        add_tracing_metadata("synchronous", request)
        config = _resolve_config(request)
        if request.output_path:
            config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path
        workflow = PipelineWorkflow(config=config)
        results = workflow.run_pipeline(request.input_path)
        return _build_response(results)
    except FileNotFoundError as exc:
        raise ValidationError(detail=str(exc))
    except Exception as exc:
        logger.exception("Pipeline run failed")
        raise APIError(detail="Pipeline execution failed")


@router.post("/run-batch", response_model=PipelineResponse)
@traceable(name="pipeline_run_batch")
async def run_pipeline_batch(request: PipelineRequest):
    """Run the pipeline on a directory processing files in batches."""
    try:
        add_tracing_metadata("batch", request)
        config = _resolve_config(request)
        if request.output_path:
            config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path
        results = process_directory_in_batches(request.input_path, config, batch_size=request.batch_size)
        return _build_response(results)
    except FileNotFoundError as exc:
        raise ValidationError(detail=str(exc))
    except Exception as exc:
        logger.exception("Batch pipeline failed")
        raise APIError(detail="Batch pipeline execution failed")


@router.post("/run-csv-batch", response_model=PipelineResponse)
@traceable(name="pipeline_run_csv_batch")
async def run_csv_batch_pipeline(request: PipelineRequest):
    """Run the pipeline on a CSV file processing rows in batches."""
    try:
        add_tracing_metadata("csv_batch", request)
        config = _resolve_config(request)
        output_dir = request.output_path or "./output/csv_batches"
        results = process_csv_in_batches(request.input_path, config, batch_size=request.batch_size, output_dir=output_dir)
        return _build_response(results)
    except FileNotFoundError as exc:
        raise ValidationError(detail=str(exc))
    except Exception as exc:
        logger.exception("CSV batch pipeline failed")
        raise APIError(detail="CSV batch pipeline execution failed")


@router.post("/run-async", response_model=PipelineResponse)
@traceable(name="pipeline_run_async")
async def run_pipeline_async(request: PipelineRequest):
    """Run the pipeline asynchronously on the provided input."""
    try:
        add_tracing_metadata("asynchronous", request)
        config = _resolve_config(request)
        if request.output_path:
            config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path
        workflow = PipelineWorkflow(config=config)
        results = await workflow.arun_pipeline(request.input_path)
        return _build_response(results)
    except Exception as exc:
        logger.exception("Async pipeline failed")
        raise APIError(detail="Async pipeline execution failed")


@router.post("/stream")
@traceable(name="pipeline_stream")
async def stream_pipeline(request: PipelineRequest):
    """Stream pipeline execution with real-time progress updates."""
    try:
        config = _resolve_config(request)
        if request.output_path:
            config["pipeline"]["components"]["writer"]["config"]["output_path"] = request.output_path
        workflow = PipelineWorkflow(config=config)

        async def generate_stream():
            try:
                for update in workflow.stream_pipeline(request.input_path):
                    yield f"data: {json.dumps(update)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    except Exception as exc:
        logger.exception("Stream pipeline failed")
        raise APIError(detail="Stream pipeline execution failed")


@router.post("/upload-and-run", response_model=PipelineResponse)
@traceable(name="pipeline_upload_and_run")
async def upload_and_run_pipeline(file: UploadFile = File(...), config: Optional[str] = None):
    """Upload a file and run the pipeline on it."""
    try:
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)

        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)

        pipeline_config = load_config()
        if config:
            try:
                pipeline_config.update(json.loads(config))
            except json.JSONDecodeError as exc:
                raise ValidationError(detail=f"Invalid JSON config: {exc}")

        workflow = PipelineWorkflow(config=pipeline_config)
        results = workflow.run_pipeline(temp_file_path)

        try:
            os.remove(temp_file_path)
            os.rmdir(temp_dir)
        except OSError:
            pass

        return _build_response(results, input_path=file.filename)
    except (ValidationError, APIError):
        raise
    except Exception as exc:
        logger.exception("Upload-and-run failed")
        raise APIError(detail="Upload and run pipeline failed")
