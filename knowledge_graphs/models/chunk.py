"""
Document chunk models for the KAG-LangGraph pipeline.

This module defines the Chunk class and related types for representing
text segments extracted from documents.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
import hashlib
import json


class ChunkType(str, Enum):
    """Types of document chunks."""
    
    TEXT = "text"
    TABLE = "table" 
    IMAGE = "image"
    HEADER = "header"
    FOOTER = "footer"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    CODE = "code"


class Chunk(BaseModel):
    """
    Represents a chunk of text extracted from a document.
    
    Chunks are the basic unit of text processing in the pipeline.
    They contain the text content along with metadata about its
    source and structure.
    """
    
    id: str = Field(..., description="Unique identifier for the chunk")
    content: str = Field(..., description="Text content of the chunk")
    chunk_type: ChunkType = Field(ChunkType.TEXT, description="Type of chunk")

    # Source information
    page_number: Optional[int] = Field(None, description="Page number in source document")
    chunk_index: Optional[int] = Field(None, description="Index of chunk in document")
    
    # Content metadata
    length: Optional[int] = Field(None, description="Length of content in characters")
    word_count: Optional[int] = Field(None, description="Number of words in content")
    language: Optional[str] = Field(None, description="Detected language")
    
    # Structure metadata  
    heading_level: Optional[int] = Field(None, description="Heading level if applicable")
    parent_section: Optional[str] = Field(None, description="Parent section title")
    
    # Processing metadata
    embeddings: Optional[List[float]] = Field(None, description="Text embeddings")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional processing metadata")
    
    def __init__(self, **data):
        """Initialize chunk and compute derived fields."""
        super().__init__(**data)
        
        # Compute derived fields if not provided
        if self.length is None:
            self.length = len(self.content)
            
        if self.word_count is None:
            self.word_count = len(self.content.split())
    
    @property
    def hash_key(self) -> str:
        """
        Generate a hash key for this chunk based on its content and metadata.

        Returns:
            SHA-256 hash of chunk content and key metadata
        """
        # Create a string representation of the chunk's identifying features
        key_data = {
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
        }

        # Convert to JSON string for hashing
        key_string = json.dumps(key_data, sort_keys=True)

        # Generate SHA-256 hash
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert chunk to dictionary representation.

        Returns:
            Dictionary representation of the chunk
        """
        return {
            "id": self.id,
            "content": self.content,
            "chunk_type": self.chunk_type.value,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "length": self.length,
            "word_count": self.word_count,
            "language": self.language,
            "heading_level": self.heading_level,
            "parent_section": self.parent_section,
            "embeddings": self.embeddings,
            "processing_metadata": self.processing_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """
        Create chunk from dictionary representation.
        
        Args:
            data: Dictionary containing chunk data
            
        Returns:
            Chunk instance
        """
        # Convert chunk_type string back to enum if needed
        if "chunk_type" in data and isinstance(data["chunk_type"], str):
            data["chunk_type"] = ChunkType(data["chunk_type"])
            
        return cls(**data)
    
    def get_text_preview(self, max_length: int = 100) -> str:
        """
        Get a preview of the chunk content.
        
        Args:
            max_length: Maximum length of preview
            
        Returns:
            Truncated content with ellipsis if needed
        """
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length].rsplit(' ', 1)[0] + "..."
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the chunk.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.processing_metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.processing_metadata.get(key, default)
    
    def __str__(self) -> str:
        """String representation of the chunk."""
        preview = self.get_text_preview(50)
        return f"Chunk(id='{self.id}', type={self.chunk_type}, content='{preview}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the chunk."""
        return (f"Chunk(id='{self.id}', content_length={self.length}, "
                f"type={self.chunk_type})")
    
    model_config = ConfigDict(
        use_enum_values=True,
        arbitrary_types_allowed=True
    )