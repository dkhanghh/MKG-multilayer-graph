"""
Splitter components for KAG-LangGraph pipeline.

This module contains splitter implementations that break down document chunks
into smaller, more manageable pieces for downstream processing.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Callable
import math

from .base import Splitter
from ..models.chunk import Chunk, ChunkType
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component

logger = logging.getLogger(__name__)

# Optional imports for advanced text processing
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@register_component(
    "splitter",
    "length_splitter",
    description="Splits chunks based on character or token count",
    config_schema={
        "type": "object",
        "properties": {
            "chunk_size": {
                "type": "integer",
                "description": "Maximum size of each chunk",
                "default": 1000
            },
            "chunk_overlap": {
                "type": "integer", 
                "description": "Number of characters to overlap between chunks",
                "default": 100
            },
            "split_by": {
                "type": "string",
                "enum": ["character", "word", "token"],
                "description": "What to use for measuring chunk size",
                "default": "character"
            },
            "separators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of separators to try when splitting (in order of preference)",
                "default": ["\n\n", "\n", ". ", " "]
            },
            "keep_separator": {
                "type": "boolean",
                "description": "Whether to keep separators in the chunks",
                "default": False
            }
        }
    }
)
class LengthSplitter(Splitter):
    """
    Splitter that breaks chunks based on length (characters, words, or tokens).
    
    Uses a hierarchical approach with preferred separators to maintain
    semantic coherence while respecting size constraints.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Split chunks based on length constraints.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with split chunks
        """
        chunks = state.get("chunks", [])
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")
        
        # Get configuration
        chunk_size = self.get_config_value("chunk_size", 1000)
        chunk_overlap = self.get_config_value("chunk_overlap", 100)
        split_by = self.get_config_value("split_by", "character")
        separators = self.get_config_value("separators", ["\n\n", "\n", ". ", " "])
        keep_separator = self.get_config_value("keep_separator", False)
        
        split_chunks = []
        
        for chunk in chunks:
            try:
                new_chunks = self._split_chunk(
                    chunk=chunk,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    split_by=split_by,
                    separators=separators,
                    keep_separator=keep_separator
                )
                split_chunks.extend(new_chunks)
            except Exception as e:
                logger.error(f"Error splitting chunk {chunk.id}: {e}")
                # Keep original chunk if splitting fails
                split_chunks.append(chunk)
        
        logger.info(f"Split {len(chunks)} chunks into {len(split_chunks)} chunks")
        
        # Update state
        updated_state = state.copy()
        updated_state["split_chunks"] = split_chunks
        
        return updated_state
    
    def _split_chunk(
        self,
        chunk: Chunk,
        chunk_size: int,
        chunk_overlap: int,
        split_by: str,
        separators: List[str],
        keep_separator: bool
    ) -> List[Chunk]:
        """
        Split a single chunk into smaller pieces.
        
        Args:
            chunk: Original chunk to split
            chunk_size: Maximum size per chunk
            chunk_overlap: Overlap between chunks
            split_by: How to measure size
            separators: Preferred separators
            keep_separator: Whether to keep separators
            
        Returns:
            List of split chunks
        """
        text = chunk.content
        
        # If chunk is already small enough, return as-is
        current_size = self._get_text_size(text, split_by)
        if current_size <= chunk_size:
            return [chunk]
        
        # Split the text
        splits = self._split_text(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            split_by=split_by,
            separators=separators,
            keep_separator=keep_separator
        )
        
        # Create new chunks
        split_chunks = []
        for i, split_text in enumerate(splits):
            if split_text.strip():
                split_chunk = Chunk(
                    id=f"{chunk.id}_split_{i}",
                    content=split_text.strip(),
                    chunk_type=chunk.chunk_type,
                    source_file=chunk.source_file,
                    page_number=chunk.page_number,
                    chunk_index=i,
                    heading_level=chunk.heading_level,
                    parent_section=chunk.parent_section,
                    processing_metadata={
                        **chunk.processing_metadata,
                        "original_chunk_id": chunk.id,
                        "split_index": i,
                        "split_method": "length_splitter"
                    }
                )
                split_chunks.append(split_chunk)
        
        return split_chunks
    
    def _split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        split_by: str,
        separators: List[str],
        keep_separator: bool
    ) -> List[str]:
        """
        Split text using hierarchical separators.
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            split_by: How to measure size
            separators: Separators to try
            keep_separator: Whether to keep separators
            
        Returns:
            List of text splits
        """
        # Try each separator in order
        for separator in separators:
            splits = self._split_text_by_separator(
                text, separator, chunk_size, chunk_overlap, split_by, keep_separator
            )
            
            # Check if all splits are within size limit
            valid_splits = True
            for split in splits:
                if self._get_text_size(split, split_by) > chunk_size:
                    valid_splits = False
                    break
            
            if valid_splits:
                return splits
        
        # If no separator worked, fall back to character splitting
        return self._split_text_by_character(text, chunk_size, chunk_overlap)
    
    def _split_text_by_separator(
        self,
        text: str,
        separator: str,
        chunk_size: int,
        chunk_overlap: int,
        split_by: str,
        keep_separator: bool
    ) -> List[str]:
        """
        Split text by a specific separator.
        
        Args:
            text: Text to split
            separator: Separator to split by
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            split_by: How to measure size
            keep_separator: Whether to keep separator
            
        Returns:
            List of text splits
        """
        # Split by separator
        parts = text.split(separator)
        if len(parts) == 1:
            # Separator not found in text
            return [text]
        
        # Rebuild splits with size constraints
        splits = []
        current_split = ""
        
        for i, part in enumerate(parts):
            # Add separator back if keeping it (except for first part)
            if keep_separator and i > 0:
                test_split = current_split + separator + part
            else:
                test_split = current_split + part if current_split else part
            
            test_size = self._get_text_size(test_split, split_by)
            
            if test_size <= chunk_size:
                current_split = test_split
            else:
                # Current split would be too big
                if current_split:
                    splits.append(current_split)
                    
                    # Handle overlap
                    if chunk_overlap > 0:
                        overlap_text = self._get_overlap_text(current_split, chunk_overlap, split_by)
                        if keep_separator and i > 0:
                            current_split = overlap_text + separator + part
                        else:
                            current_split = overlap_text + part
                    else:
                        current_split = part
                else:
                    # Even single part is too big - this separator won't work
                    return [text]
        
        # Add final split
        if current_split:
            splits.append(current_split)
        
        return splits
    
    def _split_text_by_character(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split text by character count (fallback method).
        
        Args:
            text: Text to split
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text splits
        """
        splits = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            split_text = text[start:end]
            splits.append(split_text)
            
            # Move start position considering overlap
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        return splits
    
    def _get_text_size(self, text: str, split_by: str) -> int:
        """
        Get size of text based on splitting method.
        
        Args:
            text: Text to measure
            split_by: Method to use for measurement
            
        Returns:
            Size of text
        """
        if split_by == "character":
            return len(text)
        elif split_by == "word":
            return len(text.split())
        elif split_by == "token":
            # Simple token approximation (could use proper tokenizer)
            return len(text.split())
        else:
            return len(text)
    
    def _get_overlap_text(self, text: str, overlap_size: int, split_by: str) -> str:
        """
        Get overlap text from the end of a chunk.
        
        Args:
            text: Text to get overlap from
            overlap_size: Size of overlap
            split_by: Method to use for measurement
            
        Returns:
            Overlap text
        """
        if split_by == "character":
            return text[-overlap_size:] if overlap_size < len(text) else text
        elif split_by == "word":
            words = text.split()
            overlap_words = words[-overlap_size:] if overlap_size < len(words) else words
            return " ".join(overlap_words)
        else:
            # Default to character-based
            return text[-overlap_size:] if overlap_size < len(text) else text


