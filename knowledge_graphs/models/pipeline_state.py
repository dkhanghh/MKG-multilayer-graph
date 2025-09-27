"""
Pipeline state models for LangGraph workflow management.

This module defines the state structure that flows through the
KAG-LangGraph pipeline, enabling stateful workflow execution.
"""

from typing import Dict, Any, List, Optional, Union
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from enum import Enum
import json
from datetime import datetime

from .chunk import Chunk
from .graph import SubGraph, Node, Edge


class PipelineStatus(str, Enum):
    """Status of pipeline execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComponentOutput(BaseModel):
    """Output from a pipeline component."""
    
    component_name: str = Field(..., description="Name of the component that produced this output")
    component_type: str = Field(..., description="Type of component (scanner, reader, etc.)")
    status: str = Field(..., description="Status of component execution")
    data: Any = Field(None, description="Output data from the component")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Component execution metadata")
    execution_time: Optional[float] = Field(None, description="Time taken to execute component (seconds)")
    timestamp: Optional[datetime] = Field(None, description="When the component was executed")
    
    class Config:
        arbitrary_types_allowed = True


class PipelineMetrics(BaseModel):
    """Metrics and statistics for pipeline execution."""
    
    # Input metrics
    total_files_processed: int = Field(0, description="Total number of files processed")
    total_chunks_created: int = Field(0, description="Total number of chunks created")
    
    # Knowledge extraction metrics
    total_nodes_extracted: int = Field(0, description="Total number of nodes extracted")
    total_edges_extracted: int = Field(0, description="Total number of edges extracted")
    total_subgraphs_created: int = Field(0, description="Total number of subgraphs created")
    
    # Performance metrics
    total_execution_time: Optional[float] = Field(None, description="Total pipeline execution time")
    component_times: Dict[str, float] = Field(default_factory=dict, description="Execution time per component")
    
    # Quality metrics
    average_chunk_length: Optional[float] = Field(None, description="Average chunk length in characters")
    average_node_confidence: Optional[float] = Field(None, description="Average confidence score for extracted nodes")
    average_edge_confidence: Optional[float] = Field(None, description="Average confidence score for extracted edges")
    
    def add_component_time(self, component_name: str, execution_time: float) -> None:
        """Add execution time for a component."""
        self.component_times[component_name] = execution_time
    
    def get_total_execution_time(self) -> float:
        """Calculate total execution time from component times."""
        return sum(self.component_times.values())


class PipelineState(TypedDict, total=False):
    """
    State structure for the KAG-LangGraph pipeline.
    
    This TypedDict defines the structure that flows through the LangGraph
    workflow. Each component reads from and writes to this shared state.
    
    Note: Using TypedDict for LangGraph compatibility, with total=False
    to allow gradual state building.
    """
    
    # Pipeline metadata
    pipeline_id: str
    status: PipelineStatus
    created_at: datetime
    updated_at: datetime
    
    # Input configuration
    input_path: str  # Original input file/directory path
    config: Dict[str, Any]  # Pipeline configuration
    
    # Component outputs
    file_paths: List[str]  # Output from Scanner
    chunks: List[Chunk]    # Output from Reader
    split_chunks: List[Chunk]  # Output from Splitter  
    subgraphs: List[SubGraph]  # Output from Extractor
    vectorized_subgraphs: List[SubGraph]  # Output from Vectorizer
    output_path: str  # Output from Writer
    
    # Execution tracking
    component_outputs: List[ComponentOutput]  # History of component outputs
    current_component: Optional[str]  # Currently executing component
    metrics: PipelineMetrics  # Pipeline metrics and statistics
    
    # Error handling
    errors: List[str]  # List of error messages
    warnings: List[str]  # List of warning messages
    
    # Additional metadata
    metadata: Dict[str, Any]  # Additional pipeline metadata


class PipelineStateManager:
    """
    Helper class for managing pipeline state operations.
    
    Provides utility methods for creating, updating, and validating
    pipeline state throughout the workflow execution.
    """
    
    @staticmethod
    def create_initial_state(
        pipeline_id: str,
        input_path: str,
        config: Dict[str, Any]
    ) -> PipelineState:
        """
        Create initial pipeline state.
        
        Args:
            pipeline_id: Unique identifier for this pipeline run
            input_path: Path to input file or directory
            config: Pipeline configuration
            
        Returns:
            Initial pipeline state
        """
        now = datetime.utcnow()
        
        return PipelineState(
            pipeline_id=pipeline_id,
            status=PipelineStatus.PENDING,
            created_at=now,
            updated_at=now,
            input_path=input_path,
            config=config,
            file_paths=[],
            chunks=[],
            split_chunks=[],
            subgraphs=[],
            vectorized_subgraphs=[],
            output_path="",
            component_outputs=[],
            current_component=None,
            metrics=PipelineMetrics(),
            errors=[],
            warnings=[],
            metadata={},
        )
    
    @staticmethod
    def update_component_start(
        state: PipelineState,
        component_name: str,
        component_type: str
    ) -> PipelineState:
        """
        Update state when a component starts execution.
        
        Args:
            state: Current pipeline state
            component_name: Name of the component starting
            component_type: Type of component
            
        Returns:
            Updated pipeline state
        """
        state = state.copy()
        state["current_component"] = component_name
        state["status"] = PipelineStatus.RUNNING
        state["updated_at"] = datetime.utcnow()
        return state
    
    @staticmethod
    def update_component_complete(
        state: PipelineState,
        component_name: str,
        component_type: str,
        output_data: Any,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PipelineState:
        """
        Update state when a component completes execution.
        
        Args:
            state: Current pipeline state
            component_name: Name of the completed component
            component_type: Type of component
            output_data: Data produced by the component
            execution_time: Time taken for execution
            metadata: Additional metadata
            
        Returns:
            Updated pipeline state
        """
        state = state.copy()
        
        # Create component output record
        component_output = ComponentOutput(
            component_name=component_name,
            component_type=component_type,
            status="completed",
            data=output_data,
            metadata=metadata or {},
            execution_time=execution_time,
            timestamp=datetime.utcnow(),
        )
        
        # Add to component outputs history
        if "component_outputs" not in state:
            state["component_outputs"] = []
        state["component_outputs"].append(component_output)
        
        # Update metrics
        if "metrics" not in state:
            state["metrics"] = PipelineMetrics()
        state["metrics"].add_component_time(component_name, execution_time)
        
        # Update state based on component type
        if component_type == "scanner":
            state["file_paths"] = output_data
        elif component_type == "reader":
            state["chunks"] = output_data
            state["metrics"].total_chunks_created = len(output_data)
        elif component_type == "splitter":
            state["split_chunks"] = output_data
        elif component_type == "extractor":
            state["subgraphs"] = output_data
            # Update extraction metrics
            total_nodes = sum(len(sg.nodes) for sg in output_data)
            total_edges = sum(len(sg.edges) for sg in output_data)
            state["metrics"].total_nodes_extracted = total_nodes
            state["metrics"].total_edges_extracted = total_edges
            state["metrics"].total_subgraphs_created = len(output_data)
        elif component_type == "vectorizer":
            state["vectorized_subgraphs"] = output_data
        elif component_type == "writer":
            state["output_path"] = output_data
        
        # Update general state
        state["current_component"] = None
        state["updated_at"] = datetime.utcnow()
        
        return state
    
    @staticmethod
    def update_component_error(
        state: PipelineState,
        component_name: str,
        error_message: str,
        execution_time: Optional[float] = None
    ) -> PipelineState:
        """
        Update state when a component encounters an error.
        
        Args:
            state: Current pipeline state
            component_name: Name of the failed component
            error_message: Error message
            execution_time: Time taken before failure
            
        Returns:
            Updated pipeline state
        """
        state = state.copy()
        
        # Add error to error list
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"{component_name}: {error_message}")
        
        # Update status
        state["status"] = PipelineStatus.FAILED
        state["current_component"] = None
        state["updated_at"] = datetime.utcnow()
        
        return state
    
    @staticmethod
    def mark_pipeline_complete(state: PipelineState) -> PipelineState:
        """
        Mark the pipeline as completed.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state
        """
        state = state.copy()
        state["status"] = PipelineStatus.COMPLETED
        state["current_component"] = None
        state["updated_at"] = datetime.utcnow()
        
        # Calculate final metrics
        if "metrics" in state:
            state["metrics"].total_execution_time = state["metrics"].get_total_execution_time()
            
            # Calculate quality metrics
            if "chunks" in state and state["chunks"]:
                avg_chunk_length = sum(len(chunk.content) for chunk in state["chunks"]) / len(state["chunks"])
                state["metrics"].average_chunk_length = avg_chunk_length
        
        return state
    
    @staticmethod
    def get_state_summary(state: PipelineState) -> Dict[str, Any]:
        """
        Get a summary of the current pipeline state.
        
        Args:
            state: Pipeline state
            
        Returns:
            Summary dictionary
        """
        return {
            "pipeline_id": state.get("pipeline_id"),
            "status": state.get("status"),
            "current_component": state.get("current_component"),
            "files_processed": len(state.get("file_paths", [])),
            "chunks_created": len(state.get("chunks", [])),
            "subgraphs_created": len(state.get("subgraphs", [])),
            "total_nodes": sum(len(sg.nodes) for sg in state.get("subgraphs", [])),
            "total_edges": sum(len(sg.edges) for sg in state.get("subgraphs", [])),
            "errors": len(state.get("errors", [])),
            "warnings": len(state.get("warnings", [])),
            "execution_time": getattr(state.get("metrics"), "total_execution_time", None) if state.get("metrics") else None,
        }
    
    @staticmethod
    def serialize_state(state: PipelineState) -> str:
        """
        Serialize pipeline state to JSON string.
        
        Args:
            state: Pipeline state
            
        Returns:
            JSON string representation
        """
        # Convert to serializable format
        serializable_state = {}
        for key, value in state.items():
            if isinstance(value, datetime):
                serializable_state[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                # Handle complex objects
                if key in ["chunks", "split_chunks"]:
                    serializable_state[key] = [chunk.to_dict() for chunk in value]
                elif key in ["subgraphs", "vectorized_subgraphs"]:
                    serializable_state[key] = [sg.to_dict() for sg in value]
                elif key == "component_outputs":
                    serializable_state[key] = [output.dict() for output in value]
                else:
                    serializable_state[key] = value
            else:
                serializable_state[key] = value
        
        return json.dumps(serializable_state, indent=2)
    
    @staticmethod
    def deserialize_state(json_str: str) -> PipelineState:
        """
        Deserialize pipeline state from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            Pipeline state
        """
        data = json.loads(json_str)
        
        # Convert back to proper types
        state = PipelineState()
        for key, value in data.items():
            if key in ["created_at", "updated_at"] and isinstance(value, str):
                state[key] = datetime.fromisoformat(value)
            elif key in ["chunks", "split_chunks"] and isinstance(value, list):
                state[key] = [Chunk.from_dict(chunk_data) for chunk_data in value]
            elif key in ["subgraphs", "vectorized_subgraphs"] and isinstance(value, list):
                state[key] = [SubGraph.from_dict(sg_data) for sg_data in value]
            elif key == "component_outputs" and isinstance(value, list):
                state[key] = [ComponentOutput(**output_data) for output_data in value]
            elif key == "metrics" and isinstance(value, dict):
                state[key] = PipelineMetrics(**value)
            else:
                state[key] = value
        
        return state