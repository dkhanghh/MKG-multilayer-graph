"""Request models for API endpoints."""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class PipelineRequest(BaseModel):
    """Request model for pipeline execution."""

    input_path: str = Field(
        ...,
        description="Path to input file or directory",
        example="./data/financebench"
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom pipeline configuration to override defaults"
    )
    output_path: Optional[str] = Field(
        None,
        description="Custom output path for results"
    )
    batch_size: Optional[int] = Field(
        10,
        description="Number of files to process per batch (for directory processing)",
        ge=1,
        le=100
    )

    class Config:
        schema_extra = {
            "example": {
                "input_path": "./data/financebench",
                "batch_size": 10,
                "output_path": "./output/results"
            }
        }
