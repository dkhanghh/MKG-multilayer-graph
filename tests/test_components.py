"""
Basic tests for KAG-LangGraph components.

This module contains unit tests for the core pipeline components
to ensure they work correctly in isolation and integration.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

# Add the package to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.components.scanner import FileScanner, DirectoryScanner
from knowledge_graphs.components.reader import TXTReader, MixedReader
from knowledge_graphs.components.splitter import LengthSplitter
from knowledge_graphs.components.extractor import RegexExtractor, KeywordExtractor
from knowledge_graphs.components.vectorizer import NoOpVectorizer
from knowledge_graphs.components.writer import JSONWriter, CSVWriter
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.pipeline_state import PipelineStateManager
from knowledge_graphs.models.chunk import Chunk, ChunkType
from knowledge_graphs.models.graph import SubGraph, Node, Edge


class TestScanner:
    """Test scanner components."""
    
    def test_file_scanner(self):
        """Test FileScanner component."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test content")
            test_file = f.name
        
        try:
            # Create scanner
            config = ComponentConfig(type="file_scanner")
            scanner = FileScanner(config)
            
            # Create initial state
            state = PipelineStateManager.create_initial_state(
                pipeline_id="test", 
                input_path=test_file,
                config={}
            )
            
            # Process
            result_state = scanner.process(state)
            
            # Verify results
            assert "file_paths" in result_state
            assert result_state["file_paths"] == [test_file]
            
        finally:
            os.unlink(test_file)
    
    def test_directory_scanner(self):
        """Test DirectoryScanner component."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file1 = Path(temp_dir) / "test1.txt"
            test_file2 = Path(temp_dir) / "test2.md"
            
            test_file1.write_text("Test content 1")
            test_file2.write_text("Test content 2")
            
            # Create scanner
            config = ComponentConfig(
                type="directory_scanner",
                config={
                    "file_patterns": ["*.txt", "*.md"],
                    "recursive": False
                }
            )
            scanner = DirectoryScanner(config)
            
            # Create state
            state = PipelineStateManager.create_initial_state(
                pipeline_id="test",
                input_path=temp_dir,
                config={}
            )
            
            # Process
            result_state = scanner.process(state)
            
            # Verify results
            assert "file_paths" in result_state
            file_paths = result_state["file_paths"]
            assert len(file_paths) == 2
            assert str(test_file1) in file_paths
            assert str(test_file2) in file_paths


class TestReader:
    """Test reader components."""
    
    def test_txt_reader(self):
        """Test TXTReader component."""
        test_content = "This is a test document.\nIt has multiple lines.\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            test_file = f.name
        
        try:
            # Create reader
            config = ComponentConfig(type="txt_reader")
            reader = TXTReader(config)
            
            # Create state with file paths
            state = {
                "file_paths": [test_file],
                "pipeline_id": "test"
            }
            
            # Process
            result_state = reader.process(state)
            
            # Verify results
            assert "chunks" in result_state
            chunks = result_state["chunks"]
            assert len(chunks) == 1
            assert chunks[0].content.strip() == test_content.strip()
            assert chunks[0].source_file == test_file
            
        finally:
            os.unlink(test_file)
    
    def test_mixed_reader(self):
        """Test MixedReader component."""
        # Create test TXT file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test TXT content")
            txt_file = f.name
        
        try:
            # Create reader
            config = ComponentConfig(
                type="mixed_reader",
                config={"supported_types": ["txt", "md"]}
            )
            reader = MixedReader(config)
            
            # Create state
            state = {
                "file_paths": [txt_file],
                "pipeline_id": "test"
            }
            
            # Process
            result_state = reader.process(state)
            
            # Verify results
            assert "chunks" in result_state
            chunks = result_state["chunks"]
            assert len(chunks) == 1
            assert chunks[0].content == "Test TXT content"
            
        finally:
            os.unlink(txt_file)


class TestSplitter:
    """Test splitter components."""
    
    def test_length_splitter(self):
        """Test LengthSplitter component."""
        # Create a long chunk
        long_content = "This is a sentence. " * 100  # Much longer than chunk size
        chunk = Chunk(
            id="test_chunk",
            content=long_content,
            chunk_type=ChunkType.TEXT,
            source_file="test.txt"
        )
        
        # Create splitter
        config = ComponentConfig(
            type="length_splitter",
            config={
                "chunk_size": 100,
                "chunk_overlap": 20,
                "split_by": "character"
            }
        )
        splitter = LengthSplitter(config)
        
        # Create state
        state = {
            "chunks": [chunk],
            "pipeline_id": "test"
        }
        
        # Process
        result_state = splitter.process(state)
        
        # Verify results
        assert "split_chunks" in result_state
        split_chunks = result_state["split_chunks"]
        assert len(split_chunks) > 1  # Should be split into multiple chunks
        
        # Check that chunks are smaller
        for chunk in split_chunks:
            assert len(chunk.content) <= 120  # Some tolerance for overlap


class TestExtractor:
    """Test extractor components."""
    
    def test_regex_extractor(self):
        """Test RegexExtractor component."""
        # Create chunk with email addresses
        content = "Contact us at john@example.com or support@test.org for help."
        chunk = Chunk(
            id="test_chunk",
            content=content,
            chunk_type=ChunkType.TEXT,
            source_file="test.txt"
        )
        
        # Create extractor
        config = ComponentConfig(
            type="regex_extractor",
            config={
                "patterns": {
                    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                },
                "case_sensitive": False
            }
        )
        extractor = RegexExtractor(config)
        
        # Create state
        state = {
            "split_chunks": [chunk],
            "pipeline_id": "test"
        }
        
        # Process
        result_state = extractor.process(state)
        
        # Verify results
        assert "subgraphs" in result_state
        subgraphs = result_state["subgraphs"]
        assert len(subgraphs) == 1
        
        subgraph = subgraphs[0]
        assert len(subgraph.nodes) == 2  # Two email addresses
        
        # Check node names
        node_names = [node.name for node in subgraph.nodes]
        assert "john@example.com" in node_names
        assert "support@test.org" in node_names
    
    def test_keyword_extractor(self):
        """Test KeywordExtractor component."""
        content = "John works at Tech Corp in San Francisco."
        chunk = Chunk(
            id="test_chunk",
            content=content,
            chunk_type=ChunkType.TEXT,
            source_file="test.txt"
        )
        
        # Create extractor
        config = ComponentConfig(
            type="keyword_extractor",
            config={
                "keywords": {
                    "Person": ["John"],
                    "Company": ["Tech Corp"],
                    "Location": ["San Francisco"]
                },
                "case_sensitive": False,
                "word_boundaries": True
            }
        )
        extractor = KeywordExtractor(config)
        
        # Create state
        state = {
            "split_chunks": [chunk],
            "pipeline_id": "test"
        }
        
        # Process
        result_state = extractor.process(state)
        
        # Verify results
        assert "subgraphs" in result_state
        subgraphs = result_state["subgraphs"]
        assert len(subgraphs) == 1
        
        subgraph = subgraphs[0]
        assert len(subgraph.nodes) == 3  # Three keywords found
        
        # Check node types
        node_types = [node.node_type for node in subgraph.nodes]
        assert "Person" in node_types
        assert "Company" in node_types
        assert "Location" in node_types


class TestVectorizer:
    """Test vectorizer components."""
    
    def test_no_op_vectorizer(self):
        """Test NoOpVectorizer component."""
        # Create a subgraph
        node = Node(id="test_node", name="Test Entity", node_type="Test")
        subgraph = SubGraph(nodes=[node])
        
        # Create vectorizer
        config = ComponentConfig(type="no_op_vectorizer")
        vectorizer = NoOpVectorizer(config)
        
        # Create state
        state = {
            "subgraphs": [subgraph],
            "pipeline_id": "test"
        }
        
        # Process
        result_state = vectorizer.process(state)
        
        # Verify results
        assert "vectorized_subgraphs" in result_state
        vectorized_subgraphs = result_state["vectorized_subgraphs"]
        assert len(vectorized_subgraphs) == 1
        assert vectorized_subgraphs[0].nodes[0].name == "Test Entity"


class TestWriter:
    """Test writer components."""
    
    def test_json_writer(self):
        """Test JSONWriter component."""
        # Create a subgraph
        node = Node(id="test_node", name="Test Entity", node_type="Test")
        edge = Edge(id="test_edge", source_id="test_node", target_id="test_node", relation_type="self_reference")
        subgraph = SubGraph(nodes=[node], edges=[edge])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "test_output.json")
            
            # Create writer
            config = ComponentConfig(
                type="json_writer",
                config={
                    "output_path": output_path,
                    "pretty_print": True,
                    "include_metadata": True
                }
            )
            writer = JSONWriter(config)
            
            # Create state
            state = {
                "vectorized_subgraphs": [subgraph],
                "pipeline_id": "test"
            }
            
            # Process
            result_state = writer.process(state)
            
            # Verify results
            assert "output_path" in result_state
            assert result_state["output_path"] == output_path
            
            # Check file was created
            assert os.path.exists(output_path)
            
            # Check file content
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert "nodes" in data
            assert "edges" in data
            assert len(data["nodes"]) == 1
            assert len(data["edges"]) == 1
            assert data["nodes"][0]["name"] == "Test Entity"
    
    def test_csv_writer(self):
        """Test CSVWriter component."""
        # Create a subgraph
        node = Node(id="test_node", name="Test Entity", node_type="Test")
        subgraph = SubGraph(nodes=[node])
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create writer
            config = ComponentConfig(
                type="csv_writer",
                config={
                    "output_dir": temp_dir,
                    "nodes_filename": "test_nodes.csv",
                    "edges_filename": "test_edges.csv"
                }
            )
            writer = CSVWriter(config)
            
            # Create state
            state = {
                "vectorized_subgraphs": [subgraph],
                "pipeline_id": "test"
            }
            
            # Process
            result_state = writer.process(state)
            
            # Verify results
            assert "output_path" in result_state
            
            # Check files were created
            nodes_path = os.path.join(temp_dir, "test_nodes.csv")
            edges_path = os.path.join(temp_dir, "test_edges.csv")
            
            assert os.path.exists(nodes_path)
            assert os.path.exists(edges_path)
            
            # Check nodes CSV content
            with open(nodes_path, 'r') as f:
                content = f.read()
                assert "test_node" in content
                assert "Test Entity" in content


class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    def test_simple_pipeline_flow(self):
        """Test a simple end-to-end pipeline flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Contact Alice at alice@example.com or Bob at bob@test.org.")
            
            # Create initial state
            state = PipelineStateManager.create_initial_state(
                pipeline_id="integration_test",
                input_path=test_file,
                config={}
            )
            
            # Step 1: Scanner
            scanner_config = ComponentConfig(type="file_scanner")
            scanner = FileScanner(scanner_config)
            state = scanner.process(state)
            assert len(state["file_paths"]) == 1
            
            # Step 2: Reader
            reader_config = ComponentConfig(type="txt_reader")
            reader = TXTReader(reader_config)
            state = reader.process(state)
            assert len(state["chunks"]) == 1
            
            # Step 3: Splitter (no-op for small content)
            splitter_config = ComponentConfig(type="length_splitter", config={"chunk_size": 1000})
            splitter = LengthSplitter(splitter_config)
            state = splitter.process(state)
            assert len(state["split_chunks"]) >= 1
            
            # Step 4: Extractor
            extractor_config = ComponentConfig(
                type="regex_extractor",
                config={"patterns": {"email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'}}
            )
            extractor = RegexExtractor(extractor_config)
            state = extractor.process(state)
            assert len(state["subgraphs"]) == 1
            assert len(state["subgraphs"][0].nodes) == 2  # Two emails
            
            # Step 5: Vectorizer (no-op)
            vectorizer_config = ComponentConfig(type="no_op_vectorizer")
            vectorizer = NoOpVectorizer(vectorizer_config)
            state = vectorizer.process(state)
            assert len(state["vectorized_subgraphs"]) == 1
            
            # Step 6: Writer
            output_path = os.path.join(temp_dir, "output.json")
            writer_config = ComponentConfig(
                type="json_writer",
                config={"output_path": output_path}
            )
            writer = JSONWriter(writer_config)
            state = writer.process(state)
            assert state["output_path"] == output_path
            assert os.path.exists(output_path)
            
            # Verify final output
            with open(output_path, 'r') as f:
                data = json.load(f)
            assert len(data["nodes"]) == 2
            node_names = [node["name"] for node in data["nodes"]]
            assert "alice@example.com" in node_names
            assert "bob@test.org" in node_names


if __name__ == "__main__":
    # Run basic tests without pytest
    print("🧪 Running basic component tests...")
    
    # Test scanner
    test_scanner = TestScanner()
    test_scanner.test_file_scanner()
    print("✅ FileScanner test passed")
    
    # Test reader
    test_reader = TestReader()
    test_reader.test_txt_reader()
    print("✅ TXTReader test passed")
    
    # Test extractor
    test_extractor = TestExtractor()
    test_extractor.test_regex_extractor()
    print("✅ RegexExtractor test passed")
    
    # Test vectorizer
    test_vectorizer = TestVectorizer()
    test_vectorizer.test_no_op_vectorizer()
    print("✅ NoOpVectorizer test passed")
    
    # Test writer
    test_writer = TestWriter()
    test_writer.test_json_writer()
    print("✅ JSONWriter test passed")
    
    # Test integration
    test_integration = TestIntegration()
    test_integration.test_simple_pipeline_flow()
    print("✅ Integration test passed")
    
    print("\n🎉 All tests passed successfully!")