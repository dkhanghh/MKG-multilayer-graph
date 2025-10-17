"""
Unit tests for LLMExtractor and GeminiVectorizer components.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from knowledge_graphs.components.extractor import LLMExtractor
from knowledge_graphs.components.vectorizer import GeminiVectorizer
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.chunk import Chunk
from knowledge_graphs.models.graph import SubGraph, Node, Edge
from knowledge_graphs.models.pipeline_state import PipelineState


class TestLLMExtractor:
    """Test cases for LLMExtractor component."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing."""
        client = Mock()
        client.simple_chat = Mock()
        return client

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for LLMExtractor."""
        return ComponentConfig(
            type="llm_extractor",
            name="test_extractor",
            enabled=True,
            config={
                "llm_provider": "openai",
                "model": "gpt-4",
                "api_key": "test-key",
                "temperature": 0.1,
                "max_tokens": 2000,
                "entity_types": ["Person", "Organization", "Location"],
                "relation_types": ["works_for", "located_in", "related_to"],
                "use_template": True,
                "template_name": "ner.md"
            }
        )

    @pytest.fixture
    def sample_chunk(self):
        """Sample chunk for testing."""
        return Chunk(
            id="chunk_1",
            content="John Smith works at Microsoft in Seattle.",
            source_file="test.txt",
            page_number=1
        )

    @pytest.fixture
    def sample_pipeline_state(self, sample_chunk):
        """Sample pipeline state with chunks."""
        return PipelineState(chunks=[sample_chunk])

    @patch('knowledge_graphs.components.extractor.create_llm_client')
    def test_llm_extractor_initialization(self, mock_create_client, sample_config):
        """Test LLMExtractor initialization."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        extractor = LLMExtractor(sample_config)

        assert extractor.llm_client == mock_client
        assert extractor.entity_types == ["Person", "Organization", "Location"]
        assert extractor.relation_types == ["works_for", "located_in", "related_to"]
        assert extractor.name == "test_extractor"
        mock_create_client.assert_called_once()

    @patch('knowledge_graphs.components.extractor.create_llm_client')
    @patch('knowledge_graphs.components.extractor.extract_json_from_response')
    @patch('knowledge_graphs.components.extractor.load_prompt_template')
    def test_template_based_extraction(self, mock_load_template, mock_extract_json,
                                     mock_create_client, sample_config, sample_chunk):
        """Test template-based extraction (NER -> STD -> Triple)."""
        # Setup mocks
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_load_template.return_value = "test prompt"

        # Mock extraction results
        ner_result = {
            "entities": [
                {"name": "John Smith", "category": "Person", "id": "john_smith"}
            ]
        }
        std_result = {
            "entities": [
                {"name": "John Smith", "category": "Person", "id": "john_smith", "official_name": "John Smith"}
            ]
        }
        triple_result = {
            "relationships": [
                {"source_id": "john_smith", "target_id": "microsoft", "relation_type": "works_for", "confidence": 0.9}
            ]
        }

        mock_extract_json.side_effect = [ner_result, std_result, triple_result]
        mock_client.simple_chat.return_value = "mock response"

        extractor = LLMExtractor(sample_config)
        subgraph = extractor._extract_from_chunk(sample_chunk)

        # Verify the extraction process
        assert mock_client.simple_chat.call_count == 3  # NER, STD, Triple
        assert isinstance(subgraph, SubGraph)
        assert len(subgraph.nodes) == 1
        assert subgraph.nodes[0].name == "John Smith"

    @patch('knowledge_graphs.components.extractor.create_llm_client')
    def test_create_node_from_entity(self, mock_create_client, sample_config, sample_chunk):
        """Test node creation from entity data."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        extractor = LLMExtractor(sample_config)

        entity_data = {
            "id": "john_smith",
            "name": "John Smith",
            "category": "Person",
            "official_name": "John Smith",
            "description": "Software engineer"
        }

        node = extractor._create_node_from_entity(sample_chunk, entity_data)

        assert node.id == "john_smith"
        assert node.name == "John Smith"
        assert node.node_type == "Person"
        assert node.official_name == "John Smith"
        assert node.get_property("description") == "Software engineer"
        assert sample_chunk.id in node.source_chunks

    @patch('knowledge_graphs.components.extractor.create_llm_client')
    def test_create_edge_from_relationship(self, mock_create_client, sample_config, sample_chunk):
        """Test edge creation from relationship data."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        extractor = LLMExtractor(sample_config)

        # Create entity map
        node1 = Node(id="john_smith", name="John Smith", node_type="Person", official_name="John Smith")
        node2 = Node(id="microsoft", name="Microsoft", node_type="Organization", official_name="Microsoft Corporation")
        entity_map = {"john_smith": node1, "microsoft": node2}

        relationship_data = {
            "source_id": "john_smith",
            "target_id": "microsoft",
            "relation_type": "works_for",
            "confidence": 0.9,
            "description": "Employment relationship"
        }

        edge = extractor._create_edge_from_relationship(sample_chunk, relationship_data, entity_map)

        assert edge.source_id == "john_smith"
        assert edge.target_id == "microsoft"
        assert edge.relation_type == "works_for"
        assert edge.confidence == 0.9
        assert edge.get_property("description") == "Employment relationship"

    @patch('knowledge_graphs.components.extractor.create_llm_client')
    def test_domain_schema_parsing(self, mock_create_client, sample_config):
        """Test parsing of domain schema content."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        extractor = LLMExtractor(sample_config)

        schema_content = """
        namespace TestDomain

        Person: EntityType
            properties:
                name: Text
                age: Integer

        Company: EntityType
            properties:
                name: Text
        """

        result = extractor._parse_domain_schema_content(schema_content)

        # Should update entity types
        assert "Person" in extractor.entity_types
        assert "Company" in extractor.entity_types

    @patch('knowledge_graphs.components.extractor.create_llm_client')
    @patch('knowledge_graphs.components.extractor.extract_json_from_response')
    def test_error_handling_invalid_json(self, mock_extract_json, mock_create_client,
                                       sample_config, sample_chunk):
        """Test error handling when LLM returns invalid JSON."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_extract_json.return_value = None  # Invalid JSON
        mock_client.simple_chat.return_value = "invalid json"

        # Test traditional extraction
        sample_config.config["use_template"] = False
        extractor = LLMExtractor(sample_config)

        subgraph = extractor._extract_from_chunk(sample_chunk)

        # Should return empty subgraph
        assert isinstance(subgraph, SubGraph)
        assert len(subgraph.nodes) == 0
        assert len(subgraph.edges) == 0


