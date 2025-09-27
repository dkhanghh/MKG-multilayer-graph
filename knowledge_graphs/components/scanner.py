"""
Scanner components for KAG-LangGraph pipeline.

This module contains scanner implementations that discover and collect
file paths for processing by downstream components.
"""

import os
import glob
from pathlib import Path
from typing import List, Optional, Set, Union
import logging
import mimetypes

from .base import Scanner
from ..models.pipeline_state import PipelineState, PipelineStateManager
from ..utils.registry import register_component

logger = logging.getLogger(__name__)


@register_component(
    "scanner",
    "file_scanner", 
    description="Scans a single file and returns its path",
    config_schema={
        "type": "object",
        "properties": {
            "verify_exists": {
                "type": "boolean", 
                "description": "Whether to verify file exists",
                "default": True
            }
        }
    }
)
class FileScanner(Scanner):
    """
    Scanner that processes a single file.
    
    Takes a file path as input and returns it as a list containing
    that single path, optionally verifying the file exists.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Process a single file path.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with file_paths set
        """
        input_path = state.get("input_path", "")
        verify_exists = self.get_config_value("verify_exists", True)
        
        if not input_path:
            raise ValueError("No input_path provided in pipeline state")
        
        # Verify file exists if requested
        if verify_exists and not os.path.isfile(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")
        
        # Return the single file path as a list
        file_paths = [input_path]
        
        # Update state
        updated_state = state.copy()
        updated_state["file_paths"] = file_paths
        
        return updated_state


@register_component(
    "scanner", 
    "directory_scanner",
    description="Recursively scans a directory for files matching patterns",
    config_schema={
        "type": "object",
        "properties": {
            "recursive": {
                "type": "boolean",
                "description": "Whether to scan directories recursively", 
                "default": True
            },
            "file_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file patterns to match (e.g., ['*.pdf', '*.txt'])",
                "default": ["*"]
            },
            "exclude_patterns": {
                "type": "array", 
                "items": {"type": "string"},
                "description": "List of patterns to exclude",
                "default": []
            },
            "max_files": {
                "type": "integer",
                "description": "Maximum number of files to return",
                "default": None
            },
            "supported_extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of supported file extensions",
                "default": [".pdf", ".txt", ".docx", ".doc", ".md"]
            }
        }
    }
)
class DirectoryScanner(Scanner):
    """
    Scanner that recursively discovers files in a directory.
    
    Supports pattern matching, file filtering, and various options
    for controlling the discovery process.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Scan directory for files matching patterns.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with file_paths set
        """
        input_path = state.get("input_path", "")
        
        if not input_path:
            raise ValueError("No input_path provided in pipeline state")
        
        if not os.path.isdir(input_path):
            raise NotADirectoryError(f"Not a directory: {input_path}")
        
        # Get configuration
        recursive = self.get_config_value("recursive", True)
        file_patterns = self.get_config_value("file_patterns", ["*"])
        exclude_patterns = self.get_config_value("exclude_patterns", [])
        max_files = self.get_config_value("max_files")
        supported_extensions = self.get_config_value(
            "supported_extensions", 
            [".pdf", ".txt", ".docx", ".doc", ".md"]
        )
        
        # Discover files
        file_paths = self._discover_files(
            directory=input_path,
            patterns=file_patterns,
            exclude_patterns=exclude_patterns,
            recursive=recursive,
            supported_extensions=supported_extensions,
            max_files=max_files
        )
        
        logger.info(f"Discovered {len(file_paths)} files in {input_path}")
        
        # Update state
        updated_state = state.copy()
        updated_state["file_paths"] = file_paths
        
        return updated_state
    
    def _discover_files(
        self,
        directory: str,
        patterns: List[str],
        exclude_patterns: List[str],
        recursive: bool,
        supported_extensions: List[str],
        max_files: Optional[int]
    ) -> List[str]:
        """
        Discover files in directory matching criteria.
        
        Args:
            directory: Directory to scan
            patterns: File patterns to match
            exclude_patterns: Patterns to exclude
            recursive: Whether to scan recursively
            supported_extensions: List of supported extensions
            max_files: Maximum number of files to return
            
        Returns:
            List of discovered file paths
        """
        discovered_files: Set[str] = set()
        
        # Convert to Path for easier handling
        root_path = Path(directory)
        
        for pattern in patterns:
            if recursive:
                # Use ** for recursive globbing
                search_pattern = root_path / "**" / pattern
                matches = glob.glob(str(search_pattern), recursive=True)
            else:
                # Search only in the immediate directory
                search_pattern = root_path / pattern
                matches = glob.glob(str(search_pattern))
            
            # Filter matches
            for match in matches:
                if self._should_include_file(
                    match, exclude_patterns, supported_extensions
                ):
                    discovered_files.add(match)
                    
                    # Check max files limit
                    if max_files and len(discovered_files) >= max_files:
                        logger.warning(f"Reached max_files limit of {max_files}")
                        break
            
            # Break if we've hit the limit
            if max_files and len(discovered_files) >= max_files:
                break
        
        # Sort for consistent ordering
        return sorted(list(discovered_files))
    
    def _should_include_file(
        self,
        file_path: str,
        exclude_patterns: List[str],
        supported_extensions: List[str]
    ) -> bool:
        """
        Check if a file should be included based on filters.
        
        Args:
            file_path: Path to the file
            exclude_patterns: Patterns to exclude
            supported_extensions: Supported file extensions
            
        Returns:
            True if file should be included
        """
        # Must be a regular file
        if not os.path.isfile(file_path):
            return False
        
        file_path_obj = Path(file_path)
        
        # Check supported extensions
        if supported_extensions:
            extension = file_path_obj.suffix.lower()
            if extension not in [ext.lower() for ext in supported_extensions]:
                return False
        
        # Check exclude patterns
        for exclude_pattern in exclude_patterns:
            if file_path_obj.match(exclude_pattern):
                return False
        
        # Check if file is readable
        try:
            with open(file_path, 'rb') as f:
                f.read(1)
            return True
        except (PermissionError, OSError):
            logger.warning(f"Cannot read file: {file_path}")
            return False


