"""Configuration endpoints."""
import logging
import os

from fastapi import APIRouter
from pydantic import BaseModel

from server.api.exceptions import APIError, NotFoundError
from server.core.config import get_default_config
from knowledge_graphs.pipeline.langgraph_executor import PipelineWorkflow

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/config")
async def get_config():
    """Get the default pipeline configuration."""
    return {"config": get_default_config()}


@router.get("/components")
async def list_components():
    """List available pipeline components."""
    try:
        workflow = PipelineWorkflow(config=get_default_config())
        info = workflow.get_pipeline_info()
        return {"components": info["components"], "total_components": info["workflow_nodes"]}
    except Exception as exc:
        logger.exception("Failed to list components")
        raise APIError(detail="Could not list pipeline components")


class SchemaUpdate(BaseModel):
    content: str


_SCHEMA_PATH = "knowledge_graphs/schema/financebench_spg.schema"


@router.get("/schema")
async def get_schema():
    """Get the custom schema definition."""
    if not os.path.exists(_SCHEMA_PATH):
        raise NotFoundError(detail="Schema file not found")
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except Exception as exc:
        logger.exception("Failed to read schema")
        raise APIError(detail="Could not read schema file")


@router.post("/schema")
async def update_schema(update: SchemaUpdate):
    """Update the custom schema definition."""
    try:
        os.makedirs(os.path.dirname(_SCHEMA_PATH), exist_ok=True)
        with open(_SCHEMA_PATH, "w", encoding="utf-8") as f:
            f.write(update.content)
        return {"status": "success", "message": "Schema updated successfully"}
    except Exception as exc:
        logger.exception("Failed to update schema")
        raise APIError(detail="Could not update schema file")
