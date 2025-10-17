"""
FinanceBench Reader component for KAG-LangGraph pipeline.

This module contains a specialized reader for FinanceBench financial documents
that parses the unique multi-section format with metadata and page information.
"""

import os
import re
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
    "financebench_reader",
    description="Reads FinanceBench financial statement files with metadata parsing",
    config_schema={
        "type": "object",
        "properties": {
            "encoding": {
                "type": "string",
                "description": "Text file encoding",
                "default": "utf-8"
            },
            "preserve_page_structure": {
                "type": "boolean",
                "description": "Keep each page as a separate chunk",
                "default": True
            },
            "detect_statement_type": {
                "type": "boolean",
                "description": "Detect financial statement types in content",
                "default": True
            },
            "extract_metadata": {
                "type": "boolean",
                "description": "Extract document metadata (doc_name, page numbers, etc.)",
                "default": True
            }
        }
    }
)
class FinanceBenchReader(Reader):
    """
    Reader for FinanceBench financial statement files.

    FinanceBench format structure:
    Line 1: financebench_id: <id>
    Line 2+: [Optional blank line or content]
    ...
    doc_name: <document_name>
    evidence_page_num: <page_number>
    evidence_text_full_page: <full page text content>

    This reader parses the structure and creates chunks with rich metadata.
    """

    # Financial statement type patterns
    STATEMENT_PATTERNS = {
        'balance_sheet': [
            r'balance\s+sheet',
            r'statement\s+of\s+financial\s+position',
            r'consolidated\s+balance\s+sheet'
        ],
        'income_statement': [
            r'income\s+statement',
            r'statement\s+of\s+operations',
            r'statement\s+of\s+earnings',
            r'consolidated\s+statement\s+of\s+operations',
            r'profit\s+and\s+loss'
        ],
        'cash_flow': [
            r'cash\s+flow',
            r'statement\s+of\s+cash\s+flows',
            r'consolidated\s+statement\s+of\s+cash\s+flows'
        ],
        'shareholders_equity': [
            r'shareholders.*equity',
            r'statement\s+of\s+stockholders.*equity',
            r'changes\s+in\s+equity'
        ]
    }

    def process(self, state: PipelineState) -> PipelineState:
        """
        Process FinanceBench files and create chunks.

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
                if self._is_financebench_file(file_path):
                    file_chunks = self._read_financebench_file(file_path)
                    chunks.extend(file_chunks)
                    logger.info(f"Parsed FinanceBench file: {file_path} → {len(file_chunks)} chunks")
                else:
                    logger.warning(f"File does not match FinanceBench format: {file_path}")
            except Exception as e:
                logger.error(f"Error reading FinanceBench file {file_path}: {e}")
                continue

        logger.info(f"Created {len(chunks)} chunks from {len(file_paths)} FinanceBench files")

        # Update state
        updated_state = state.copy()
        updated_state["chunks"] = chunks

        return updated_state

    def _is_financebench_file(self, file_path: str) -> bool:
        """
        Check if file matches FinanceBench format.

        Args:
            file_path: Path to the file

        Returns:
            True if file appears to be FinanceBench format
        """
        # Check filename pattern
        filename = Path(file_path).name
        if filename.startswith('financebench_id_') and filename.endswith('.txt'):
            return True

        # Also check content structure (first line)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                return first_line.startswith('financebench_id:')
        except Exception:
            return False

    def _read_financebench_file(self, file_path: str) -> List[Chunk]:
        """
        Read a FinanceBench file and create structured chunks.

        Args:
            file_path: Path to the FinanceBench file

        Returns:
            List of chunks with metadata
        """
        encoding = self.get_config_value("encoding", "utf-8")
        preserve_pages = self.get_config_value("preserve_page_structure", True)
        detect_statement = self.get_config_value("detect_statement_type", True)
        extract_metadata = self.get_config_value("extract_metadata", True)

        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        # Parse the FinanceBench structure
        parsed_data = self._parse_financebench_structure(content, file_path)

        if not parsed_data:
            logger.warning(f"Could not parse FinanceBench structure from {file_path}")
            return []

        chunks = []
        financebench_id = parsed_data['financebench_id']
        sections = parsed_data['sections']

        # Create chunks from sections
        for idx, section in enumerate(sections):
            doc_name = section.get('doc_name', 'unknown')
            page_num = section.get('page_number')
            page_content = section.get('content', '')

            if not page_content.strip():
                continue

            # Detect statement type if enabled
            statement_type = None
            if detect_statement:
                statement_type = self._detect_statement_type(page_content)

            # Extract time periods from content
            periods = self._extract_periods(page_content)

            # Create chunk metadata
            metadata = {}
            if extract_metadata:
                metadata = {
                    'financebench_id': financebench_id,
                    'doc_name': doc_name,
                    'statement_type': statement_type,
                    'periods': periods,
                    'source_file': str(file_path)
                }

            # Create chunk ID
            chunk_id = f"{financebench_id}_page_{page_num}" if page_num else f"{financebench_id}_chunk_{idx}"

            # Create chunk
            chunk = Chunk(
                id=chunk_id,
                content=page_content.strip(),
                chunk_type=ChunkType.TEXT,
                page_number=page_num,
                chunk_index=idx,
                processing_metadata=metadata
            )
            chunks.append(chunk)

        return chunks

    def _parse_financebench_structure(self, content: str, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse the FinanceBench file structure.

        Format:
        Line 1: financebench_id: <id>
        [blank line or content]
        doc_name: <name>
        evidence_page_num: <num>
        evidence_text_full_page: <content...>
        [more sections...]

        Args:
            content: File content
            file_path: File path for logging

        Returns:
            Dictionary with financebench_id and sections
        """
        lines = content.split('\n')

        # Extract financebench_id from first line
        if not lines or not lines[0].startswith('financebench_id:'):
            logger.error(f"Invalid FinanceBench format: missing financebench_id in {file_path}")
            return None

        financebench_id = lines[0].replace('financebench_id:', '').strip()

        # Parse sections
        sections = []
        current_section = None
        in_evidence_text = False
        evidence_lines = []

        for i, line in enumerate(lines[1:], start=1):
            # Check for section markers
            if line.startswith('doc_name:'):
                # Save previous section if exists
                if current_section and evidence_lines:
                    current_section['content'] = '\n'.join(evidence_lines).strip()
                    sections.append(current_section)

                # Start new section
                current_section = {
                    'doc_name': line.replace('doc_name:', '').strip()
                }
                evidence_lines = []
                in_evidence_text = False

            elif line.startswith('evidence_page_num:'):
                if current_section:
                    page_num_str = line.replace('evidence_page_num:', '').strip()
                    try:
                        current_section['page_number'] = int(page_num_str)
                    except ValueError:
                        current_section['page_number'] = None
                        logger.warning(f"Could not parse page number: {page_num_str}")

            elif line.startswith('evidence_text_full_page:'):
                # Start collecting evidence text
                in_evidence_text = True
                # First line of evidence might be on same line
                evidence_text_start = line.replace('evidence_text_full_page:', '').strip()
                if evidence_text_start:
                    evidence_lines.append(evidence_text_start)

            elif in_evidence_text:
                # Collect evidence text lines until next section
                # Stop if we hit another doc_name marker
                if line.startswith('doc_name:'):
                    # This is the next section, don't include this line
                    # Backtrack - process this line in next iteration
                    continue
                evidence_lines.append(line)

        # Don't forget last section
        if current_section and evidence_lines:
            current_section['content'] = '\n'.join(evidence_lines).strip()
            sections.append(current_section)

        return {
            'financebench_id': financebench_id,
            'sections': sections
        }

    def _detect_statement_type(self, content: str) -> Optional[str]:
        """
        Detect the type of financial statement from content.

        Args:
            content: Page content

        Returns:
            Statement type string or None
        """
        content_lower = content.lower()

        for statement_type, patterns in self.STATEMENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    return statement_type

        return None

    def _extract_periods(self, content: str) -> List[str]:
        """
        Extract time periods/dates from financial statement content.

        Common formats:
        - December 31, 2022
        - 2022-12-31
        - Q4 2023
        - FY2022

        Args:
            content: Page content

        Returns:
            List of extracted periods
        """
        periods = []

        # Pattern: Month DD, YYYY (e.g., December 31, 2022)
        month_day_year = re.findall(
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b',
            content,
            re.IGNORECASE
        )
        periods.extend(month_day_year)

        # Pattern: YYYY-MM-DD
        iso_dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', content)
        periods.extend(iso_dates)

        # Pattern: Q1/Q2/Q3/Q4 YYYY
        quarters = re.findall(r'\bQ[1-4]\s+\d{4}\b', content, re.IGNORECASE)
        periods.extend(quarters)

        # Pattern: FY YYYY or Fiscal Year YYYY
        fiscal_years = re.findall(r'\b(?:FY|Fiscal\s+Year)\s*\d{4}\b', content, re.IGNORECASE)
        periods.extend(fiscal_years)

        # Return unique periods (preserve order)
        seen = set()
        unique_periods = []
        for period in periods:
            if period not in seen:
                seen.add(period)
                unique_periods.append(period)

        return unique_periods[:10]  # Limit to 10 most prominent periods