@register_component(
    "splitter",
    "sentence_splitter",
    description="Splits chunks by sentences using NLTK",
    config_schema={
        "type": "object",
        "properties": {
            "max_sentences": {
                "type": "integer",
                "description": "Maximum sentences per chunk",
                "default": 5
            },
            "sentence_overlap": {
                "type": "integer",
                "description": "Number of sentences to overlap between chunks",
                "default": 1
            },
            "min_chunk_length": {
                "type": "integer",
                "description": "Minimum characters per chunk", 
                "default": 100
            },
            "language": {
                "type": "string",
                "description": "Language for sentence tokenization",
                "default": "english"
            }
        }
    }
)
class SentenceSplitter(Splitter):
    """
    Splitter that breaks chunks by sentences using NLTK sentence tokenizer.
    
    Maintains sentence boundaries to preserve semantic coherence.
    """
    
    def __init__(self, config):
        """Initialize sentence splitter."""
        super().__init__(config)
        
        if not HAS_NLTK:
            logger.warning("NLTK not available, falling back to simple sentence splitting")
        else:
            # Download required NLTK data
            try:
                import nltk
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Split chunks by sentences.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with split chunks
        """
        chunks = state.get("chunks", [])
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")
        
        # Get configuration
        max_sentences = self.get_config_value("max_sentences", 5)
        sentence_overlap = self.get_config_value("sentence_overlap", 1)
        min_chunk_length = self.get_config_value("min_chunk_length", 100)
        language = self.get_config_value("language", "english")
        
        split_chunks = []
        
        for chunk in chunks:
            try:
                new_chunks = self._split_chunk_by_sentences(
                    chunk=chunk,
                    max_sentences=max_sentences,
                    sentence_overlap=sentence_overlap,
                    min_chunk_length=min_chunk_length,
                    language=language
                )
                split_chunks.extend(new_chunks)
            except Exception as e:
                logger.error(f"Error splitting chunk {chunk.id} by sentences: {e}")
                split_chunks.append(chunk)
        
        logger.info(f"Split {len(chunks)} chunks into {len(split_chunks)} chunks by sentences")
        
        # Update state
        updated_state = state.copy()
        updated_state["split_chunks"] = split_chunks
        
        return updated_state
    
    def _split_chunk_by_sentences(
        self,
        chunk: Chunk,
        max_sentences: int,
        sentence_overlap: int,
        min_chunk_length: int,
        language: str
    ) -> List[Chunk]:
        """
        Split chunk by sentences.
        
        Args:
            chunk: Chunk to split
            max_sentences: Maximum sentences per chunk
            sentence_overlap: Sentence overlap
            min_chunk_length: Minimum chunk length
            language: Language for tokenization
            
        Returns:
            List of split chunks
        """
        text = chunk.content
        
        # Tokenize into sentences
        sentences = self._tokenize_sentences(text, language)
        
        # If not enough sentences, return original chunk
        if len(sentences) <= max_sentences:
            return [chunk]
        
        # Create chunks from sentence groups
        split_chunks = []
        start_idx = 0
        chunk_idx = 0
        
        while start_idx < len(sentences):
            end_idx = min(start_idx + max_sentences, len(sentences))
            
            # Get sentences for this chunk
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = " ".join(chunk_sentences).strip()
            
            # Check minimum length
            if len(chunk_text) >= min_chunk_length or chunk_idx == 0:
                split_chunk = Chunk(
                    id=f"{chunk.id}_sent_{chunk_idx}",
                    content=chunk_text,
                    chunk_type=chunk.chunk_type,
                    source_file=chunk.source_file,
                    page_number=chunk.page_number,
                    chunk_index=chunk_idx,
                    heading_level=chunk.heading_level,
                    parent_section=chunk.parent_section,
                    processing_metadata={
                        **chunk.processing_metadata,
                        "original_chunk_id": chunk.id,
                        "split_index": chunk_idx,
                        "split_method": "sentence_splitter",
                        "sentence_count": len(chunk_sentences)
                    }
                )
                split_chunks.append(split_chunk)
                chunk_idx += 1
            
            # Move to next position with overlap
            start_idx = end_idx - sentence_overlap
            if start_idx >= len(sentences) or start_idx < 0:
                break
        
        return split_chunks
    
    def _tokenize_sentences(self, text: str, language: str) -> List[str]:
        """
        Tokenize text into sentences.
        
        Args:
            text: Text to tokenize
            language: Language for tokenization
            
        Returns:
            List of sentences
        """
        if HAS_NLTK:
            try:
                return sent_tokenize(text, language=language)
            except Exception as e:
                logger.warning(f"NLTK sentence tokenization failed: {e}")
        
        # Fallback to simple splitting
        return self._simple_sentence_split(text)
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """
        Simple sentence splitting fallback.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Split on sentence endings
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences


