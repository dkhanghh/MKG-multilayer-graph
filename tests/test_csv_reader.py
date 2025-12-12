"""
Unit tests for CSV Reader component.
"""

import os
import csv
import tempfile
import unittest
from pathlib import Path

from knowledge_graphs.components.csv_reader import CSVReader
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.pipeline_state import PipelineState
from knowledge_graphs.models.chunk import Chunk, ChunkType


class TestCSVReader(unittest.TestCase):
    """Test cases for CSVReader component."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_csv(self, filename, rows, headers=None):
        """Helper to create a test CSV file."""
        if headers is None:
            headers = ["_id", "content", "company_code", "year"]

        csv_path = Path(self.temp_dir) / filename
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        return str(csv_path)

    def test_csv_reader_basic(self):
        """Test basic CSV reading functionality."""
        # Create test CSV
        rows = [
            {"_id": "1", "content": "Test content 1", "company_code": "ABC", "year": "2023"},
            {"_id": "2", "content": "Test content 2", "company_code": "XYZ", "year": "2023"},
        ]
        csv_path = self.create_test_csv("test.csv", rows)

        # Create reader
        config = ComponentConfig(
            type="csv_reader",
            config={
                "encoding": "utf-8",
                "content_column": "content",
                "id_column": "_id",
                "metadata_columns": ["company_code", "year"]
            }
        )
        reader = CSVReader(config)

        # Process
        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        # Verify
        self.assertIn("chunks", result_state)
        chunks = result_state["chunks"]
        self.assertEqual(len(chunks), 2)

        # Check first chunk
        chunk = chunks[0]
        self.assertIsInstance(chunk, Chunk)
        self.assertEqual(chunk.content, "Test content 1")
        self.assertIn("company_code", chunk.processing_metadata)
        self.assertEqual(chunk.processing_metadata["company_code"], "ABC")

    def test_metadata_extraction(self):
        """Test metadata extraction from CSV columns."""
        rows = [
            {
                "_id": "row1",
                "content": "Financial report",
                "company_code": "VPB",
                "company_name": "VPBank",
                "year": "2023",
                "quarter": "3",
                "language": "vi"
            }
        ]
        headers = ["_id", "content", "company_code", "company_name", "year", "quarter", "language"]
        csv_path = self.create_test_csv("test_metadata.csv", rows, headers)

        # Configure with all metadata columns
        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "id_column": "_id",
                "metadata_columns": ["company_code", "company_name", "year", "quarter", "language"]
            }
        )
        reader = CSVReader(config)

        # Process
        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        # Verify all metadata fields
        chunk = result_state["chunks"][0]
        metadata = chunk.processing_metadata

        self.assertEqual(metadata["company_code"], "VPB")
        self.assertEqual(metadata["company_name"], "VPBank")
        self.assertEqual(metadata["year"], "2023")
        self.assertEqual(metadata["quarter"], "3")
        self.assertEqual(metadata["language"], "vi")
        self.assertEqual(metadata["source_type"], "csv")
        self.assertIn("source_file", metadata)

    def test_embedding_parsing(self):
        """Test parsing PostgreSQL array format embeddings."""
        config = ComponentConfig(type="csv_reader", config={})
        reader = CSVReader(config)

        # Test valid array
        array_str = "{0.058532715,0.047607422,-0.013374329,0.123}"
        result = reader._parse_postgres_array(array_str)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertAlmostEqual(result[0], 0.058532715, places=6)
        self.assertAlmostEqual(result[2], -0.013374329, places=6)

        # Test empty array
        self.assertIsNone(reader._parse_postgres_array("{}"))
        self.assertIsNone(reader._parse_postgres_array(""))
        self.assertIsNone(reader._parse_postgres_array(None))

        # Test malformed array
        self.assertIsNone(reader._parse_postgres_array("{invalid}"))

    def test_filtering(self):
        """Test row filtering with filter conditions."""
        rows = [
            {"_id": "1", "content": "Content 1", "company_code": "ABC", "year": "2023"},
            {"_id": "2", "content": "Content 2", "company_code": "XYZ", "year": "2023"},
            {"_id": "3", "content": "Content 3", "company_code": "ABC", "year": "2022"},
        ]
        csv_path = self.create_test_csv("test_filter.csv", rows)

        # Configure with filter
        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "id_column": "_id",
                "metadata_columns": ["company_code", "year"],
                "filter_conditions": {
                    "company_code": "ABC",
                    "year": "2023"
                }
            }
        )
        reader = CSVReader(config)

        # Process
        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        # Should only get 1 chunk (ABC, 2023)
        chunks = result_state["chunks"]
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].processing_metadata["company_code"], "ABC")
        self.assertEqual(chunks[0].processing_metadata["year"], "2023")

    def test_empty_content_skipping(self):
        """Test skipping rows with empty content."""
        rows = [
            {"_id": "1", "content": "Valid content", "company_code": "ABC"},
            {"_id": "2", "content": "", "company_code": "XYZ"},
            {"_id": "3", "content": "   ", "company_code": "DEF"},
            {"_id": "4", "content": "Another valid", "company_code": "GHI"},
        ]
        csv_path = self.create_test_csv("test_empty.csv", rows)

        # Enable skip_empty_content
        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "skip_empty_content": True
            }
        )
        reader = CSVReader(config)

        # Process
        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        # Should only get 2 chunks (non-empty content)
        chunks = result_state["chunks"]
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].content, "Valid content")
        self.assertEqual(chunks[1].content, "Another valid")

    def test_encoding_utf8(self):
        """Test handling of UTF-8 encoded text (Vietnamese)."""
        rows = [
            {
                "_id": "1",
                "content": "Ngân hàng Thương mại Cổ phần Việt Nam Thịnh Vượng",
                "company_name": "VPBank"
            }
        ]
        headers = ["_id", "content", "company_name"]
        csv_path = self.create_test_csv("test_utf8.csv", rows, headers)

        # Configure reader
        config = ComponentConfig(
            type="csv_reader",
            config={
                "encoding": "utf-8",
                "content_column": "content",
                "metadata_columns": ["company_name"]
            }
        )
        reader = CSVReader(config)

        # Process
        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        # Verify Vietnamese text preserved
        chunk = result_state["chunks"][0]
        self.assertIn("Ngân hàng", chunk.content)
        self.assertIn("Việt Nam", chunk.content)
        self.assertEqual(chunk.processing_metadata["company_name"], "VPBank")

    def test_boolean_conversion(self):
        """Test conversion of boolean string values."""
        rows = [
            {"_id": "1", "content": "Content 1", "is_tabular": "t"},
            {"_id": "2", "content": "Content 2", "is_tabular": "f"},
            {"_id": "3", "content": "Content 3", "is_tabular": "True"},
            {"_id": "4", "content": "Content 4", "is_tabular": "false"},
        ]
        headers = ["_id", "content", "is_tabular"]
        csv_path = self.create_test_csv("test_bool.csv", rows, headers)

        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "metadata_columns": ["is_tabular"]
            }
        )
        reader = CSVReader(config)

        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        chunks = result_state["chunks"]
        self.assertEqual(chunks[0].processing_metadata["is_tabular"], True)
        self.assertEqual(chunks[1].processing_metadata["is_tabular"], False)
        self.assertEqual(chunks[2].processing_metadata["is_tabular"], True)
        self.assertEqual(chunks[3].processing_metadata["is_tabular"], False)

    def test_embeddings_integration(self):
        """Test full integration with embeddings."""
        rows = [
            {
                "_id": "test1",
                "content": "Test document",
                "content_vector": "{0.1,0.2,0.3}",
                "company_code": "ABC"
            }
        ]
        headers = ["_id", "content", "content_vector", "company_code"]
        csv_path = self.create_test_csv("test_embeddings.csv", rows, headers)

        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "embedding_column": "content_vector",
                "use_existing_embeddings": True,
                "metadata_columns": ["company_code"]
            }
        )
        reader = CSVReader(config)

        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        chunk = result_state["chunks"][0]
        self.assertIsNotNone(chunk.embeddings)
        self.assertEqual(len(chunk.embeddings), 3)
        self.assertEqual(chunk.embeddings, [0.1, 0.2, 0.3])

    def test_no_embeddings_when_disabled(self):
        """Test that embeddings are not parsed when disabled."""
        rows = [
            {
                "_id": "test1",
                "content": "Test document",
                "content_vector": "{0.1,0.2,0.3}"
            }
        ]
        headers = ["_id", "content", "content_vector"]
        csv_path = self.create_test_csv("test_no_embed.csv", rows, headers)

        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "use_existing_embeddings": False
            }
        )
        reader = CSVReader(config)

        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        chunk = result_state["chunks"][0]
        self.assertIsNone(chunk.embeddings)

    def test_missing_content_column_error(self):
        """Test error handling for missing content column."""
        rows = [{"_id": "1", "wrong_column": "data"}]
        headers = ["_id", "wrong_column"]
        csv_path = self.create_test_csv("test_error.csv", rows, headers)

        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content"  # This column doesn't exist
            }
        )
        reader = CSVReader(config)

        state = PipelineState(file_paths=[csv_path])

        with self.assertRaises(ValueError) as context:
            reader.process(state)

        self.assertIn("Content column", str(context.exception))

    def test_none_values_in_metadata(self):
        """Test handling of None values in metadata columns."""
        rows = [
            {"_id": "1", "content": "Valid content", "company_code": "ABC", "year": None},
            {"_id": "2", "content": "Another content", "company_code": None, "year": "2023"},
            {"_id": "3", "content": "Third content", "company_code": "", "year": ""},
        ]
        headers = ["_id", "content", "company_code", "year"]
        csv_path = self.create_test_csv("test_none.csv", rows, headers)

        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "metadata_columns": ["company_code", "year"]
            }
        )
        reader = CSVReader(config)

        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        chunks = result_state["chunks"]
        self.assertEqual(len(chunks), 3)

        # First chunk: year is None
        self.assertEqual(chunks[0].processing_metadata["company_code"], "ABC")
        self.assertIsNone(chunks[0].processing_metadata["year"])

        # Second chunk: company_code is None
        self.assertIsNone(chunks[1].processing_metadata["company_code"])
        self.assertEqual(chunks[1].processing_metadata["year"], "2023")

        # Third chunk: both are empty strings (converted to None)
        self.assertIsNone(chunks[2].processing_metadata["company_code"])
        self.assertIsNone(chunks[2].processing_metadata["year"])

    def test_none_value_in_content(self):
        """Test handling of None value in content column."""
        rows = [
            {"_id": "1", "content": "Valid content", "company_code": "ABC"},
            {"_id": "2", "content": None, "company_code": "XYZ"},
            {"_id": "3", "content": "Another valid", "company_code": "DEF"},
        ]
        headers = ["_id", "content", "company_code"]
        csv_path = self.create_test_csv("test_none_content.csv", rows, headers)

        config = ComponentConfig(
            type="csv_reader",
            config={
                "content_column": "content",
                "skip_empty_content": True
            }
        )
        reader = CSVReader(config)

        state = PipelineState(file_paths=[csv_path])
        result_state = reader.process(state)

        # Should skip row with None content
        chunks = result_state["chunks"]
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].content, "Valid content")
        self.assertEqual(chunks[1].content, "Another valid")


if __name__ == "__main__":
    unittest.main()
