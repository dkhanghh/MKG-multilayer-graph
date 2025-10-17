"""
Reader components for KAG-LangGraph pipeline.

This module contains reader implementations that extract text content
from various document formats including PDF, DOCX, TXT, and others.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import mimetypes

from .base import Reader
from ..models.chunk import Chunk, ChunkType
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component

logger = logging.getLogger(__name__)

# Optional imports for document processing
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


@register_component(
    "reader",
    "txt_reader",
    description="Reads plain text files and converts them to chunks",
    config_schema={
        "type": "object",
        "properties": {
            "encoding": {
                "type": "string",
                "description": "Text file encoding",
                "default": "utf-8"
            },
            "chunk_by_lines": {
                "type": "boolean",
                "description": "Whether to create one chunk per file or split by lines",
                "default": False
            },
            "lines_per_chunk": {
                "type": "integer",
                "description": "Number of lines per chunk when chunk_by_lines is True",
                "default": 100
            }
        }
    }
)
class TXTReader(Reader):
    """
    Reader for plain text files.
    
    Extracts text content from .txt files and creates chunks.
    Can optionally split files into multiple chunks based on line count.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Process text files and create chunks.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with chunks
        """
        file_paths = state.get("file_paths", [])
        if not file_paths:
            raise ValueError("No file paths provided in pipeline state")
        
        chunks = []
        
        for file_path in file_paths:
            try:
                file_chunks = self._read_text_file(file_path)
                chunks.extend(file_chunks)
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {e}")
                continue
        
        logger.info(f"Created {len(chunks)} chunks from {len(file_paths)} text files")
        
        # Update state
        updated_state = state.copy()
        updated_state["chunks"] = chunks
        
        return updated_state
    
    def _read_text_file(self, file_path: str) -> List[Chunk]:
        """
        Read a text file and create chunks.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            List of chunks
        """
        encoding = self.get_config_value("encoding", "utf-8")
        chunk_by_lines = self.get_config_value("chunk_by_lines", False)
        lines_per_chunk = self.get_config_value("lines_per_chunk", 100)
        
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        chunks = []
        
        if chunk_by_lines and content.strip():
            # Split content by lines and group into chunks
            lines = content.split('\n')
            
            for i in range(0, len(lines), lines_per_chunk):
                chunk_lines = lines[i:i + lines_per_chunk]
                chunk_content = '\n'.join(chunk_lines).strip()
                
                if chunk_content:
                    chunk = Chunk(
                        id=f"{Path(file_path).stem}_chunk_{i // lines_per_chunk}",
                        content=chunk_content,
                        chunk_type=ChunkType.TEXT,
                        chunk_index=i // lines_per_chunk,
                    )
                    chunks.append(chunk)
        else:
            # Create single chunk for entire file
            if content.strip():
                chunk = Chunk(
                    id=f"{Path(file_path).stem}_full",
                    content=content.strip(),
                    chunk_type=ChunkType.TEXT,
                    chunk_index=0,
                )
                chunks.append(chunk)
        
        return chunks


@register_component(
    "reader", 
    "pdf_reader",
    description="Reads PDF files and extracts text content",
    config_schema={
        "type": "object",
        "properties": {
            "extract_images": {
                "type": "boolean",
                "description": "Whether to extract image descriptions",
                "default": False
            },
            "preserve_layout": {
                "type": "boolean", 
                "description": "Whether to preserve text layout",
                "default": False
            },
            "page_separator": {
                "type": "string",
                "description": "Separator between pages",
                "default": "\\n\\n--- PAGE BREAK ---\\n\\n"
            }
        }
    }
)
class PDFReader(Reader):
    """
    Reader for PDF files.
    
    Extracts text content from PDF files using pypdf library.
    Can optionally preserve layout and extract image information.
    """
    
    def __init__(self, config):
        """Initialize PDF reader."""
        super().__init__(config)
        
        if not HAS_PYPDF:
            raise ImportError(
                "pypdf not installed. Install with: pip install pypdf"
            )
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Process PDF files and create chunks.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with chunks
        """
        file_paths = state.get("file_paths", [])
        if not file_paths:
            raise ValueError("No file paths provided in pipeline state")
        
        chunks = []
        
        for file_path in file_paths:
            try:
                if file_path.lower().endswith('.pdf'):
                    file_chunks = self._read_pdf_file(file_path)
                    chunks.extend(file_chunks)
            except Exception as e:
                logger.error(f"Error reading PDF file {file_path}: {e}")
                continue
        
        logger.info(f"Created {len(chunks)} chunks from PDF files")
        
        # Update state
        updated_state = state.copy()
        updated_state["chunks"] = chunks
        
        return updated_state
    
    def _read_pdf_file(self, file_path: str) -> List[Chunk]:
        """
        Read a PDF file and create chunks.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of chunks
        """
        page_separator = self.get_config_value("page_separator", "\n\n--- PAGE BREAK ---\n\n")
        preserve_layout = self.get_config_value("preserve_layout", False)
        
        chunks = []
        
        with open(file_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            
            full_text = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    if preserve_layout:
                        # Use layout-preserving extraction if available
                        page_text = page.extract_text()
                    else:
                        # Standard text extraction
                        page_text = page.extract_text()
                    
                    if page_text.strip():
                        # Create chunk for each page
                        chunk = Chunk(
                            id=f"{Path(file_path).stem}_page_{page_num + 1}",
                            content=page_text.strip(),
                            chunk_type=ChunkType.TEXT,
                            page_number=page_num + 1,
                            chunk_index=page_num,
                        )
                        chunks.append(chunk)
                        
                        # Also accumulate full text
                        full_text += page_text + page_separator
                        
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1} of {file_path}: {e}")
                    continue
        
        # If no page-level chunks were created but we have full text, create one chunk
        if not chunks and full_text.strip():
            chunk = Chunk(
                id=f"{Path(file_path).stem}_full",
                content=full_text.strip(),
                chunk_type=ChunkType.TEXT,
                chunk_index=0,
            )
            chunks.append(chunk)
        
        return chunks


