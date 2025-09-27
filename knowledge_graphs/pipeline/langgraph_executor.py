"""
LangGraph workflow executor for KAG-LangGraph pipeline.

This module implements the workflow orchestration using LangGraph instead of NetworkX,
providing stateful execution with built-in error handling and progress tracking.
"""

import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from langgraph.graph import StateGraph, END

from ..models.pipeline_state import PipelineState, PipelineStateManager, PipelineStatus
from ..utils.registry import create_component
from ..components.base import BaseComponent

logger = logging.getLogger(__name__)


class LangGraphExecutor:
    """
    Main executor that orchestrates the KAG pipeline using LangGraph.
    
    Replaces the NetworkX-based DAG execution with LangGraph's stateful
    workflow system, providing better error handling, state management,
    and execution visibility.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LangGraph executor.
        
        Args:
            config: Pipeline configuration containing component definitions
        """
        self.config = config
        self.pipeline_config = config.get("pipeline", {})
        self.components_config = self.pipeline_config.get("components", {})
        
        # Initialize components
        self.components = self._initialize_components()
        
        # Create LangGraph workflow
        self.workflow = self._create_workflow()
        
        # Compile the workflow - let LangGraph handle persistence automatically
        self.compiled_workflow = self.workflow.compile(
            interrupt_before=[],  # Can add interruption points if needed
            interrupt_after=[]
        )
        
        logger.info("Initialized LangGraph executor with workflow")
    
    def run(self, input_path: str, **kwargs) -> PipelineState:
        """
        Run the complete pipeline on the given input.
        
        Args:
            input_path: Path to input file or directory
            **kwargs: Additional parameters
            
        Returns:
            Final pipeline state
        """
        # Create initial state
        pipeline_id = str(uuid.uuid4())
        initial_state = PipelineStateManager.create_initial_state(
            pipeline_id=pipeline_id,
            input_path=input_path,
            config=self.config
        )
        
        logger.info(f"Starting pipeline run {pipeline_id} for input: {input_path}")
        
        try:
            # Execute workflow
            final_state = self.compiled_workflow.invoke(
                initial_state,
                config={"configurable": {"thread_id": pipeline_id}}
            )
            
            # Mark as completed
            final_state = PipelineStateManager.mark_pipeline_complete(final_state)
            
            logger.info(f"Pipeline run {pipeline_id} completed successfully")
            return final_state
            
        except Exception as e:
            logger.error(f"Pipeline run {pipeline_id} failed: {e}")
            # Update state with error
            error_state = PipelineStateManager.update_component_error(
                initial_state, "pipeline", str(e)
            )
            return error_state
    
    async def arun(self, input_path: str, **kwargs) -> PipelineState:
        """
        Run the pipeline asynchronously.
        
        Args:
            input_path: Path to input file or directory
            **kwargs: Additional parameters
            
        Returns:
            Final pipeline state
        """
        # Create initial state
        pipeline_id = str(uuid.uuid4())
        initial_state = PipelineStateManager.create_initial_state(
            pipeline_id=pipeline_id,
            input_path=input_path,
            config=self.config
        )
        
        logger.info(f"Starting async pipeline run {pipeline_id} for input: {input_path}")
        
        try:
            # Execute workflow asynchronously
            final_state = await self.compiled_workflow.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": pipeline_id}}
            )
            
            # Mark as completed
            final_state = PipelineStateManager.mark_pipeline_complete(final_state)
            
            logger.info(f"Async pipeline run {pipeline_id} completed successfully")
            return final_state
            
        except Exception as e:
            logger.error(f"Async pipeline run {pipeline_id} failed: {e}")
            error_state = PipelineStateManager.update_component_error(
                initial_state, "pipeline", str(e)
            )
            return error_state
    
    def stream(self, input_path: str, **kwargs):
        """
        Stream pipeline execution for real-time progress monitoring.
        
        Args:
            input_path: Path to input file or directory
            **kwargs: Additional parameters
            
        Yields:
            Pipeline state updates as they occur
        """
        pipeline_id = str(uuid.uuid4())
        initial_state = PipelineStateManager.create_initial_state(
            pipeline_id=pipeline_id,
            input_path=input_path,
            config=self.config
        )
        
        logger.info(f"Starting streaming pipeline run {pipeline_id} for input: {input_path}")
        
        try:
            # Stream workflow execution
            for state_update in self.compiled_workflow.stream(
                initial_state,
                config={"configurable": {"thread_id": pipeline_id}}
            ):
                yield state_update
                
        except Exception as e:
            logger.error(f"Streaming pipeline run {pipeline_id} failed: {e}")
            error_state = PipelineStateManager.update_component_error(
                initial_state, "pipeline", str(e)
            )
            yield error_state
    
    def _initialize_components(self) -> Dict[str, BaseComponent]:
        """
        Initialize all components from configuration.
        
        Returns:
            Dictionary mapping component names to instances
        """
        components = {}
        
        for component_name, component_config in self.components_config.items():
            try:
                component_type = self._get_component_type(component_name)
                component_class_name = component_config.get("type")
                
                if not component_class_name:
                    raise ValueError(f"No type specified for component {component_name}")
                
                # Create component instance
                component = create_component(
                    component_type=component_type,
                    name=component_class_name,
                    config=component_config.get("config", {})
                )
                
                components[component_name] = component
                logger.info(f"Initialized {component_name} component: {component_class_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize component {component_name}: {e}")
                raise
        
        return components
    
    def _get_component_type(self, component_name: str) -> str:
        """
        Determine component type from component name.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component type (scanner, reader, etc.)
        """
        # Map component names to types
        type_mapping = {
            "scanner": "scanner",
            "reader": "reader", 
            "splitter": "splitter",
            "extractor": "extractor",
            "vectorizer": "vectorizer",
            "writer": "writer"
        }
        
        return type_mapping.get(component_name, component_name)
    
    def _create_workflow(self) -> StateGraph:
        """
        Create the LangGraph workflow definition.
        
        Returns:
            StateGraph workflow
        """
        # Create workflow graph
        workflow = StateGraph(PipelineState)
        
        # Add nodes for each component
        component_order = ["scanner", "reader", "splitter", "extractor", "vectorizer", "writer"]
        
        for component_name in component_order:
            if component_name in self.components:
                # Create wrapper function for the component
                node_function = self._create_component_node(component_name)
                workflow.add_node(component_name, node_function)
        
        # Add edges to define execution order
        active_components = [name for name in component_order if name in self.components]
        
        if active_components:
            # Set entry point
            workflow.set_entry_point(active_components[0])
            
            # Connect components in sequence
            for i in range(len(active_components) - 1):
                current_component = active_components[i]
                next_component = active_components[i + 1]
                workflow.add_edge(current_component, next_component)
            
            # Connect last component to END
            workflow.add_edge(active_components[-1], END)
        
        return workflow
    
    def _create_component_node(self, component_name: str) -> Callable[[PipelineState], PipelineState]:
        """
        Create a LangGraph node function for a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Node function that can be used in LangGraph
        """
        component = self.components[component_name]
        
        def component_node(state: PipelineState) -> PipelineState:
            """
            Execute a component and update pipeline state.
            
            Args:
                state: Current pipeline state
                
            Returns:
                Updated pipeline state
            """
            logger.info(f"Executing component: {component_name}")
            start_time = time.time()
            
            # Update state to indicate component is starting
            updated_state = PipelineStateManager.update_component_start(
                state, component_name, component.component_type
            )
            
            try:
                # Execute the component
                result_state = component.process(updated_state)
                execution_time = time.time() - start_time
                
                # Update state with successful completion
                final_state = PipelineStateManager.update_component_complete(
                    result_state,
                    component_name,
                    component.component_type,
                    output_data=self._extract_component_output(result_state, component.component_type),
                    execution_time=execution_time,
                    metadata={
                        "component_class": component.__class__.__name__,
                        "config": component.config.dict() if hasattr(component.config, 'dict') else str(component.config)
                    }
                )
                
                logger.info(f"Component {component_name} completed in {execution_time:.2f}s")
                return final_state
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Component {component_name} failed after {execution_time:.2f}s: {e}")
                
                # Update state with error
                error_state = PipelineStateManager.update_component_error(
                    updated_state, component_name, str(e), execution_time
                )
                return error_state
        
        return component_node
    
    def _extract_component_output(self, state: PipelineState, component_type: str) -> Any:
        """
        Extract the relevant output data based on component type.
        
        Args:
            state: Pipeline state
            component_type: Type of component
            
        Returns:
            Relevant output data for the component
        """
        if component_type == "scanner":
            return state.get("file_paths", [])
        elif component_type == "reader":
            return state.get("chunks", [])
        elif component_type == "splitter":
            return state.get("split_chunks", [])
        elif component_type == "extractor":
            return state.get("subgraphs", [])
        elif component_type == "vectorizer":
            return state.get("vectorized_subgraphs", [])
        elif component_type == "writer":
            return state.get("output_path", "")
        else:
            return None