@register_component(
    "scanner",
    "url_scanner",
    description="Scans URLs and downloads files for processing", 
    config_schema={
        "type": "object",
        "properties": {
            "download_dir": {
                "type": "string",
                "description": "Directory to download files to",
                "default": "./downloads"
            },
            "verify_ssl": {
                "type": "boolean",
                "description": "Whether to verify SSL certificates",
                "default": True
            },
            "timeout": {
                "type": "integer", 
                "description": "Request timeout in seconds",
                "default": 30
            }
        }
    }
)
class URLScanner(Scanner):
    """
    Scanner that downloads files from URLs.
    
    Takes a URL as input, downloads the file, and returns the
    local file path for processing.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Download file from URL.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with file_paths set
        """
        input_path = state.get("input_path", "")
        
        if not input_path:
            raise ValueError("No input_path provided in pipeline state")
        
        if not (input_path.startswith("http://") or input_path.startswith("https://")):
            raise ValueError(f"Invalid URL: {input_path}")
        
        # Get configuration
        download_dir = self.get_config_value("download_dir", "./downloads")
        verify_ssl = self.get_config_value("verify_ssl", True)
        timeout = self.get_config_value("timeout", 30)
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
        
        # Download file
        local_file_path = self._download_file(
            url=input_path,
            download_dir=download_dir,
            verify_ssl=verify_ssl,
            timeout=timeout
        )
        
        logger.info(f"Downloaded file from {input_path} to {local_file_path}")
        
        # Update state
        updated_state = state.copy()
        updated_state["file_paths"] = [local_file_path]
        
        return updated_state
    
    def _download_file(
        self,
        url: str, 
        download_dir: str,
        verify_ssl: bool,
        timeout: int
    ) -> str:
        """
        Download file from URL.
        
        Args:
            url: URL to download from
            download_dir: Directory to save to
            verify_ssl: Whether to verify SSL
            timeout: Request timeout
            
        Returns:
            Path to downloaded file
        """
        import requests
        from urllib.parse import urlparse
        
        # Parse URL to get filename
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # Generate filename if not available
        if not filename or "." not in filename:
            filename = f"downloaded_file_{hash(url) % 10000}"
            
        local_file_path = os.path.join(download_dir, filename)
        
        # Download with streaming for large files
        response = requests.get(
            url,
            stream=True,
            verify=verify_ssl,
            timeout=timeout
        )
        response.raise_for_status()
        
        # Write to file
        with open(local_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return local_file_path


@register_component(
    "scanner",
    "pattern_scanner",
    description="Scans files matching specific patterns across multiple directories",
    config_schema={
        "type": "object", 
        "properties": {
            "search_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of directories to search in",
                "default": ["."]
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"}, 
                "description": "List of glob patterns to search for",
                "default": ["**/*.pdf", "**/*.txt", "**/*.docx"]
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether pattern matching is case sensitive",
                "default": False
            }
        }
    }
)
class PatternScanner(Scanner):
    """
    Advanced scanner that uses glob patterns across multiple directories.
    
    Supports complex pattern matching and can search across multiple
    root directories simultaneously.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Scan multiple directories using glob patterns.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with file_paths set
        """
        input_path = state.get("input_path", "")
        
        # Get configuration
        search_paths = self.get_config_value("search_paths", [input_path] if input_path else ["."])
        patterns = self.get_config_value("patterns", ["**/*.pdf", "**/*.txt", "**/*.docx"])
        case_sensitive = self.get_config_value("case_sensitive", False)
        
        # Discover files using patterns
        file_paths = self._pattern_search(search_paths, patterns, case_sensitive)
        
        logger.info(f"Found {len(file_paths)} files matching patterns")
        
        # Update state
        updated_state = state.copy()
        updated_state["file_paths"] = file_paths
        
        return updated_state
    
    def _pattern_search(
        self,
        search_paths: List[str],
        patterns: List[str], 
        case_sensitive: bool
    ) -> List[str]:
        """
        Search for files matching patterns in multiple directories.
        
        Args:
            search_paths: Directories to search in
            patterns: Glob patterns to match
            case_sensitive: Whether matching is case sensitive
            
        Returns:
            List of matching file paths
        """
        discovered_files: Set[str] = set()
        
        for search_path in search_paths:
            if not os.path.exists(search_path):
                logger.warning(f"Search path does not exist: {search_path}")
                continue
                
            for pattern in patterns:
                # Make pattern case insensitive if requested
                search_pattern = pattern
                if not case_sensitive:
                    # This is a simple approach - for more complex case insensitivity,
                    # would need to implement custom matching
                    search_pattern = pattern.lower()
                
                # Combine search path with pattern
                full_pattern = os.path.join(search_path, search_pattern)
                
                # Find matches
                matches = glob.glob(full_pattern, recursive=True)
                
                for match in matches:
                    if os.path.isfile(match):
                        discovered_files.add(os.path.abspath(match))
        
        return sorted(list(discovered_files))