"""Configuration endpoints."""
from fastapi import APIRouter, HTTPException

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