class TestGeminiVectorizer:
    """Test cases for GeminiVectorizer component."""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for GeminiVectorizer."""
        return ComponentConfig(
            type="gemini_vectorizer",
            name="test_vectorizer",
            enabled=True,
            config={
                "model": "gemini-embedding-001",
                "api_key": "test-google-api-key",
                "batch_size": 10,
                "embed_nodes": True,
                "embed_edges": False,
                "node_text_template": "{name} is a {type}. {description}",
                "edge_text_template": "{source} {relation} {target}"
            }
        )

    @pytest.fixture
    def sample_subgraph(self):
        """Sample subgraph for testing."""
        node1 = Node(
            id="john_smith",
            name="John Smith",
            node_type="Person",
            official_name="John Smith",
            properties={"description": "Software engineer"}
        )
        node2 = Node(
            id="microsoft",
            name="Microsoft",
            node_type="Organization",
            official_name="Microsoft Corporation"
        )
        edge = Edge(
            id="john_works_microsoft",
            source_id="john_smith",
            target_id="microsoft",
            relation_type="works_for",
            confidence=0.9
        )

        subgraph = SubGraph(
            nodes=[node1, node2],
            edges=[edge],
            source_chunk_id="chunk_1"
        )
        return subgraph

    @pytest.fixture
    def sample_pipeline_state(self, sample_subgraph):
        """Sample pipeline state with subgraphs."""
        return PipelineState(subgraphs=[sample_subgraph])

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_gemini_vectorizer_initialization(self, mock_client, sample_config):
        """Test GeminiVectorizer initialization."""
        vectorizer = GeminiVectorizer(sample_config)

        assert vectorizer.model == "gemini-embedding-001"
        assert vectorizer.batch_size == 10
        assert vectorizer.embed_nodes is True
        assert vectorizer.embed_edges is False
        assert vectorizer.name == "test_vectorizer"

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_node_text_creation(self, mock_client, sample_config):
        """Test node text creation using templates."""
        vectorizer = GeminiVectorizer(sample_config)

        node = Node(
            id="john_smith",
            name="John Smith",
            node_type="Person",
            official_name="John Smith",
            properties={"description": "Software engineer"}
        )

        text = vectorizer._create_node_text(node)
        expected = "John Smith is a Person. Software engineer"
        assert text == expected

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_edge_text_creation(self, mock_client, sample_config):
        """Test edge text creation using templates."""
        vectorizer = GeminiVectorizer(sample_config)

        node1 = Node(id="john_smith", name="John Smith", node_type="Person", official_name="John Smith")
        node2 = Node(id="microsoft", name="Microsoft", node_type="Organization", official_name="Microsoft Corporation")
        node_map = {"john_smith": node1, "microsoft": node2}

        edge = Edge(
            id="test_edge",
            source_id="john_smith",
            target_id="microsoft",
            relation_type="works_for"
        )

        text = vectorizer._create_edge_text(edge, node_map)
        expected = "John Smith works_for Microsoft"
        assert text == expected

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_generate_gemini_embeddings(self, mock_client_class, sample_config):
        """Test Gemini embedding generation."""
        # Setup mock client
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock embedding response
        mock_embedding_result = Mock()
        mock_embedding_result.embeddings = [
            Mock(values=[0.1, 0.2, 0.3]),
            Mock(values=[0.4, 0.5, 0.6])
        ]
        mock_client_instance.models.embed_content.return_value = mock_embedding_result

        vectorizer = GeminiVectorizer(sample_config)
        texts = ["John Smith is a Person.", "Microsoft is an Organization."]

        embeddings = vectorizer._generate_gemini_embeddings(texts)

        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]

        # Verify API call
        mock_client_instance.models.embed_content.assert_called_once()

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_vectorize_subgraph(self, mock_client_class, sample_config, sample_subgraph):
        """Test subgraph vectorization."""
        # Setup mock client
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock embedding response
        mock_embedding_result = Mock()
        mock_embedding_result.embeddings = [
            Mock(values=[0.1, 0.2, 0.3]),
            Mock(values=[0.4, 0.5, 0.6])
        ]
        mock_client_instance.models.embed_content.return_value = mock_embedding_result

        vectorizer = GeminiVectorizer(sample_config)
        vectorized_subgraph = vectorizer._vectorize_subgraph(sample_subgraph)

        # Check that embeddings were added to nodes
        assert len(vectorized_subgraph.nodes) == 2
        assert vectorized_subgraph.nodes[0].embeddings == [0.1, 0.2, 0.3]
        assert vectorized_subgraph.nodes[1].embeddings == [0.4, 0.5, 0.6]

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_process_pipeline_state(self, mock_client_class, sample_config, sample_pipeline_state):
        """Test processing pipeline state with subgraphs."""
        # Setup mock client
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock embedding response
        mock_embedding_result = Mock()
        mock_embedding_result.embeddings = [
            Mock(values=[0.1, 0.2, 0.3]),
            Mock(values=[0.4, 0.5, 0.6])
        ]
        mock_client_instance.models.embed_content.return_value = mock_embedding_result

        vectorizer = GeminiVectorizer(sample_config)
        updated_state = vectorizer.process(sample_pipeline_state)

        # Check that vectorized subgraphs were added to state
        assert "vectorized_subgraphs" in updated_state
        vectorized_subgraphs = updated_state["vectorized_subgraphs"]
        assert len(vectorized_subgraphs) == 1
        assert len(vectorized_subgraphs[0].nodes) == 2

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_embedding_generation_error_handling(self, mock_client_class, sample_config):
        """Test error handling during embedding generation."""
        # Setup mock client that raises exception
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.embed_content.side_effect = Exception("API Error")

        vectorizer = GeminiVectorizer(sample_config)
        texts = ["Test text"]

        embeddings = vectorizer._generate_gemini_embeddings(texts)

        # Should return zero embeddings as fallback
        assert len(embeddings) == 1
        assert embeddings[0] == [0.0] * 768  # Default dimension

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    def test_missing_api_key_error(self, mock_client_class, sample_config):
        """Test error when API key is missing."""
        # Remove api_key from config and environment
        sample_config.config.pop("api_key", None)

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Google AI API key not provided"):
                GeminiVectorizer(sample_config)

    @patch('knowledge_graphs.components.vectorizer.genai.Client')
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_text_truncation(self, mock_client_class, sample_config):
        """Test text truncation for long inputs."""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        # Mock embedding response
        mock_embedding_result = Mock()
        mock_embedding_result.embeddings = [Mock(values=[0.1, 0.2, 0.3])]
        mock_client_instance.models.embed_content.return_value = mock_embedding_result

        vectorizer = GeminiVectorizer(sample_config)

        # Create very long text
        long_text = "test " * 10000  # Much longer than max_tokens
        embeddings = vectorizer._generate_gemini_embeddings([long_text])

        # Should handle truncation gracefully
        assert len(embeddings) == 1
        assert embeddings[0] == [0.1, 0.2, 0.3]


if __name__ == "__main__":
    pytest.main([__file__])