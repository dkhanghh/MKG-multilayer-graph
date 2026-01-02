"""Configuration endpoints."""
from fastapi import APIRouter, HTTPException
import os
from pydantic import BaseModel

from server.core.config import DEFAULT_CONFIG
from knowledge_graphs.pipeline.langgraph_executor import PipelineWorkflow

router = APIRouter()


@router.get("/config")
async def get_default_config():
    """
    Get the default pipeline configuration.

    Returns:
        Default pipeline configuration dictionary
    """
    return {"config": DEFAULT_CONFIG}


@router.get("/components")
async def list_components():
    """
    List available pipeline components.

    Returns:
        Dictionary with component information

    Raises:
        HTTPException: If component listing fails
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
        raise HTTPException(status_code=500, detail=str(e))


class SchemaUpdate(BaseModel):
    content: str


@router.get("/schema")
async def get_schema():
    """
    Get the custom schema definition.
    """
    path = "knowledge_graphs/schema/financebench_spg.schema"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Schema file not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema")
async def update_schema(update: SchemaUpdate):
    """
    Update the custom schema definition.
    """
    path = "knowledge_graphs/schema/financebench_spg.schema"
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(update.content)
        return {"status": "success", "message": "Schema updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
