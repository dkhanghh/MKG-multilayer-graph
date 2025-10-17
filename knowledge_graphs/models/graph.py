"""
Knowledge graph models for the KAG-LangGraph pipeline.

This module defines the Node, Edge, and SubGraph classes for representing
structured knowledge extracted from documents.
"""

from typing import Dict, Any, List, Optional, Set, Union
from pydantic import BaseModel, Field, ConfigDict
import json
import uuid


class Node(BaseModel):
    """
    Represents a node (entity) in a knowledge graph.
    
    Nodes represent entities like people, organizations, locations, concepts, etc.
    """
    
    id: str = Field(..., description="Unique identifier for the node")
    name: str = Field(..., description="Display name of the entity")
    label: str = Field(..., description="The type/category of the node - defines what kind of entity this node represents (e.g., 'Person', 'Company', 'Location')")

    # Entity properties
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties of the entity")
    official_name: str = Field(..., description="Official/canonical name for the entity")
    aliases: List[str] = Field(default_factory=list, description="Alternative names for the entity")

    # Context and source information
    source_chunks: List[str] = Field(default_factory=list, description="IDs of chunks where this entity was mentioned")
    confidence: Optional[float] = Field(None, description="Confidence score for entity extraction")

    # Embeddings and vectors
    embeddings: Optional[List[float]] = Field(None, description="Entity embeddings for full node text")

    # Processing metadata
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from extraction process")
    
    def add_property(self, key: str, value: Any) -> None:
        """
        Add a property to the node.
        
        Args:
            key: Property name
            value: Property value
        """
        self.properties[key] = value
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value.
        
        Args:
            key: Property name
            default: Default value if property doesn't exist
            
        Returns:
            Property value or default
        """
        return self.properties.get(key, default)
    
    def add_alias(self, alias: str) -> None:
        """
        Add an alternative name for this entity.
        
        Args:
            alias: Alternative name
        """
        if alias and alias not in self.aliases:
            self.aliases.append(alias)
    
    def add_source_chunk(self, chunk_id: str) -> None:
        """
        Add a source chunk ID.
        
        Args:
            chunk_id: ID of chunk where this entity was found
        """
        if chunk_id and chunk_id not in self.source_chunks:
            self.source_chunks.append(chunk_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "properties": self.properties,
            "official_name": self.official_name,
            "aliases": self.aliases,
            "source_chunks": self.source_chunks,
            "confidence": self.confidence,
            "embeddings": self.embeddings,
            "extraction_metadata": self.extraction_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        """Create node from dictionary representation."""
        return cls(**data)
    
    def __hash__(self) -> int:
        """Hash function for node (based on ID)."""
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """Equality comparison (based on ID)."""
        return isinstance(other, Node) and self.id == other.id
    
    def __str__(self) -> str:
        return f"Node(id='{self.id}', name='{self.name}', label='{self.label}')"

    def __repr__(self) -> str:
        return f"Node(id='{self.id}', name='{self.name}', label='{self.label}', properties={len(self.properties)})"

    model_config = ConfigDict(populate_by_name=True)


class Edge(BaseModel):
    """
    Represents an edge (relationship) in a knowledge graph.

    Edges connect two nodes and represent relationships between entities.

    SPG (Semantic Property Graph) Support:
    - Edges can have rich properties (edgeProperties) as defined in schema
    - Examples:
      * REPORTED_FINANCIALS: {period, revenue, profit, expenses, ...}
      * OWNS: {ownershipPercent, acquiredDate, isSubsidiary}
      * EMPLOYS: {hireDate, salary, isCurrentEmployee}
    - All edge properties are stored in the 'properties' dict
    """

    id: str = Field(..., description="Unique identifier for the edge")
    source_id: str = Field(..., description="ID of the source node")
    target_id: str = Field(..., description="ID of the target node")
    relation_type: str = Field(..., description="Type of relationship (e.g., 'REPORTED_FINANCIALS', 'OWNS', 'EMPLOYS')")

    # Relationship properties (SPG edge properties)
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Edge properties - can contain rich semantic data in SPG model (e.g., financial metrics, temporal data, contextual info)"
    )

    # Direction and weight
    directed: bool = Field(True, description="Whether the relationship is directed")
    weight: Optional[float] = Field(None, description="Weight or strength of the relationship")

    # Context and source information
    source_chunks: List[str] = Field(default_factory=list, description="IDs of chunks where this relationship was mentioned")
    confidence: Optional[float] = Field(None, description="Confidence score for relationship extraction")

    # Processing metadata
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from extraction process")
    
    def add_property(self, key: str, value: Any) -> None:
        """
        Add a property to the edge (SPG edge property).

        Args:
            key: Property name (e.g., 'revenue', 'period', 'ownershipPercent')
            value: Property value
        """
        self.properties[key] = value

    def add_properties(self, properties: Dict[str, Any]) -> None:
        """
        Add multiple properties to the edge at once (SPG edge properties).

        Args:
            properties: Dictionary of edge properties
        """
        self.properties.update(properties)

    def get_property(self, key: str, default: Any = None) -> Any:
        """
        Get a property value.

        Args:
            key: Property name
            default: Default value if property doesn't exist

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def has_spg_properties(self) -> bool:
        """
        Check if this edge has SPG-style rich properties.

        Returns:
            True if edge has properties beyond basic metadata
        """
        # Filter out standard metadata properties
        metadata_keys = {"relationship_category", "is_taxonomy", "description"}
        spg_properties = {k: v for k, v in self.properties.items() if k not in metadata_keys}
        return len(spg_properties) > 0
    
    def add_source_chunk(self, chunk_id: str) -> None:
        """
        Add a source chunk ID.
        
        Args:
            chunk_id: ID of chunk where this relationship was found
        """
        if chunk_id and chunk_id not in self.source_chunks:
            self.source_chunks.append(chunk_id)
    
    def reverse(self) -> "Edge":
        """
        Create a reversed version of this edge.
        
        Returns:
            New edge with source and target swapped
        """
        return Edge(
            id=f"{self.id}_reversed",
            source_id=self.target_id,
            target_id=self.source_id,
            relation_type=f"reverse_{self.relation_type}",
            properties=self.properties.copy(),
            directed=self.directed,
            weight=self.weight,
            source_chunks=self.source_chunks.copy(),
            confidence=self.confidence,
            extraction_metadata=self.extraction_metadata.copy(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary representation."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "directed": self.directed,
            "weight": self.weight,
            "source_chunks": self.source_chunks,
            "confidence": self.confidence,
            "extraction_metadata": self.extraction_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        """Create edge from dictionary representation."""
        return cls(**data)
    
    def __hash__(self) -> int:
        """Hash function for edge (based on ID)."""
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """Equality comparison (based on ID)."""
        return isinstance(other, Edge) and self.id == other.id
    
    def __str__(self) -> str:
        direction = "->" if self.directed else "--"
        return f"Edge({self.source_id} {direction}[{self.relation_type}] {self.target_id})"
    
    def __repr__(self) -> str:
        return f"Edge(id='{self.id}', {self.source_id}-[{self.relation_type}]->{self.target_id})"


class SubGraph(BaseModel):
    """
    Represents a subgraph containing nodes and edges.
    
    SubGraphs are produced by extractor components and can be merged
    to form larger knowledge graphs.
    """
    
    nodes: List[Node] = Field(default_factory=list, description="List of nodes in the subgraph")
    edges: List[Edge] = Field(default_factory=list, description="List of edges in the subgraph")
    
    # Metadata
    source_chunk_id: Optional[str] = Field(None, description="ID of the chunk this subgraph was extracted from")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from extraction process")
    
    def add_node(self, node: Node) -> None:
        """
        Add a node to the subgraph.
        
        Args:
            node: Node to add
        """
        if node not in self.nodes:
            self.nodes.append(node)
    
    def add_edge(self, edge: Edge) -> None:
        """
        Add an edge to the subgraph.
        
        Args:
            edge: Edge to add
        """
        if edge not in self.edges:
            self.edges.append(edge)
    
    def get_node_by_id(self, node_id: str) -> Optional[Node]:
        """
        Get a node by its ID.
        
        Args:
            node_id: Node ID to search for
            
        Returns:
            Node if found, None otherwise
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edge_by_id(self, edge_id: str) -> Optional[Edge]:
        """
        Get an edge by its ID.
        
        Args:
            edge_id: Edge ID to search for
            
        Returns:
            Edge if found, None otherwise
        """
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None
    
    def get_node_ids(self) -> Set[str]:
        """
        Get all node IDs in the subgraph.
        
        Returns:
            Set of node IDs
        """
        return {node.id for node in self.nodes}
    
    def get_edges_for_node(self, node_id: str) -> List[Edge]:
        """
        Get all edges connected to a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            List of edges connected to the node
        """
        return [edge for edge in self.edges 
                if edge.source_id == node_id or edge.target_id == node_id]
    
    def merge(self, other: "SubGraph") -> "SubGraph":
        """
        Merge this subgraph with another subgraph.
        
        Args:
            other: SubGraph to merge with
            
        Returns:
            New merged SubGraph
        """
        merged_nodes = list(self.nodes)
        merged_edges = list(self.edges)
        
        # Add nodes from other subgraph (avoid duplicates)
        existing_node_ids = self.get_node_ids()
        for node in other.nodes:
            if node.id not in existing_node_ids:
                merged_nodes.append(node)
        
        # Add edges from other subgraph (avoid duplicates)
        existing_edge_ids = {edge.id for edge in self.edges}
        for edge in other.edges:
            if edge.id not in existing_edge_ids:
                merged_edges.append(edge)
        
        # Merge metadata
        merged_metadata = self.extraction_metadata.copy()
        merged_metadata.update(other.extraction_metadata)
        
        return SubGraph(
            nodes=merged_nodes,
            edges=merged_edges,
            extraction_metadata=merged_metadata,
        )
    
    def is_empty(self) -> bool:
        """
        Check if the subgraph is empty.
        
        Returns:
            True if no nodes or edges
        """
        return len(self.nodes) == 0 and len(self.edges) == 0
    
    def validate(self) -> List[str]:
        """
        Validate the subgraph structure.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        node_ids = self.get_node_ids()
        
        # Check that all edges reference valid nodes
        for edge in self.edges:
            if edge.source_id not in node_ids:
                errors.append(f"Edge {edge.id} references non-existent source node {edge.source_id}")
            if edge.target_id not in node_ids:
                errors.append(f"Edge {edge.id} references non-existent target node {edge.target_id}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subgraph to dictionary representation."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "source_chunk_id": self.source_chunk_id,
            "extraction_metadata": self.extraction_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubGraph":
        """Create subgraph from dictionary representation."""
        nodes = [Node.from_dict(node_data) for node_data in data.get("nodes", [])]
        edges = [Edge.from_dict(edge_data) for edge_data in data.get("edges", [])]
        
        return cls(
            nodes=nodes,
            edges=edges,
            source_chunk_id=data.get("source_chunk_id"),
            extraction_metadata=data.get("extraction_metadata", {}),
        )
    
    def __len__(self) -> int:
        """Return total number of nodes and edges."""
        return len(self.nodes) + len(self.edges)
    
    def __str__(self) -> str:
        return f"SubGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
    
    def __repr__(self) -> str:
        return f"SubGraph(nodes={len(self.nodes)}, edges={len(self.edges)}, source_chunk='{self.source_chunk_id}')"