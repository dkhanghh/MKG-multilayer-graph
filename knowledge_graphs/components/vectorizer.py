"""
Vectorizer components for KAG-LangGraph pipeline.

This module contains vectorizer implementations that create embeddings
for entities, relationships, and text content for semantic search.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import asyncio

from .base import Vectorizer
from ..models.graph import SubGraph, Node, Edge
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component

logger = logging.getLogger(__name__)

# Optional imports for embedding models
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@register_component(
    "vectorizer",
    "embedding_vectorizer",
    description="Creates embeddings using sentence transformers",
    config_schema={
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the sentence transformer model",
                "default": "all-MiniLM-L6-v2"
            },
            "batch_size": {
                "type": "integer",
                "description": "Batch size for embedding generation",
                "default": 32
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum sequence length for embeddings",
                "default": 512
            },
            "normalize_embeddings": {
                "type": "boolean",
                "description": "Whether to normalize embeddings to unit length",
                "default": True
            },
            "embed_nodes": {
                "type": "boolean",
                "description": "Whether to create embeddings for nodes",
                "default": True
            },
            "embed_edges": {
                "type": "boolean", 
                "description": "Whether to create embeddings for edges",
                "default": False
            },
            "node_text_template": {
                "type": "string",
                "description": "Template for node text: {name}, {type}, {description}",
                "default": "{name} is a {type}. {description}"
            },
            "edge_text_template": {
                "type": "string",
                "description": "Template for edge text: {source}, {relation}, {target}",
                "default": "{source} {relation} {target}"
            }
        }
    }
)
class EmbeddingVectorizer(Vectorizer):
    """
    Vectorizer that creates embeddings using sentence transformers.
    
    Generates embeddings for entity names, descriptions, and relationships
    to enable semantic search and similarity matching.
    """
    
    def __init__(self, config):
        """Initialize embedding vectorizer."""
        super().__init__(config)
        
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        # Load embedding model
        model_name = self.get_config_value("model_name", "all-MiniLM-L6-v2")
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded sentence transformer model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
        
        # Configuration
        self.batch_size = self.get_config_value("batch_size", 32)
        self.max_length = self.get_config_value("max_length", 512)
        self.normalize_embeddings = self.get_config_value("normalize_embeddings", True)
        self.embed_nodes = self.get_config_value("embed_nodes", True)
        self.embed_edges = self.get_config_value("embed_edges", False)
        
        # Text templates
        self.node_text_template = self.get_config_value(
            "node_text_template", 
            "{name} is a {type}. {description}"
        )
        self.edge_text_template = self.get_config_value(
            "edge_text_template",
            "{source} {relation} {target}"
        )
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Create embeddings for entities and relationships.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with vectorized subgraphs
        """
        subgraphs = state.get("subgraphs", [])
        if not subgraphs:
            raise ValueError("No subgraphs provided in pipeline state")
        
        vectorized_subgraphs = []
        
        for subgraph in subgraphs:
            try:
                vectorized_subgraph = self._vectorize_subgraph(subgraph)
                vectorized_subgraphs.append(vectorized_subgraph)
            except Exception as e:
                logger.error(f"Error vectorizing subgraph: {e}")
                vectorized_subgraphs.append(subgraph)  # Keep original if vectorization fails
        
        total_nodes = sum(len(sg.nodes) for sg in vectorized_subgraphs)
        total_edges = sum(len(sg.edges) for sg in vectorized_subgraphs)
        
        logger.info(f"Vectorized {len(vectorized_subgraphs)} subgraphs "
                   f"({total_nodes} nodes, {total_edges} edges)")
        
        # Update state
        updated_state = state.copy()
        updated_state["vectorized_subgraphs"] = vectorized_subgraphs
        
        return updated_state
    
    def _vectorize_subgraph(self, subgraph: SubGraph) -> SubGraph:
        """
        Create embeddings for all nodes and edges in a subgraph.
        
        Args:
            subgraph: SubGraph to vectorize
            
        Returns:
            SubGraph with embeddings added
        """
        # Create a copy to avoid modifying original
        vectorized_subgraph = SubGraph(
            nodes=subgraph.nodes.copy(),
            edges=subgraph.edges.copy(),
            source_chunk_id=subgraph.source_chunk_id,
            extraction_metadata=subgraph.extraction_metadata.copy()
        )
        
        # Vectorize nodes
        if self.embed_nodes and vectorized_subgraph.nodes:
            self._vectorize_nodes(vectorized_subgraph.nodes)
        
        # Vectorize edges
        if self.embed_edges and vectorized_subgraph.edges:
            self._vectorize_edges(vectorized_subgraph.edges, vectorized_subgraph.nodes)
        
        return vectorized_subgraph
    
    def _vectorize_nodes(self, nodes: List[Node]) -> None:
        """
        Create embeddings for a list of nodes.
        
        Args:
            nodes: List of nodes to vectorize
        """
        if not nodes:
            return
        
        # Prepare texts for embedding
        texts = []
        for node in nodes:
            text = self._create_node_text(node)
            texts.append(text)
        
        # Generate embeddings in batches
        embeddings = self._generate_embeddings(texts)
        
        # Add embeddings to nodes
        for node, embedding in zip(nodes, embeddings):
            node.embeddings = embedding.tolist()
    
    def _vectorize_edges(self, edges: List[Edge], nodes: List[Node]) -> None:
        """
        Create embeddings for a list of edges.
        
        Args:
            edges: List of edges to vectorize
            nodes: List of nodes for context
        """
        if not edges:
            return
        
        # Create node lookup
        node_map = {node.id: node for node in nodes}
        
        # Prepare texts for embedding
        texts = []
        for edge in edges:
            text = self._create_edge_text(edge, node_map)
            texts.append(text)
        
        # Generate embeddings in batches
        embeddings = self._generate_embeddings(texts)
        
        # Add embeddings to edges
        for edge, embedding in zip(edges, embeddings):
            edge.properties = edge.properties or {}
            edge.properties["embeddings"] = embedding.tolist()
    
    def _create_node_text(self, node: Node) -> str:
        """
        Create text representation of a node for embedding.
        
        Args:
            node: Node to create text for
            
        Returns:
            Text representation
        """
        # Get node information
        name = node.name or ""
        node_type = node.node_type or "Unknown"
        description = node.get_property("description", "")
        
        try:
            # Use template to create text
            text = self.node_text_template.format(
                name=name,
                type=node_type,
                description=description
            )
        except KeyError:
            # Fallback if template has issues
            text = f"{name} ({node_type})"
            if description:
                text += f" - {description}"
        
        return text.strip()
    
    def _create_edge_text(self, edge: Edge, node_map: Dict[str, Node]) -> str:
        """
        Create text representation of an edge for embedding.
        
        Args:
            edge: Edge to create text for
            node_map: Map of node IDs to nodes
            
        Returns:
            Text representation
        """
        # Get source and target names
        source_node = node_map.get(edge.source_id)
        target_node = node_map.get(edge.target_id)
        
        source_name = source_node.name if source_node else edge.source_id
        target_name = target_node.name if target_node else edge.target_id
        relation_type = edge.relation_type
        
        try:
            # Use template to create text
            text = self.edge_text_template.format(
                source=source_name,
                relation=relation_type,
                target=target_name
            )
        except KeyError:
            # Fallback if template has issues
            text = f"{source_name} {relation_type} {target_name}"
        
        return text.strip()
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Array of embeddings
        """
        if not texts:
            return np.array([])
        
        # Truncate texts to max length if needed
        truncated_texts = []
        for text in texts:
            if len(text) > self.max_length:
                # Simple truncation - could be more sophisticated
                text = text[:self.max_length]
            truncated_texts.append(text)
        
        # Generate embeddings
        embeddings = self.model.encode(
            truncated_texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False
        )
        
        return embeddings


@register_component(
    "vectorizer", 
    "openai_vectorizer",
    description="Creates embeddings using OpenAI's embedding API",
    config_schema={
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "description": "OpenAI embedding model to use",
                "default": "text-embedding-ada-002"
            },
            "api_key": {
                "type": "string",
                "description": "OpenAI API key"
            },
            "batch_size": {
                "type": "integer",
                "description": "Batch size for API requests",
                "default": 20
            },
            "max_tokens": {
                "type": "integer", 
                "description": "Maximum tokens per text",
                "default": 8000
            },
            "embed_nodes": {
                "type": "boolean",
                "description": "Whether to create embeddings for nodes",
                "default": True
            },
            "embed_edges": {
                "type": "boolean",
                "description": "Whether to create embeddings for edges", 
                "default": False
            }
        }
    }
)
class OpenAIVectorizer(Vectorizer):
    """
    Vectorizer that uses OpenAI's embedding API.
    
    Provides high-quality embeddings using OpenAI's models,
    useful when you want state-of-the-art embedding quality.
    """
    
    def __init__(self, config):
        """Initialize OpenAI vectorizer."""
        super().__init__(config)
        
        if not HAS_OPENAI:
            raise ImportError("openai not installed. Install with: pip install openai")
        
        # Configuration
        self.model = self.get_config_value("model", "text-embedding-ada-002")
        api_key = self.get_config_value("api_key")
        self.batch_size = self.get_config_value("batch_size", 20)
        self.max_tokens = self.get_config_value("max_tokens", 8000)
        self.embed_nodes = self.get_config_value("embed_nodes", True)
        self.embed_edges = self.get_config_value("embed_edges", False)
        
        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=api_key)
        
        logger.info(f"Initialized OpenAI vectorizer with model: {self.model}")
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Create embeddings using OpenAI API.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with vectorized subgraphs
        """
        subgraphs = state.get("subgraphs", [])
        if not subgraphs:
            raise ValueError("No subgraphs provided in pipeline state")
        
        vectorized_subgraphs = []
        
        for subgraph in subgraphs:
            try:
                vectorized_subgraph = self._vectorize_subgraph(subgraph)
                vectorized_subgraphs.append(vectorized_subgraph)
            except Exception as e:
                logger.error(f"Error vectorizing subgraph with OpenAI: {e}")
                vectorized_subgraphs.append(subgraph)
        
        logger.info(f"Vectorized {len(vectorized_subgraphs)} subgraphs using OpenAI")
        
        # Update state
        updated_state = state.copy()
        updated_state["vectorized_subgraphs"] = vectorized_subgraphs
        
        return updated_state
    
    def _vectorize_subgraph(self, subgraph: SubGraph) -> SubGraph:
        """
        Create embeddings for subgraph using OpenAI.
        
        Args:
            subgraph: SubGraph to vectorize
            
        Returns:
            Vectorized subgraph
        """
        # Create copy
        vectorized_subgraph = SubGraph(
            nodes=subgraph.nodes.copy(),
            edges=subgraph.edges.copy(),
            source_chunk_id=subgraph.source_chunk_id,
            extraction_metadata=subgraph.extraction_metadata.copy()
        )
        
        # Collect all texts that need embedding
        texts_to_embed = []
        node_indices = []
        edge_indices = []
        
        # Add node texts
        if self.embed_nodes:
            for i, node in enumerate(vectorized_subgraph.nodes):
                text = self._create_node_text(node)
                texts_to_embed.append(text)
                node_indices.append(i)
        
        # Add edge texts
        if self.embed_edges:
            node_map = {node.id: node for node in vectorized_subgraph.nodes}
            for i, edge in enumerate(vectorized_subgraph.edges):
                text = self._create_edge_text(edge, node_map)
                texts_to_embed.append(text)
                edge_indices.append(i)
        
        # Generate embeddings
        if texts_to_embed:
            embeddings = self._generate_openai_embeddings(texts_to_embed)
            
            # Assign embeddings back to nodes and edges
            embedding_idx = 0
            
            # Assign node embeddings
            if self.embed_nodes:
                for node_idx in node_indices:
                    vectorized_subgraph.nodes[node_idx].embeddings = embeddings[embedding_idx]
                    embedding_idx += 1
            
            # Assign edge embeddings  
            if self.embed_edges:
                for edge_idx in edge_indices:
                    edge = vectorized_subgraph.edges[edge_idx]
                    edge.properties = edge.properties or {}
                    edge.properties["embeddings"] = embeddings[embedding_idx]
                    embedding_idx += 1
        
        return vectorized_subgraph
    
    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//self.batch_size}: {e}")
                # Add zero embeddings as fallback
                embedding_dim = 1536 if "ada-002" in self.model else 1024
                zero_embedding = [0.0] * embedding_dim
                all_embeddings.extend([zero_embedding] * len(batch))
        
        return all_embeddings
    
    def _create_node_text(self, node: Node) -> str:
        """Create text for node embedding."""
        name = node.name or ""
        node_type = node.node_type or ""
        description = node.get_property("description", "")
        
        parts = [name]
        if node_type:
            parts.append(f"({node_type})")
        if description:
            parts.append(f"- {description}")
        
        return " ".join(parts)
    
    def _create_edge_text(self, edge: Edge, node_map: Dict[str, Node]) -> str:
        """Create text for edge embedding."""
        source_node = node_map.get(edge.source_id)
        target_node = node_map.get(edge.target_id)
        
        source_name = source_node.name if source_node else edge.source_id
        target_name = target_node.name if target_node else edge.target_id
        
        return f"{source_name} {edge.relation_type} {target_name}"


@register_component(
    "vectorizer",
    "no_op_vectorizer", 
    description="Pass-through vectorizer that does not add embeddings",
    config_schema={
        "type": "object",
        "properties": {}
    }
)
class NoOpVectorizer(Vectorizer):
    """
    No-operation vectorizer that passes subgraphs through unchanged.
    
    Useful when you don't need embeddings or want to disable
    vectorization temporarily.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Pass subgraphs through unchanged.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Pipeline state with subgraphs copied to vectorized_subgraphs
        """
        subgraphs = state.get("subgraphs", [])
        
        logger.info(f"No-op vectorizer: passing through {len(subgraphs)} subgraphs unchanged")
        
        # Update state
        updated_state = state.copy()
        updated_state["vectorized_subgraphs"] = subgraphs.copy()
        
        return updated_state