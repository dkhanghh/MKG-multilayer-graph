"""
CSV reader component for KAG-LangGraph pipeline.

This module contains a reader implementation that extracts data from CSV files,
converting each row into a chunk with metadata and optional embeddings.
"""

import csv
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from .base import Reader
from ..models.chunk import Chunk, ChunkType
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component

logger = logging.getLogger(__name__)


@register_component(
    "reader",
    "csv_reader",
    description="Reads CSV files and converts rows to chunks with metadata and embeddings support",
    config_schema={
        "type": "object",
        "properties": {
            "encoding": {
                "type": "string",
                "description": "CSV file encoding",
                "default": "utf-8"
            },
            "content_column": {
                "type": "string",
                "description": "Name of the column containing main text content",
                "default": "content"
            },
            "id_column": {
                "type": "string",
                "description": "Name of the column containing unique identifiers",
                "default": "_id"
            },
            "metadata_columns": {
                "type": "array",
                "description": "List of column names to include as metadata",
                "default": ["company_code", "company_name", "year", "quarter", "report_type", "language"]
            },
            "embedding_column": {
                "type": "string",
                "description": "Name of the column containing embeddings (PostgreSQL array format)",
                "default": "content_vector"
            },
            "use_existing_embeddings": {
                "type": "boolean",
                "description": "Whether to parse and use embeddings from the embedding_column",
                "default": True
            },
            "skip_empty_content": {
                "type": "boolean",
                "description": "Whether to skip rows with empty content",
                "default": True
            },
            "filter_conditions": {
                "type": "object",
                "description": "Dictionary of column:value pairs for filtering rows",
                "default": {}
            }
        }
    }
)
class CSVReader(Reader):
    """
    Reader for CSV files with metadata and embeddings support.

    Extracts data from CSV files, converting each row into a Chunk object.
    Supports:
    - Configurable column mapping
    - Metadata extraction from specified columns
    - PostgreSQL array format embedding parsing
    - Row filtering based on column values
    - UTF-8 encoding for international text (e.g., Vietnamese)
    """

    def process(self, state: PipelineState) -> PipelineState:
        """
        Process CSV files and create chunks.

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
                logger.info(f"Reading CSV file: {file_path}")
                file_chunks = self._read_csv_file(file_path)
                chunks.extend(file_chunks)
                logger.info(f"Created {len(file_chunks)} chunks from {file_path}")
            except ValueError:
                # Re-raise ValueError for validation errors (missing columns, etc.)
                raise
            except Exception as e:
                logger.error(f"Error reading CSV file {file_path}: {e}")
                continue

        logger.info(f"Total: Created {len(chunks)} chunks from {len(file_paths)} CSV file(s)")

        # Update state
        updated_state = state.copy()
        updated_state["chunks"] = chunks

        return updated_state

    def _read_csv_file(self, file_path: str) -> List[Chunk]:
        """
        Read a CSV file and create chunks from rows.

        Args:
            file_path: Path to the CSV file

        Returns:
            List of chunks
        """
        encoding = self.get_config_value("encoding", "utf-8")
        content_column = self.get_config_value("content_column", "content")
        skip_empty = self.get_config_value("skip_empty_content", True)

        chunks = []
        skipped_rows = 0

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)

                # Validate required columns
                if reader.fieldnames:
                    if content_column not in reader.fieldnames:
                        raise ValueError(
                            f"Content column '{content_column}' not found in CSV. "
                            f"Available columns: {reader.fieldnames}"
                        )

                for row_index, row in enumerate(reader):
                    # Skip empty content if configured
                    content_value = row.get(content_column, "")
                    if content_value is None:
                        content_value = ""
                    if skip_empty and not content_value.strip():
                        skipped_rows += 1
                        continue

                    # Create chunk from row
                    chunk = self._create_chunk_from_row(row, row_index, file_path)

                    if chunk:
                        chunks.append(chunk)
                    else:
                        skipped_rows += 1

            if skipped_rows > 0:
                logger.info(f"Skipped {skipped_rows} rows (empty content or filtered out)")

        except FileNotFoundError:
            logger.error(f"CSV file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            raise

        return chunks

    def _create_chunk_from_row(
        self,
        row: Dict[str, str],
        row_index: int,
        file_path: str
    ) -> Optional[Chunk]:
        """
        Create a chunk from a CSV row.

        Args:
            row: Dictionary representing a CSV row
            row_index: Index of the row in the CSV
            file_path: Path to the source CSV file

        Returns:
            Chunk object or None if row should be skipped
        """
        content_column = self.get_config_value("content_column", "content")
        id_column = self.get_config_value("id_column", "_id")
        metadata_columns = self.get_config_value("metadata_columns", [])
        embedding_column = self.get_config_value("embedding_column", "content_vector")
        use_embeddings = self.get_config_value("use_existing_embeddings", True)
        filter_conditions = self.get_config_value("filter_conditions", {})

        # Apply filters
        if not self._apply_filters(row, filter_conditions):
            return None

        # Extract content
        content = row.get(content_column, "")
        if content is None:
            content = ""
        content = content.strip()
        if not content:
            return None

        # Generate chunk ID
        csv_filename = Path(file_path).stem
        row_id = row.get(id_column, f"row_{row_index}")
        chunk_id = f"{csv_filename}_{row_id}"

        # Extract metadata
        processing_metadata = {
            "source_type": "csv",
            "source_file": file_path,
            "csv_row_index": row_index,
        }

        # Add configured metadata columns
        for col in metadata_columns:
            if col in row:
                value = row[col]
                # Handle None/empty values
                if value is None or value == "":
                    processing_metadata[col] = None
                    continue
                # Convert boolean strings to actual booleans
                if isinstance(value, str) and value.lower() in ('t', 'true', '1'):
                    value = True
                elif isinstance(value, str) and value.lower() in ('f', 'false', '0'):
                    value = False
                processing_metadata[col] = value

        # Parse embeddings if enabled
        embeddings = None
        if use_embeddings and embedding_column in row:
            embeddings = self._parse_postgres_array(row[embedding_column])
            if embeddings:
                logger.debug(f"Parsed {len(embeddings)} dimensions for chunk {chunk_id}")

        # Create chunk
        try:
            chunk = Chunk(
                id=chunk_id,
                content=content,
                chunk_type=ChunkType.TEXT,
                chunk_index=row_index,
                embeddings=embeddings,
                processing_metadata=processing_metadata
            )
            return chunk
        except Exception as e:
            logger.error(f"Error creating chunk from row {row_index}: {e}")
            return None

    def _parse_postgres_array(self, array_str: str) -> Optional[List[float]]:
        """
        Parse PostgreSQL array format to Python list of floats.

        PostgreSQL arrays are formatted as: {0.058532715,0.047607422,-0.013374329,...}

        Args:
            array_str: PostgreSQL array string

        Returns:
            List of floats or None if parsing fails
        """
        if not array_str or not isinstance(array_str, str):
            return None

        # Remove leading/trailing whitespace
        array_str = array_str.strip()

        # Check for empty array
        if array_str in ('{}', ''):
            return None

        # Remove braces
        if array_str.startswith('{') and array_str.endswith('}'):
            array_str = array_str[1:-1]

        # Split by comma and convert to floats
        try:
            values = [float(x.strip()) for x in array_str.split(',') if x.strip()]
            return values if values else None
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse embedding array: {e}")
            return None

    def _apply_filters(self, row: Dict[str, str], filter_conditions: Dict[str, Any]) -> bool:
        """
        Check if a row passes filter conditions.

        Args:
            row: CSV row dictionary
            filter_conditions: Dictionary of column:value pairs to match

        Returns:
            True if row passes all filters, False otherwise
        """
        if not filter_conditions:
            return True

        for column, expected_value in filter_conditions.items():
            if column not in row:
                logger.warning(f"Filter column '{column}' not found in CSV row")
                return False

            actual_value = row[column]

            # Handle case-insensitive string comparison
            if isinstance(expected_value, str):
                if actual_value.lower() != expected_value.lower():
                    return False
            else:
                if actual_value != str(expected_value):
                    return False

        return True
