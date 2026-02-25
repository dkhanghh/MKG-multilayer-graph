"""Configuration endpoints."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from knowledge_graphs.models.schema import DomainSchema
from knowledge_graphs.pipeline.langgraph_executor import PipelineWorkflow
from server.api.exceptions import APIError, NotFoundError
from server.core.config import get_default_config

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


class SchemaValidateRequest(BaseModel):
    content: str
    format: Optional[str] = None  # "dsl" or "yaml"; auto-detected when None


def _resolve_schema_path() -> str:
    """Return the first existing schema file path (YAML preferred, then DSL)."""
    candidates = [
        "knowledge_graphs/schema/financebench_spg.yaml",
        "knowledge_graphs/schema/financebench_spg.schema",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


@router.get("/schema")
async def get_schema():
    """Get the raw schema file content."""
    schema_path = _resolve_schema_path()
    if not os.path.exists(schema_path):
        raise NotFoundError(detail="Schema file not found")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return {"content": f.read(), "path": schema_path}
    except Exception as exc:
        logger.exception("Failed to read schema")
        raise APIError(detail="Could not read schema file")


@router.get("/schema/parsed")
async def get_schema_parsed():
    """Get the schema parsed into structured JSON via DomainSchema."""
    schema_path = _resolve_schema_path()
    if not os.path.exists(schema_path):
        raise NotFoundError(detail="Schema file not found")
    try:
        domain_schema = DomainSchema.from_file(schema_path)
        return {
            "schema": domain_schema.model_dump(),
            "extraction_schema": domain_schema.to_extraction_schema(),
            "path": schema_path,
        }
    except Exception as exc:
        logger.exception("Failed to parse schema")
        raise APIError(detail=f"Could not parse schema file: {exc}")


@router.post("/schema/validate")
async def validate_schema(request: SchemaValidateRequest):
    """Parse and validate schema content without saving.

    Returns the parsed schema on success or an error message on failure.
    """
    fmt = request.format
    content = request.content

    try:
        if fmt == "yaml" or fmt == "yml":
            domain_schema = DomainSchema.from_yaml(content)
        elif fmt == "dsl" or fmt == "schema":
            domain_schema = DomainSchema.from_dsl(content)
        else:
            # Auto-detect: if it starts with typical YAML markers, treat as YAML
            stripped = content.strip()
            if stripped.startswith("namespace:") or stripped.startswith("---"):
                domain_schema = DomainSchema.from_yaml(content)
            else:
                domain_schema = DomainSchema.from_dsl(content)

        return {
            "valid": True,
            "schema": domain_schema.model_dump(),
            "entity_count": len(domain_schema.entities),
            "relation_types": domain_schema.relation_type_names,
        }
    except Exception as exc:
        logger.warning("Schema validation failed: %s", exc)
        return {"valid": False, "error": str(exc)}


@router.post("/schema")
async def update_schema(update: SchemaUpdate):
    """Update the custom schema definition."""
    schema_path = _resolve_schema_path()
    try:
        os.makedirs(os.path.dirname(schema_path), exist_ok=True)
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write(update.content)
        return {"status": "success", "message": "Schema updated successfully", "path": schema_path}
    except Exception as exc:
        logger.exception("Failed to update schema")
        raise APIError(detail="Could not update schema file")
