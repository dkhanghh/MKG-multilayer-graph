"""Response models for API endpoints."""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class PipelineResponse(BaseModel):
    """Response model for pipeline execution."""

    pipeline_id: str = Field(..., description="Unique pipeline execution ID")
    status: str = Field(..., description="Pipeline status (success, error, running)")
    input_path: str = Field(..., description="Input path that was processed")
    output_path: Optional[str] = Field(None, description="Output path where results were saved")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Pipeline execution metrics")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    execution_summary: Optional[Dict[str, Any]] = Field(None, description="Summary of execution")
    timestamp: str = Field(..., description="Timestamp of response")

    class Config:
        schema_extra = {
            "example": {
                "pipeline_id": "pipeline-123abc",
                "status": "success",
                "input_path": "./data/financebench",
                "output_path": "./output/results",
                "metrics": {
                    "files_processed": 10,
                    "entities_extracted": 150,
                    "duration_seconds": 45.2
                },
                "errors": [],
                "execution_summary": {
                    "total_files": 10,
                    "successful": 10,
                    "failed": 0
                },
                "timestamp": "2024-10-17T22:30:00Z"
            }
        }


class PipelineStatus(BaseModel):
    """Model for pipeline status information."""

    pipeline_id: str = Field(..., description="Unique pipeline execution ID")
    status: str = Field(..., description="Current status")
    current_component: Optional[str] = Field(None, description="Currently executing component")
    progress: float = Field(0.0, description="Progress percentage (0-100)", ge=0.0, le=100.0)
    errors: List[str] = Field(default_factory=list, description="List of errors")
    timestamp: str = Field(..., description="Timestamp of status")