@register_component(
    "reader",
    "docx_reader", 
    description="Reads Microsoft Word DOCX files",
    config_schema={
        "type": "object",
        "properties": {
            "include_headers": {
                "type": "boolean",
                "description": "Whether to include header text",
                "default": True
            },
            "include_footers": {
                "type": "boolean",
                "description": "Whether to include footer text", 
                "default": False
            },
            "paragraph_separator": {
                "type": "string",
                "description": "Separator between paragraphs",
                "default": "\\n\\n"
            }
        }
    }
)
class DOCXReader(Reader):
    """
    Reader for Microsoft Word DOCX files.
    
    Extracts text content from DOCX files including paragraphs,
    headers, footers, and table content.
    """
    
    def __init__(self, config):
        """Initialize DOCX reader."""
        super().__init__(config)
        
        if not HAS_DOCX:
            raise ImportError(
                "python-docx not installed. Install with: pip install python-docx"
            )
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Process DOCX files and create chunks.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with chunks
        """
        file_paths = state.get("file_paths", [])
        if not file_paths:
            raise ValueError("No file paths provided in pipeline state")
        
        chunks = []
        
        for file_path in file_paths:
            try:
                if file_path.lower().endswith(('.docx', '.doc')):
                    file_chunks = self._read_docx_file(file_path)
                    chunks.extend(file_chunks)
            except Exception as e:
                logger.error(f"Error reading DOCX file {file_path}: {e}")
                continue
        
        logger.info(f"Created {len(chunks)} chunks from DOCX files")
        
        # Update state
        updated_state = state.copy()
        updated_state["chunks"] = chunks
        
        return updated_state
    
    def _read_docx_file(self, file_path: str) -> List[Chunk]:
        """
        Read a DOCX file and create chunks.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            List of chunks
        """
        include_headers = self.get_config_value("include_headers", True)
        include_footers = self.get_config_value("include_footers", False)
        paragraph_separator = self.get_config_value("paragraph_separator", "\n\n")
        
        doc = Document(file_path)
        
        # Extract paragraphs
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        # Extract table content
        for table in doc.tables:
            table_text = self._extract_table_text(table)
            if table_text:
                paragraphs.append(table_text)
        
        # Extract headers if requested
        if include_headers:
            for section in doc.sections:
                header = section.header
                for para in header.paragraphs:
                    text = para.text.strip()
                    if text:
                        paragraphs.insert(0, text)  # Add to beginning
        
        # Extract footers if requested
        if include_footers:
            for section in doc.sections:
                footer = section.footer
                for para in footer.paragraphs:
                    text = para.text.strip()
                    if text:
                        paragraphs.append(text)  # Add to end
        
        # Create chunks
        chunks = []
        
        if paragraphs:
            # Join all paragraphs into one chunk
            content = paragraph_separator.join(paragraphs)
            
            chunk = Chunk(
                id=f"{Path(file_path).stem}_full",
                content=content,
                chunk_type=ChunkType.TEXT,
                chunk_index=0,
                processing_metadata={"paragraph_count": len(paragraphs)}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_table_text(self, table) -> str:
        """
        Extract text from a Word table.
        
        Args:
            table: Table object from python-docx
            
        Returns:
            Formatted table text
        """
        table_text = []
        
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                row_text.append(cell_text)
            
            if any(row_text):  # Only add non-empty rows
                table_text.append(" | ".join(row_text))
        
        return "\n".join(table_text) if table_text else ""


@register_component(
    "reader",
    "mixed_reader",
    description="Auto-detects file types and uses appropriate readers",
    config_schema={
        "type": "object",
        "properties": {
            "supported_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of supported file types",
                "default": ["pdf", "txt", "docx", "md"]
            },
            "default_encoding": {
                "type": "string", 
                "description": "Default encoding for text files",
                "default": "utf-8"
            }
        }
    }
)
class MixedReader(Reader):
    """
    Reader that automatically detects file types and uses appropriate readers.
    
    Supports PDF, DOCX, TXT, MD, and other text-based formats.
    Uses MIME type detection and file extension analysis.
    """
    
    def __init__(self, config):
        """Initialize mixed reader."""
        super().__init__(config)
        
        # Initialize sub-readers
        self.txt_reader = None
        self.pdf_reader = None  
        self.docx_reader = None
        
        # Initialize readers as needed
        supported_types = self.get_config_value("supported_types", ["pdf", "txt", "docx", "md"])
        
        if "txt" in supported_types or "md" in supported_types:
            txt_config = self.config.model_copy()
            self.txt_reader = TXTReader(txt_config)
        
        if "pdf" in supported_types and HAS_PYPDF:
            pdf_config = self.config.model_copy()
            self.pdf_reader = PDFReader(pdf_config)
        
        if "docx" in supported_types and HAS_DOCX:
            docx_config = self.config.model_copy()
            self.docx_reader = DOCXReader(docx_config)
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Process files using appropriate readers based on file type.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with chunks
        """
        file_paths = state.get("file_paths", [])
        if not file_paths:
            raise ValueError("No file paths provided in pipeline state")
        
        # Group files by type
        file_groups = self._group_files_by_type(file_paths)
        
        all_chunks = []
        
        # Process each file type group
        for file_type, files in file_groups.items():
            if not files:
                continue
            
            try:
                # Create temporary state for this file group
                temp_state = state.copy()
                temp_state["file_paths"] = files
                
                # Use appropriate reader
                if file_type == "pdf" and self.pdf_reader:
                    result_state = self.pdf_reader.process(temp_state)
                elif file_type == "docx" and self.docx_reader:
                    result_state = self.docx_reader.process(temp_state)
                elif file_type in ["txt", "md"] and self.txt_reader:
                    result_state = self.txt_reader.process(temp_state)
                else:
                    # Fallback to text reading
                    result_state = self._read_as_text(temp_state)
                
                chunks = result_state.get("chunks", [])
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Error processing {file_type} files: {e}")
                continue
        
        logger.info(f"Created {len(all_chunks)} chunks from mixed file types")
        
        # Update state
        updated_state = state.copy()
        updated_state["chunks"] = all_chunks
        
        return updated_state
    
    def _group_files_by_type(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Group files by their detected type.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary mapping file types to file path lists
        """
        groups = {
            "pdf": [],
            "docx": [],
            "txt": [],
            "md": []
        }
        
        for file_path in file_paths:
            file_type = self._detect_file_type(file_path)
            if file_type in groups:
                groups[file_type].append(file_path)
            else:
                # Default to text
                groups["txt"].append(file_path)
        
        return groups
    
    def _detect_file_type(self, file_path: str) -> str:
        """
        Detect file type based on extension and MIME type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected file type
        """
        file_path_lower = file_path.lower()
        
        # Check by extension first
        if file_path_lower.endswith('.pdf'):
            return "pdf"
        elif file_path_lower.endswith(('.docx', '.doc')):
            return "docx"
        elif file_path_lower.endswith(('.md', '.markdown')):
            return "md"
        elif file_path_lower.endswith(('.txt', '.text')):
            return "txt"
        
        # Try MIME type detection
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type == 'application/pdf':
                return "pdf"
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return "docx"
            elif mime_type.startswith('text/'):
                return "txt"
        
        # Default to text
        return "txt"
    
    def _read_as_text(self, state: PipelineState) -> PipelineState:
        """
        Fallback method to read files as plain text.
        
        Args:
            state: Pipeline state with file paths
            
        Returns:
            Updated state with chunks
        """
        file_paths = state.get("file_paths", [])
        encoding = self.get_config_value("default_encoding", "utf-8")
        
        chunks = []
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                
                if content.strip():
                    chunk = Chunk(
                        id=f"{Path(file_path).stem}_text",
                        content=content.strip(),
                        chunk_type=ChunkType.TEXT,
                        chunk_index=0,
                    )
                    chunks.append(chunk)
                    
            except Exception as e:
                logger.warning(f"Could not read {file_path} as text: {e}")
                continue
        
        updated_state = state.copy()
        updated_state["chunks"] = chunks
        return updated_state