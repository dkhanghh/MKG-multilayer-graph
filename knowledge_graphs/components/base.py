"""
Base classes and interfaces for KAG-LangGraph pipeline components.

This module defines the abstract base classes and common functionality
that all pipeline components inherit from.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, Field

from ..models.pipeline_state import PipelineState, ComponentOutput

T = TypeVar('T', bound='BaseComponent')


class ComponentConfig(BaseModel):
    """Base configuration class for all components."""
    
    type: str = Field(..., description="Component type identifier")
    name: Optional[str] = Field(None, description="Custom component name")
    enabled: bool = Field(True, description="Whether component is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Component-specific configuration")
    
    class Config:
        extra = "allow"


class BaseComponent(ABC):
    """
    Abstract base class for all pipeline components.
    
    Each component processes the pipeline state and returns updated state.
    Components should be stateless and thread-safe.
    """
    
    def __init__(self, config: ComponentConfig):
        """
        Initialize component with configuration.
        
        Args:
            config: Component configuration
        """
        self.config = config
        self.name = config.name or self.__class__.__name__
        self.enabled = config.enabled
        
    @property
    @abstractmethod
    def component_type(self) -> str:
        """Return the component type identifier."""
        pass
    
    @property
    @abstractmethod
    def input_types(self) -> List[Type]:
        """Return list of expected input types."""
        pass
    
    @property
    @abstractmethod
    def output_types(self) -> List[Type]:
        """Return list of output types this component produces."""
        pass
    
    @abstractmethod
    def process(self, state: PipelineState) -> PipelineState:
        """
        Process the pipeline state and return updated state.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state
        """
        pass
    
    async def aprocess(self, state: PipelineState) -> PipelineState:
        """
        Async version of process. Default implementation calls sync version.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state
        """
        import asyncio
        return await asyncio.to_thread(self.process, state)
    
    def validate_inputs(self, state: PipelineState) -> bool:
        """
        Validate that the pipeline state contains required inputs.
        
        Args:
            state: Pipeline state to validate
            
        Returns:
            True if inputs are valid
        """
        # Basic validation - can be overridden by subclasses
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with fallback to default.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.config.get(key, default)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})"


class Scanner(BaseComponent):
    """Abstract base class for scanner components."""
    
    @property
    def component_type(self) -> str:
        return "scanner"
    
    @property
    def input_types(self) -> List[Type]:
        return [str]  # File paths or directory paths
    
    @property
    def output_types(self) -> List[Type]:
        return [List[str]]  # List of file paths


class Reader(BaseComponent):
    """Abstract base class for reader components."""
    
    @property
    def component_type(self) -> str:
        return "reader"
    
    @property
    def input_types(self) -> List[Type]:
        return [List[str]]  # List of file paths
    
    @property
    def output_types(self) -> List[Type]:
        from ..models.chunk import Chunk
        return [List[Chunk]]  # List of document chunks


class Splitter(BaseComponent):
    """Abstract base class for splitter components."""
    
    @property
    def component_type(self) -> str:
        return "splitter"
    
    @property
    def input_types(self) -> List[Type]:
        from ..models.chunk import Chunk
        return [List[Chunk]]  # List of document chunks
    
    @property
    def output_types(self) -> List[Type]:
        from ..models.chunk import Chunk
        return [List[Chunk]]  # List of smaller chunks


class Extractor(BaseComponent):
    """Abstract base class for extractor components."""
    
    @property
    def component_type(self) -> str:
        return "extractor"
    
    @property
    def input_types(self) -> List[Type]:
        from ..models.chunk import Chunk
        return [List[Chunk]]  # List of text chunks
    
    @property
    def output_types(self) -> List[Type]:
        from ..models.graph import SubGraph
        return [List[SubGraph]]  # List of knowledge subgraphs


class Vectorizer(BaseComponent):
    """Abstract base class for vectorizer components."""
    
    @property
    def component_type(self) -> str:
        return "vectorizer"
    
    @property
    def input_types(self) -> List[Type]:
        from ..models.graph import SubGraph
        return [List[SubGraph]]  # List of knowledge subgraphs
    
    @property
    def output_types(self) -> List[Type]:
        from ..models.graph import SubGraph
        return [List[SubGraph]]  # List of subgraphs with embeddings


class Writer(BaseComponent):
    """Abstract base class for writer components."""
    
    @property
    def component_type(self) -> str:
        return "writer"
    
    @property
    def input_types(self) -> List[Type]:
        from ..models.graph import SubGraph
        return [List[SubGraph]]  # List of knowledge subgraphs
    
    @property
    def output_types(self) -> List[Type]:
        return [str]  # Output file path or status message