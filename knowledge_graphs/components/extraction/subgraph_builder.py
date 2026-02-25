"""SubGraph assembly logic for extraction results."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from ...models.chunk import Chunk
from ...models.graph import Edge, Node, SubGraph

logger = logging.getLogger(__name__)


class SubGraphBuilder:
    """Builds ``SubGraph`` instances from raw extraction dicts.

    Parameters:
        extraction_metadata: Base metadata attached to every subgraph produced
            by this builder (e.g. provider name, model, extraction method).
    """

    def __init__(self, extraction_metadata: Dict[str, Any]) -> None:
        self.extraction_metadata = extraction_metadata

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_from_extraction(
        self,
        chunk: Chunk,
        entities_data: Dict[str, Any],
        relationships_data: Dict[str, Any],
    ) -> SubGraph:
        """Create a ``SubGraph`` from entity and relationship dicts.

        Args:
            chunk: Source chunk the data was extracted from.
            entities_data: Dict with an ``"entities"`` key mapping to a list of
                entity dicts.
            relationships_data: Dict with a ``"relationships"`` key mapping to a
                list of relationship dicts.

        Returns:
            Populated ``SubGraph``.
        """
        subgraph = SubGraph(source_chunk_id=chunk.id)

        # --- nodes ---
        entity_map: Dict[str, Node] = {}
        entities = entities_data.get("entities", [])
        for entity_data in entities:
            try:
                node = self.create_node_from_entity(chunk, entity_data)
                subgraph.add_node(node)
                entity_id = entity_data.get("id", "")
                entity_map[entity_id] = node
                logger.debug(
                    "Added entity to map: id='%s', name='%s'",
                    entity_id,
                    entity_data.get("name"),
                )
            except Exception as e:
                logger.warning("Error creating node from entity: %s", e)
                continue

        logger.debug(
            "Entity map has %d entities: %s",
            len(entity_map),
            list(entity_map.keys()),
        )

        # --- edges ---
        relationships = relationships_data.get("relationships", [])
        for relationship_data in relationships:
            try:
                edge = self.create_edge_from_relationship(
                    chunk, relationship_data, entity_map
                )
                if edge:
                    subgraph.add_edge(edge)
            except Exception as e:
                logger.warning("Error creating edge from relationship: %s", e)
                continue

        # --- metadata ---
        subgraph.extraction_metadata = {
            **self.extraction_metadata,
            "entities_extracted": len(entities),
            "relationships_extracted": len(relationships),
        }

        return subgraph

    # ------------------------------------------------------------------
    # Node / Edge factories
    # ------------------------------------------------------------------

    def create_node_from_entity(
        self, chunk: Chunk, entity_data: Dict[str, Any]
    ) -> Node:
        """Create a ``Node`` from a single entity dict.

        Args:
            chunk: Source chunk.
            entity_data: Entity dictionary produced by the LLM.

        Returns:
            A ``Node`` instance.

        Raises:
            ValueError: If the entity has no ``name``.
        """
        entity_id = entity_data.get("id", str(uuid.uuid4()))
        name = entity_data.get("name", "")
        label = entity_data.get("category", "Unknown")
        official_name = entity_data.get("official_name", "")
        description = entity_data.get("description", "")
        properties = entity_data.get("properties", "")

        if not name:
            raise ValueError("Entity name is required")

        node = Node(
            id=entity_id,
            name=name,
            label=label,
            official_name=official_name if official_name else name,
        )

        if description:
            node.add_property("description", description)

        if properties:
            node.add_property("properties", properties)

        node.add_source_chunk(chunk.id)
        if chunk.page_number:
            node.add_property("page_number", chunk.page_number)

        return node

    def create_edge_from_relationship(
        self,
        chunk: Chunk,
        relationship_data: Dict[str, Any],
        entity_map: Dict[str, Node],
    ) -> Optional[Edge]:
        """Create an ``Edge`` from a relationship dict.

        Handles taxonomy (``isA``), hierarchy (``belongTo``), schema-defined,
        and on-the-fly discovered relationships.

        Args:
            chunk: Source chunk.
            relationship_data: Relationship dictionary produced by the LLM.
            entity_map: Mapping of entity IDs to ``Node`` objects so that we can
                validate both endpoints exist.

        Returns:
            An ``Edge`` instance or ``None`` when the relationship is invalid.
        """
        source_id = relationship_data.get("source_id", "")
        target_id = relationship_data.get("target_id", "")
        relation_type = relationship_data.get("relation_type", "")
        description = relationship_data.get("description", "")
        confidence = relationship_data.get("confidence", 0.8)

        if not all([source_id, target_id, relation_type]):
            logger.warning("Missing required relationship fields")
            return None

        if source_id not in entity_map or target_id not in entity_map:
            logger.warning(
                "Relationship references unknown entities: %s -> %s",
                source_id,
                target_id,
            )
            return None

        edge_id = f"{source_id}_{relation_type}_{target_id}"

        edge = Edge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
        )

        # SPG edge properties
        edge_properties = relationship_data.get("properties", {})
        if edge_properties and isinstance(edge_properties, dict):
            edge.add_properties(edge_properties)
            logger.debug(
                "Added %d SPG edge properties to %s",
                len(edge_properties),
                relation_type,
            )

        # Relationship category
        if relation_type == "isA":
            edge.add_property("relationship_category", "taxonomy")
            edge.add_property("is_taxonomy", True)
        elif relation_type == "belongTo":
            edge.add_property("relationship_category", "concept_hierarchy")
            edge.add_property("is_hierarchy", True)
        elif confidence >= 0.7:
            edge.add_property("relationship_category", "schema_defined")
        else:
            edge.add_property("relationship_category", "discovered")

        if description:
            edge.add_property("description", description)

        edge.add_source_chunk(chunk.id)

        return edge

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge_subgraphs(self, subgraphs: List[SubGraph]) -> List[SubGraph]:
        """Merge a list of subgraphs, deduplicating nodes and edges.

        Nodes are deduplicated by ``label:lowercased_name``.  Edges are
        deduplicated by ``source_id:relation_type:target_id``.  Source chunks
        from duplicates are merged into the surviving instance.

        Args:
            subgraphs: Subgraphs to merge.

        Returns:
            A list containing at most one merged ``SubGraph``.
        """
        if len(subgraphs) <= 1:
            return subgraphs

        merged_nodes: Dict[str, Node] = {}
        merged_edges: Dict[str, Edge] = {}

        for subgraph in subgraphs:
            for node in subgraph.nodes:
                node_key = f"{node.label}:{node.name.lower()}"
                if node_key in merged_nodes:
                    existing_node = merged_nodes[node_key]
                    for chunk_id in node.source_chunks:
                        existing_node.add_source_chunk(chunk_id)
                else:
                    merged_nodes[node_key] = node

            for edge in subgraph.edges:
                edge_key = f"{edge.source_id}:{edge.relation_type}:{edge.target_id}"
                if edge_key in merged_edges:
                    existing_edge = merged_edges[edge_key]
                    for chunk_id in edge.source_chunks:
                        existing_edge.add_source_chunk(chunk_id)
                else:
                    merged_edges[edge_key] = edge

        if merged_nodes or merged_edges:
            final_subgraph = SubGraph(
                nodes=list(merged_nodes.values()),
                edges=list(merged_edges.values()),
            )
            return [final_subgraph]

        return []