class PipelineWorkflow:
    """
    High-level interface for creating and managing KAG pipelines.
    
    Provides a simplified interface for common pipeline configurations
    and operations.
    """
    
    def __init__(self, config_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize pipeline workflow.
        
        Args:
            config_path: Path to YAML configuration file
            config: Direct configuration dictionary
        """
        if config_path:
            self.config = self._load_config_from_file(config_path)
        elif config:
            self.config = config
        else:
            raise ValueError("Either config_path or config must be provided")
        
        self.executor = LangGraphExecutor(self.config)
    
    def run_pipeline(self, input_path: str, **kwargs) -> Dict[str, Any]:
        """
        Run the complete pipeline and return results.
        
        Args:
            input_path: Path to input file or directory
            **kwargs: Additional parameters
            
        Returns:
            Pipeline results dictionary
        """
        # Execute pipeline
        final_state = self.executor.run(input_path, **kwargs)
        
        # Extract results
        results = {
            "pipeline_id": final_state.get("pipeline_id"),
            "status": final_state.get("status"),
            "input_path": final_state.get("input_path"),
            "output_path": final_state.get("output_path"),
            "metrics": final_state.get("metrics"),
            "errors": final_state.get("errors", []),
            "execution_summary": PipelineStateManager.get_state_summary(final_state)
        }
        
        return results
    
    async def arun_pipeline(self, input_path: str, **kwargs) -> Dict[str, Any]:
        """
        Run pipeline asynchronously.
        
        Args:
            input_path: Path to input file or directory
            **kwargs: Additional parameters
            
        Returns:
            Pipeline results dictionary
        """
        final_state = await self.executor.arun(input_path, **kwargs)
        
        results = {
            "pipeline_id": final_state.get("pipeline_id"),
            "status": final_state.get("status"),
            "input_path": final_state.get("input_path"),
            "output_path": final_state.get("output_path"),
            "metrics": final_state.get("metrics"),
            "errors": final_state.get("errors", []),
            "execution_summary": PipelineStateManager.get_state_summary(final_state)
        }
        
        return results
    
    def stream_pipeline(self, input_path: str, **kwargs):
        """
        Stream pipeline execution with real-time updates.
        
        Args:
            input_path: Path to input file or directory
            **kwargs: Additional parameters
            
        Yields:
            Pipeline state updates
        """
        for state_update in self.executor.stream(input_path, **kwargs):
            # Extract relevant information for streaming
            update_info = {
                "current_component": state_update.get("current_component"),
                "status": state_update.get("status"),
                "progress": self._calculate_progress(state_update),
                "errors": state_update.get("errors", []),
                "timestamp": datetime.utcnow().isoformat()
            }
            yield update_info
    
    def _calculate_progress(self, state: PipelineState) -> float:
        """
        Calculate pipeline progress as a percentage.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Progress percentage (0.0 to 1.0)
        """
        # Simple progress calculation based on completed components
        total_components = len(self.config.get("pipeline", {}).get("components", {}))
        completed_components = len(state.get("component_outputs", []))
        
        if total_components == 0:
            return 0.0
        
        return min(completed_components / total_components, 1.0)
    
    def _load_config_from_file(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        import yaml
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        Get information about the configured pipeline.
        
        Returns:
            Pipeline information dictionary
        """
        components_info = {}
        
        for component_name, component in self.executor.components.items():
            components_info[component_name] = {
                "type": component.component_type,
                "class": component.__class__.__name__,
                "enabled": component.enabled,
                "config": component.config.dict() if hasattr(component.config, 'dict') else str(component.config)
            }
        
        return {
            "components": components_info,
            "workflow_nodes": len(self.executor.components),
            "config": self.config
        }


# Convenience function for quick pipeline execution
def run_pipeline(config: Dict[str, Any], input_path: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to run a pipeline with a configuration dictionary.
    
    Args:
        config: Pipeline configuration
        input_path: Path to input file or directory
        **kwargs: Additional parameters
        
    Returns:
        Pipeline results
    """
    workflow = PipelineWorkflow(config=config)
    return workflow.run_pipeline(input_path, **kwargs)