@register_component(
    "splitter",
    "semantic_splitter",
    description="Splits chunks based on semantic similarity using embeddings",
    config_schema={
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the sentence transformer model",
                "default": "all-MiniLM-L6-v2"
            },
            "similarity_threshold": {
                "type": "number",
                "description": "Similarity threshold for splitting (0.0-1.0)",
                "default": 0.8
            },
            "min_chunk_length": {
                "type": "integer", 
                "description": "Minimum characters per chunk",
                "default": 200
            },
            "max_chunk_length": {
                "type": "integer",
                "description": "Maximum characters per chunk",
                "default": 2000
            }
        }
    }
)
class SemanticSplitter(Splitter):
    """
    Splitter that uses semantic similarity to determine split points.
    
    Uses sentence embeddings to find natural breakpoints where
    semantic content changes significantly.
    """
    
    def __init__(self, config):
        """Initialize semantic splitter."""
        super().__init__(config)
        
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        # Load embedding model
        model_name = self.get_config_value("model_name", "all-MiniLM-L6-v2")
        try:
            self.embedding_model = SentenceTransformer(model_name)
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Split chunks based on semantic similarity.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with split chunks
        """
        chunks = state.get("chunks", [])
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")
        
        # Get configuration
        similarity_threshold = self.get_config_value("similarity_threshold", 0.8)
        min_chunk_length = self.get_config_value("min_chunk_length", 200)
        max_chunk_length = self.get_config_value("max_chunk_length", 2000)
        
        split_chunks = []
        
        for chunk in chunks:
            try:
                new_chunks = self._split_chunk_semantically(
                    chunk=chunk,
                    similarity_threshold=similarity_threshold,
                    min_chunk_length=min_chunk_length,
                    max_chunk_length=max_chunk_length
                )
                split_chunks.extend(new_chunks)
            except Exception as e:
                logger.error(f"Error splitting chunk {chunk.id} semantically: {e}")
                split_chunks.append(chunk)
        
        logger.info(f"Split {len(chunks)} chunks into {len(split_chunks)} chunks semantically")
        
        # Update state
        updated_state = state.copy()
        updated_state["split_chunks"] = split_chunks
        
        return updated_state
    
    def _split_chunk_semantically(
        self,
        chunk: Chunk,
        similarity_threshold: float,
        min_chunk_length: int,
        max_chunk_length: int
    ) -> List[Chunk]:
        """
        Split chunk based on semantic similarity.
        
        Args:
            chunk: Chunk to split
            similarity_threshold: Similarity threshold
            min_chunk_length: Minimum chunk length
            max_chunk_length: Maximum chunk length
            
        Returns:
            List of split chunks
        """
        text = chunk.content
        
        # If chunk is within size limits, return as-is
        if len(text) <= max_chunk_length:
            return [chunk]
        
        # Split into sentences first
        if HAS_NLTK:
            try:
                sentences = sent_tokenize(text)
            except:
                sentences = self._simple_sentence_split(text)
        else:
            sentences = self._simple_sentence_split(text)
        
        if len(sentences) <= 2:
            return [chunk]
        
        # Compute sentence embeddings
        embeddings = self.embedding_model.encode(sentences)
        
        # Find split points based on similarity
        split_points = self._find_semantic_splits(
            sentences, embeddings, similarity_threshold
        )
        
        # Create chunks from splits
        split_chunks = self._create_chunks_from_splits(
            chunk, sentences, split_points, min_chunk_length, max_chunk_length
        )
        
        return split_chunks
    
    def _find_semantic_splits(
        self,
        sentences: List[str],
        embeddings: List,
        similarity_threshold: float
    ) -> List[int]:
        """
        Find split points based on semantic similarity.
        
        Args:
            sentences: List of sentences
            embeddings: Sentence embeddings
            similarity_threshold: Similarity threshold
            
        Returns:
            List of sentence indices where splits should occur
        """
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        
        split_points = [0]  # Always start at beginning
        
        # Calculate similarities between consecutive sentences
        for i in range(len(embeddings) - 1):
            similarity = cosine_similarity(
                [embeddings[i]], [embeddings[i + 1]]
            )[0][0]
            
            # If similarity drops below threshold, mark as split point
            if similarity < similarity_threshold:
                split_points.append(i + 1)
        
        split_points.append(len(sentences))  # Always end at end
        
        return split_points
    
    def _create_chunks_from_splits(
        self,
        original_chunk: Chunk,
        sentences: List[str],
        split_points: List[int],
        min_chunk_length: int,
        max_chunk_length: int
    ) -> List[Chunk]:
        """
        Create chunks from sentence splits.
        
        Args:
            original_chunk: Original chunk
            sentences: List of sentences
            split_points: Split point indices
            min_chunk_length: Minimum chunk length
            max_chunk_length: Maximum chunk length
            
        Returns:
            List of chunks
        """
        split_chunks = []
        
        for i in range(len(split_points) - 1):
            start_idx = split_points[i]
            end_idx = split_points[i + 1]
            
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = " ".join(chunk_sentences).strip()
            
            # Check length constraints
            if len(chunk_text) < min_chunk_length:
                # Merge with previous chunk if possible
                if split_chunks and len(split_chunks[-1].content) + len(chunk_text) <= max_chunk_length:
                    split_chunks[-1].content += " " + chunk_text
                    continue
                elif len(chunk_text.strip()) > 0:  # Create chunk anyway if it has content
                    pass
                else:
                    continue
            
            # Create new chunk
            split_chunk = Chunk(
                id=f"{original_chunk.id}_semantic_{i}",
                content=chunk_text,
                chunk_type=original_chunk.chunk_type,
                source_file=original_chunk.source_file,
                page_number=original_chunk.page_number,
                chunk_index=i,
                heading_level=original_chunk.heading_level,
                parent_section=original_chunk.parent_section,
                processing_metadata={
                    **original_chunk.processing_metadata,
                    "original_chunk_id": original_chunk.id,
                    "split_index": i,
                    "split_method": "semantic_splitter",
                    "sentence_count": len(chunk_sentences)
                }
            )
            split_chunks.append(split_chunk)
        
        return split_chunks if split_chunks else [original_chunk]
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """Simple sentence splitting fallback."""
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]