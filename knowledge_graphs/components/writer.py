"""
Writer components for KAG-LangGraph pipeline.

This module contains writer implementations that output knowledge graphs
in various formats including JSON, CSV, GraphML, and database storage.
"""

import json
import csv
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import datetime

from .base import Writer
from ..models.graph import SubGraph, Node, Edge
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component
from ..utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Optional imports for database connectivity
try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError, TransientError, SessionExpired

    NEO4J_FATAL_ERRORS = (ServiceUnavailable, AuthError)
    NEO4J_TRANSIENT_ERRORS = (ServiceUnavailable, TransientError, SessionExpired)
    HAS_NEO4J = True
except ImportError:
    NEO4J_FATAL_ERRORS = ()
    NEO4J_TRANSIENT_ERRORS = ()
    HAS_NEO4J = False


@register_component(
    "writer",
    "json_writer",
    description="Writes knowledge graph to JSON format",
    config_schema={
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Path to output JSON file",
                "default": "./output/knowledge_graph.json"
            },
            "pretty_print": {
                "type": "boolean",
                "description": "Whether to format JSON with indentation",
                "default": True
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Whether to include extraction metadata",
                "default": True
            },
            "separate_files": {
                "type": "boolean",
                "description": "Whether to save nodes and edges in separate files",
                "default": False
            }
        }
    }
)
class JSONWriter(Writer):
    """
    Writer that outputs knowledge graphs in JSON format.
    
    Saves nodes and edges as structured JSON data, optionally
    with pretty formatting and metadata inclusion.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Write knowledge graph to JSON format.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with output path
        """
        subgraphs = state.get("vectorized_subgraphs", state.get("subgraphs", []))
        if not subgraphs:
            logger.warning("No subgraphs to write")
            updated_state = state.copy()
            updated_state["output_path"] = ""
            return updated_state
        
        # Configuration
        output_path = self.get_config_value("output_path", "./output/knowledge_graph.json")
        pretty_print = self.get_config_value("pretty_print", True)
        include_metadata = self.get_config_value("include_metadata", True)
        separate_files = self.get_config_value("separate_files", False)
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Merge all subgraphs
        merged_graph = self._merge_subgraphs(subgraphs)
        
        if separate_files:
            output_paths = self._write_separate_files(
                merged_graph, output_path, pretty_print, include_metadata
            )
            final_output_path = output_paths[0]  # Return first file path
        else:
            final_output_path = self._write_combined_file(
                merged_graph, output_path, pretty_print, include_metadata
            )
        
        logger.info(f"Wrote knowledge graph to {final_output_path}")
        
        # Update state
        updated_state = state.copy()
        updated_state["output_path"] = final_output_path
        
        return updated_state
    
    def _merge_subgraphs(self, subgraphs: List[SubGraph]) -> SubGraph:
        """
        Merge multiple subgraphs into one.
        
        Args:
            subgraphs: List of subgraphs to merge
            
        Returns:
            Merged subgraph
        """
        if not subgraphs:
            return SubGraph()
        
        if len(subgraphs) == 1:
            return subgraphs[0]
        
        # Start with first subgraph
        merged = subgraphs[0]
        
        # Merge remaining subgraphs
        for subgraph in subgraphs[1:]:
            merged = merged.merge(subgraph)
        
        return merged
    
    def _write_combined_file(
        self,
        graph: SubGraph,
        output_path: str,
        pretty_print: bool,
        include_metadata: bool
    ) -> str:
        """
        Write combined graph data to single JSON file.
        
        Args:
            graph: SubGraph to write
            output_path: Path to output file
            pretty_print: Whether to format JSON
            include_metadata: Whether to include metadata
            
        Returns:
            Path to written file
        """
        # Convert to dictionary
        graph_data = {
            "nodes": [node.to_dict() for node in graph.nodes],
            "edges": [edge.to_dict() for edge in graph.edges]
        }
        
        # Add metadata if requested
        if include_metadata:
            graph_data["metadata"] = {
                "created_at": datetime.datetime.utcnow().isoformat(),
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
                "source_chunk_id": graph.source_chunk_id,
                "extraction_metadata": graph.extraction_metadata
            }
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty_print:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(graph_data, f, ensure_ascii=False)
        
        return output_path
    
    def _write_separate_files(
        self,
        graph: SubGraph,
        base_path: str,
        pretty_print: bool,
        include_metadata: bool
    ) -> List[str]:
        """
        Write nodes and edges to separate JSON files.
        
        Args:
            graph: SubGraph to write
            base_path: Base path for output files
            pretty_print: Whether to format JSON
            include_metadata: Whether to include metadata
            
        Returns:
            List of written file paths
        """
        base_path_obj = Path(base_path)
        base_name = base_path_obj.stem
        base_dir = base_path_obj.parent
        
        # Create output file paths
        nodes_path = base_dir / f"{base_name}_nodes.json"
        edges_path = base_dir / f"{base_name}_edges.json"
        
        output_paths = []
        
        # Write nodes file
        nodes_data = {"nodes": [node.to_dict() for node in graph.nodes]}
        if include_metadata:
            nodes_data["metadata"] = {
                "created_at": datetime.datetime.utcnow().isoformat(),
                "node_count": len(graph.nodes)
            }
        
        with open(nodes_path, 'w', encoding='utf-8') as f:
            if pretty_print:
                json.dump(nodes_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(nodes_data, f, ensure_ascii=False)
        
        output_paths.append(str(nodes_path))
        
        # Write edges file
        edges_data = {"edges": [edge.to_dict() for edge in graph.edges]}
        if include_metadata:
            edges_data["metadata"] = {
                "created_at": datetime.datetime.utcnow().isoformat(),
                "edge_count": len(graph.edges)
            }
        
        with open(edges_path, 'w', encoding='utf-8') as f:
            if pretty_print:
                json.dump(edges_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(edges_data, f, ensure_ascii=False)
        
        output_paths.append(str(edges_path))
        
        return output_paths


@register_component(
    "writer",
    "csv_writer",
    description="Writes knowledge graph to CSV format",
    config_schema={
        "type": "object",
        "properties": {
            "output_dir": {
                "type": "string",
                "description": "Directory to write CSV files",
                "default": "./output"
            },
            "nodes_filename": {
                "type": "string",
                "description": "Filename for nodes CSV",
                "default": "nodes.csv"
            },
            "edges_filename": {
                "type": "string",
                "description": "Filename for edges CSV",
                "default": "edges.csv"
            },
            "include_embeddings": {
                "type": "boolean",
                "description": "Whether to include embeddings in CSV",
                "default": False
            }
        }
    }
)
class CSVWriter(Writer):
    """
    Writer that outputs knowledge graphs as CSV files.
    
    Creates separate CSV files for nodes and edges,
    suitable for import into databases or analysis tools.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Write knowledge graph to CSV format.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with output path
        """
        subgraphs = state.get("vectorized_subgraphs", state.get("subgraphs", []))
        if not subgraphs:
            logger.warning("No subgraphs to write")
            updated_state = state.copy()
            updated_state["output_path"] = ""
            return updated_state
        
        # Configuration
        output_dir = self.get_config_value("output_dir", "./output")
        nodes_filename = self.get_config_value("nodes_filename", "nodes.csv")
        edges_filename = self.get_config_value("edges_filename", "edges.csv")
        include_embeddings = self.get_config_value("include_embeddings", False)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Merge all subgraphs
        merged_graph = self._merge_subgraphs(subgraphs)
        
        # Write CSV files
        nodes_path = self._write_nodes_csv(
            merged_graph.nodes, 
            Path(output_dir) / nodes_filename,
            include_embeddings
        )
        
        edges_path = self._write_edges_csv(
            merged_graph.edges,
            Path(output_dir) / edges_filename,
            include_embeddings
        )
        
        logger.info(f"Wrote knowledge graph to {nodes_path} and {edges_path}")
        
        # Update state
        updated_state = state.copy()
        updated_state["output_path"] = nodes_path  # Return nodes file as primary output
        
        return updated_state
    
    def _merge_subgraphs(self, subgraphs: List[SubGraph]) -> SubGraph:
        """Merge multiple subgraphs into one."""
        if not subgraphs:
            return SubGraph()
        
        if len(subgraphs) == 1:
            return subgraphs[0]
        
        merged = subgraphs[0]
        for subgraph in subgraphs[1:]:
            merged = merged.merge(subgraph)
        
        return merged
    
    def _write_nodes_csv(
        self,
        nodes: List[Node], 
        output_path: Path,
        include_embeddings: bool
    ) -> str:
        """
        Write nodes to CSV file.
        
        Args:
            nodes: List of nodes to write
            output_path: Path to CSV file
            include_embeddings: Whether to include embeddings
            
        Returns:
            Path to written file
        """
        if not nodes:
            # Create empty file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "name", "label", "official_name", "source_chunks", "confidence"])
            return str(output_path)

        # Determine all property keys
        all_property_keys = set()
        for node in nodes:
            all_property_keys.update(node.properties.keys())

        # Create CSV header
        header = ["id", "name", "label", "official_name", "source_chunks", "confidence"]
        
        # Add property columns
        property_columns = sorted(all_property_keys)
        header.extend(property_columns)
        
        # Add embeddings column if requested
        if include_embeddings:
            header.append("embeddings")
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            
            for node in nodes:
                row = [
                    node.id,
                    node.name,
                    node.label,
                    node.official_name or "",
                    "|".join(node.source_chunks) if node.source_chunks else "",
                    node.confidence or ""
                ]
                
                # Add property values
                for prop_key in property_columns:
                    prop_value = node.properties.get(prop_key, "")
                    if isinstance(prop_value, (list, dict)):
                        prop_value = json.dumps(prop_value)
                    row.append(str(prop_value))
                
                # Add embeddings if requested
                if include_embeddings:
                    if node.embeddings:
                        embeddings_str = json.dumps(node.embeddings)
                    else:
                        embeddings_str = ""
                    row.append(embeddings_str)
                
                writer.writerow(row)
        
        return str(output_path)
    
    def _write_edges_csv(
        self,
        edges: List[Edge],
        output_path: Path,
        include_embeddings: bool
    ) -> str:
        """
        Write edges to CSV file.
        
        Args:
            edges: List of edges to write
            output_path: Path to CSV file
            include_embeddings: Whether to include embeddings
            
        Returns:
            Path to written file
        """
        if not edges:
            # Create empty file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "source_id", "target_id", "relation_type", "properties"])
            return str(output_path)
        
        # Determine all property keys
        all_property_keys = set()
        for edge in edges:
            if edge.properties:
                all_property_keys.update(edge.properties.keys())
        
        # Remove embeddings from property keys if it will be handled separately
        if include_embeddings and "embeddings" in all_property_keys:
            all_property_keys.remove("embeddings")
        
        # Create CSV header
        header = [
            "id", "source_id", "target_id", "relation_type", 
            "directed", "weight", "source_chunks", "confidence"
        ]
        
        # Add property columns
        property_columns = sorted(all_property_keys)
        header.extend(property_columns)
        
        # Add embeddings column if requested
        if include_embeddings:
            header.append("embeddings")
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            
            for edge in edges:
                row = [
                    edge.id,
                    edge.source_id,
                    edge.target_id,
                    edge.relation_type,
                    edge.directed,
                    edge.weight or "",
                    "|".join(edge.source_chunks) if edge.source_chunks else "",
                    edge.confidence or ""
                ]
                
                # Add property values
                for prop_key in property_columns:
                    prop_value = edge.properties.get(prop_key, "") if edge.properties else ""
                    if isinstance(prop_value, (list, dict)):
                        prop_value = json.dumps(prop_value)
                    row.append(str(prop_value))
                
                # Add embeddings if requested
                if include_embeddings:
                    embeddings_str = ""
                    if edge.properties and "embeddings" in edge.properties:
                        embeddings_str = json.dumps(edge.properties["embeddings"])
                    row.append(embeddings_str)
                
                writer.writerow(row)
        
        return str(output_path)


@register_component(
    "writer",
    "neo4j_writer",
    description="Writes knowledge graph to Neo4j database",
    config_schema={
        "type": "object",
        "properties": {
            "uri": {
                "type": "string",
                "description": "Neo4j connection URI",
                "default": "bolt://localhost:7687"
            },
            "username": {
                "type": "string",
                "description": "Neo4j username",
                "default": "neo4j"
            },
            "password": {
                "type": "string",
                "description": "Neo4j password"
            },
            "database": {
                "type": "string",
                "description": "Neo4j database name",
                "default": "neo4j"
            },
            "clear_database": {
                "type": "boolean",
                "description": "Whether to clear database before writing",
                "default": False
            },
            "batch_size": {
                "type": "integer",
                "description": "Batch size for database operations",
                "default": 1000
            }
        }
    }
)
class Neo4jWriter(Writer):
    """
    Writer that stores knowledge graphs in Neo4j database.
    
    Creates nodes and relationships in Neo4j, preserving
    all properties and metadata.
    """
    
    def __init__(self, config):
        """Initialize Neo4j writer."""
        super().__init__(config)
        
        if not HAS_NEO4J:
            raise ImportError("neo4j not installed. Install with: pip install neo4j")
        
        # Configuration
        uri = self.get_config_value("uri", "bolt://localhost:7687")
        username = self.get_config_value("username", "neo4j")
        password = self.get_config_value("password")
        
        if not password:
            raise ValueError("Neo4j password is required")
        
        # Create driver
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    @staticmethod
    def _run_with_retry(session, cypher: str, **kwargs):
        """
        Execute a Cypher query with retry for transient Neo4j errors.

        Args:
            session: Neo4j session
            cypher: Cypher query string
            **kwargs: Parameters to pass to session.run()

        Returns:
            Result of session.run()
        """
        if NEO4J_TRANSIENT_ERRORS:

            @retry_with_backoff(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                retryable_exceptions=NEO4J_TRANSIENT_ERRORS,
            )
            def _execute():
                return session.run(cypher, **kwargs)

            return _execute()
        else:
            return session.run(cypher, **kwargs)

    def process(self, state: PipelineState) -> PipelineState:
        """
        Write knowledge graph to Neo4j database.

        Args:
            state: Current pipeline state

        Returns:
            Updated pipeline state with output path (connection info)
        """
        subgraphs = state.get("vectorized_subgraphs", state.get("subgraphs", []))
        if not subgraphs:
            logger.warning("No subgraphs to write")
            updated_state = state.copy()
            updated_state["output_path"] = ""
            return updated_state

        # Configuration
        database = self.get_config_value("database", "neo4j")
        clear_database = self.get_config_value("clear_database", False)
        batch_size = self.get_config_value("batch_size", 1000)

        # Merge all subgraphs
        merged_graph = self._merge_subgraphs(subgraphs)

        # Get chunks from pipeline state
        chunks = state.get("split_chunks", state.get("chunks", []))
        chunk_map = {chunk.id: chunk for chunk in chunks} if chunks else {}

        # Track per-operation failures
        write_failures: List[Dict[str, Any]] = []

        try:
            with self.driver.session(database=database) as session:
                # Clear database if requested
                if clear_database:
                    self._run_with_retry(session, "MATCH (n) DETACH DELETE n")
                    logger.info("Cleared Neo4j database")

                # Write chunk nodes first
                chunks_written, chunk_failures = self._write_chunks_to_neo4j(
                    session, chunk_map, batch_size
                )
                write_failures.extend(chunk_failures)

                # Write entity nodes in batches
                nodes_written, node_failures = self._write_nodes_to_neo4j(
                    session, merged_graph.nodes, batch_size
                )
                write_failures.extend(node_failures)

                # Write edges in batches
                edges_written, edge_failures = self._write_edges_to_neo4j(
                    session, merged_graph.edges, batch_size
                )
                write_failures.extend(edge_failures)

                # Create source relationships from chunks to entities
                source_rels_written = self._write_chunk_source_relationships(
                    session, merged_graph.nodes, batch_size
                )

                logger.info(
                    f"Wrote {chunks_written} chunks, {nodes_written} nodes, "
                    f"{edges_written} edges, and {source_rels_written} source "
                    f"relationships to Neo4j"
                )

                if write_failures:
                    logger.warning(
                        f"Encountered {len(write_failures)} write failures during Neo4j ingestion"
                    )

            output_path = (
                f"neo4j://{self.get_config_value('username')}@"
                f"{self.get_config_value('uri').split('//')[-1]}/{database}"
            )

        except NEO4J_FATAL_ERRORS as e:
            logger.error(f"Fatal Neo4j connection error: {e}")
            raise  # Unrecoverable -- let the pipeline know

        except Exception as e:
            logger.error(f"Error writing to Neo4j: {e}")
            output_path = ""
            write_failures.append({"operation": "session", "error": str(e)})

        # Update state
        updated_state = state.copy()
        updated_state["output_path"] = output_path

        # Store write failures in metadata
        if write_failures:
            metadata = dict(updated_state.get("metadata", {}) or {})
            metadata["write_failures"] = write_failures
            metadata["write_failure_count"] = len(write_failures)
            updated_state["metadata"] = metadata

        return updated_state

    def _merge_subgraphs(self, subgraphs: List[SubGraph]) -> SubGraph:
        """Merge multiple subgraphs into one."""
        if not subgraphs:
            return SubGraph()

        if len(subgraphs) == 1:
            return subgraphs[0]

        merged = subgraphs[0]
        for subgraph in subgraphs[1:]:
            merged = merged.merge(subgraph)

        return merged

    def _write_chunks_to_neo4j(
        self, session, chunk_map: Dict[str, Any], batch_size: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Write Chunk nodes to Neo4j in batches.

        Args:
            session: Neo4j session
            chunk_map: Dictionary mapping chunk IDs to Chunk objects
            batch_size: Batch size

        Returns:
            Tuple of (number of chunks written, list of failure records)
        """
        if not chunk_map:
            logger.info("No chunks to write")
            return 0, []

        chunks_written = 0
        failures: List[Dict[str, Any]] = []
        chunk_list = list(chunk_map.values())

        for i in range(0, len(chunk_list), batch_size):
            batch = chunk_list[i:i + batch_size]
            batch_index = i // batch_size

            try:
                # Prepare chunk data for batch
                chunk_data = []
                for chunk in batch:
                    chunk_dict = {
                        "id": chunk.id,
                        "content": chunk.content,
                        "chunk_type": (
                            chunk.chunk_type.value
                            if hasattr(chunk.chunk_type, "value")
                            else str(chunk.chunk_type)
                        ),
                        "length": chunk.length,
                        "word_count": chunk.word_count,
                    }

                    # Add optional fields
                    if chunk.page_number is not None:
                        chunk_dict["page_number"] = chunk.page_number
                    if chunk.chunk_index is not None:
                        chunk_dict["chunk_index"] = chunk.chunk_index
                    if chunk.language:
                        chunk_dict["language"] = chunk.language

                    chunk_data.append(chunk_dict)

                # Create Chunk nodes in Neo4j
                cypher = """
                UNWIND $chunks as chunkData
                MERGE (c:Chunk {id: chunkData.id})
                SET c += chunkData
                """

                self._run_with_retry(session, cypher, chunks=chunk_data)
                chunks_written += len(batch)

            except Exception as e:
                logger.warning(f"Failed to write chunk batch {batch_index}: {e}")
                failures.append({
                    "operation": "write_chunks",
                    "batch_index": batch_index,
                    "batch_size": len(batch),
                    "error": str(e),
                })

        return chunks_written, failures

    def _write_chunk_source_relationships(self, session, nodes: List[Node], batch_size: int) -> int:
        """
        Create source relationships from Chunk nodes to Entity nodes.

        Args:
            session: Neo4j session
            nodes: List of entity nodes
            batch_size: Batch size

        Returns:
            Number of relationships written
        """
        relationships_written = 0

        # Collect all chunk-entity pairs
        chunk_entity_pairs = []
        for node in nodes:
            if node.source_chunks:
                for chunk_id in node.source_chunks:
                    chunk_entity_pairs.append({
                        "chunk_id": chunk_id,
                        "entity_id": node.id
                    })

        if not chunk_entity_pairs:
            logger.info("No chunk-entity relationships to write")
            return 0

        # Write relationships in batches
        for i in range(0, len(chunk_entity_pairs), batch_size):
            batch = chunk_entity_pairs[i:i + batch_size]

            cypher = """
            UNWIND $pairs as pair
            MATCH (c:Chunk {id: pair.chunk_id})
            MATCH (e:Entity {id: pair.entity_id})
            MERGE (c)-[r:SOURCE]->(e)
            """

            self._run_with_retry(session, cypher, pairs=batch)
            relationships_written += len(batch)

        return relationships_written

    def _write_nodes_to_neo4j(
        self, session, nodes: List[Node], batch_size: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Write nodes to Neo4j in batches.

        Args:
            session: Neo4j session
            nodes: List of nodes to write
            batch_size: Batch size

        Returns:
            Tuple of (number of nodes written, list of failure records)
        """
        nodes_written = 0
        failures: List[Dict[str, Any]] = []

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # Prepare node data for batch
            node_data = []
            for node in batch:
                node_dict = {
                    "id": node.id,
                    "name": node.name,
                    "label": node.label,
                }

                # Add properties
                if node.properties:
                    # Filter out complex objects that Neo4j can't store directly
                    simple_props = {}
                    for key, value in node.properties.items():
                        if isinstance(value, (str, int, float, bool)):
                            simple_props[key] = value
                        elif isinstance(value, list) and all(
                            isinstance(v, (str, int, float, bool)) for v in value
                        ):
                            simple_props[key] = value
                        else:
                            # Convert complex objects to strings
                            simple_props[key] = str(value)

                    node_dict.update(simple_props)

                # Add metadata
                if node.official_name:
                    node_dict["official_name"] = node.official_name
                if node.source_chunks:
                    node_dict["source_chunks"] = node.source_chunks
                if node.confidence is not None:
                    node_dict["confidence"] = node.confidence

                # Add embeddings
                if node.embeddings:
                    node_dict["embeddings"] = node.embeddings

                node_data.append(node_dict)

            # Create nodes in Neo4j with dynamic labels
            # We need to set labels per node since each can have a different category
            for node in node_data:
                label = node.get("label", "Entity")
                # Sanitize label to be a valid Neo4j label (alphanumeric and underscore only)
                sanitized_label = "".join(
                    c if c.isalnum() or c == "_" else "_" for c in label
                )

                # Each entity gets two labels: :Entity (base) and category-specific
                cypher = f"""
                MERGE (n:Entity {{id: $nodeData.id}})
                SET n += $nodeData
                SET n:{sanitized_label}
                """

                try:
                    self._run_with_retry(session, cypher, nodeData=node)
                    nodes_written += 1
                except Exception as e:
                    node_id = node.get("id", "unknown")
                    logger.warning(f"Failed to write node {node_id}: {e}")
                    failures.append({
                        "operation": "write_node",
                        "node_id": node_id,
                        "error": str(e),
                    })

        return nodes_written, failures
    
    def _write_edges_to_neo4j(
        self, session, edges: List[Edge], batch_size: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Write edges to Neo4j in batches.

        Handles three types of relationships:
        1. isA (taxonomy): Creates relationship AND adds ConceptType as label
        2. Schema-defined: Standard relationship creation
        3. Discovered: Standard relationship creation

        Args:
            session: Neo4j session
            edges: List of edges to write
            batch_size: Batch size

        Returns:
            Tuple of (number of edges written, list of failure records)
        """
        edges_written = 0
        failures: List[Dict[str, Any]] = []

        # Separate special relationships from regular ones
        isa_edges = []
        belongto_edges = []
        regular_edges = []

        for edge in edges:
            if edge.relation_type == "isA":
                isa_edges.append(edge)
            elif edge.relation_type == "belongTo":
                belongto_edges.append(edge)
            else:
                regular_edges.append(edge)

        # Write isA relationships with special handling (Entity -> ConceptType)
        edges_written += self._write_isa_relationships(session, isa_edges, batch_size)

        # Write belongTo relationships with special handling (ConceptType -> ConceptType)
        edges_written += self._write_belongto_relationships(session, belongto_edges, batch_size)

        # Write regular relationships
        for i in range(0, len(regular_edges), batch_size):
            batch = regular_edges[i:i + batch_size]

            # Prepare edge data for batch
            edge_data = []
            for edge in batch:
                edge_dict = {
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation_type": edge.relation_type,
                    "directed": edge.directed,
                }

                # Add optional properties
                if edge.weight is not None:
                    edge_dict["weight"] = edge.weight
                if edge.confidence is not None:
                    edge_dict["confidence"] = edge.confidence
                if edge.source_chunks:
                    edge_dict["source_chunks"] = edge.source_chunks

                # Add custom properties (including SPG edge properties)
                if edge.properties:
                    # Convert properties for Neo4j storage
                    neo4j_props = self._convert_edge_properties_for_neo4j(edge.properties)
                    edge_dict.update(neo4j_props)

                edge_data.append(edge_dict)

            # Create relationships in Neo4j
            cypher = """
            UNWIND $edges as edgeData
            MATCH (source {id: edgeData.source_id})
            MATCH (target {id: edgeData.target_id})
            CALL apoc.create.relationship(source, edgeData.relation_type, edgeData, target) YIELD rel
            RETURN count(rel)
            """

            # Fallback if APOC is not available
            try:
                self._run_with_retry(session, cypher, edges=edge_data)
                edges_written += len(batch)
            except Exception:
                # Use simpler approach without APOC
                for edge_dict in edge_data:
                    simple_cypher = f"""
                    MATCH (source {{id: $source_id}})
                    MATCH (target {{id: $target_id}})
                    MERGE (source)-[r:`{edge_dict['relation_type']}`]->(target)
                    SET r += $properties
                    """

                    properties = {
                        k: v
                        for k, v in edge_dict.items()
                        if k not in ["source_id", "target_id", "relation_type"]
                    }

                    try:
                        self._run_with_retry(
                            session, simple_cypher,
                            source_id=edge_dict["source_id"],
                            target_id=edge_dict["target_id"],
                            properties=properties,
                        )
                        edges_written += 1
                    except Exception as e:
                        edge_id = edge_dict.get("id", "unknown")
                        logger.warning(f"Failed to write edge {edge_id}: {e}")
                        failures.append({
                            "operation": "write_edge",
                            "edge_id": edge_id,
                            "error": str(e),
                        })

        return edges_written, failures

    def _convert_edge_properties_for_neo4j(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert edge properties to Neo4j-compatible format.

        Handles SPG edge properties with proper type conversion:
        - Preserves numeric types (Float, Integer)
        - Converts complex objects to JSON strings
        - Handles lists appropriately

        Args:
            properties: Dictionary of edge properties

        Returns:
            Neo4j-compatible properties dictionary
        """
        neo4j_props = {}

        for key, value in properties.items():
            # Direct storage for simple types
            if isinstance(value, (str, int, float, bool, type(None))):
                neo4j_props[key] = value

            # Lists of simple types
            elif isinstance(value, list):
                if all(isinstance(v, (str, int, float, bool)) for v in value):
                    neo4j_props[key] = value
                else:
                    # Complex list - convert to JSON string
                    neo4j_props[key] = json.dumps(value)

            # Dictionaries - convert to JSON string
            elif isinstance(value, dict):
                neo4j_props[key] = json.dumps(value)

            # Other objects - convert to string
            else:
                neo4j_props[key] = str(value)

        return neo4j_props

    def _write_isa_relationships(self, session, isa_edges: List[Edge], batch_size: int) -> int:
        """
        Write isA (taxonomy) relationships to Neo4j with special handling.

        For isA relationships (Entity -> ConceptType):
        1. Create the isA relationship edge
        2. Get the target ConceptType label and add it to the source entity

        Args:
            session: Neo4j session
            isa_edges: List of isA relationship edges
            batch_size: Batch size

        Returns:
            Number of edges written
        """
        edges_written = 0

        for i in range(0, len(isa_edges), batch_size):
            batch = isa_edges[i:i + batch_size]

            for edge in batch:
                # Prepare edge properties
                edge_props = {
                    "confidence": edge.confidence if edge.confidence is not None else 0.95,
                    "relationship_category": "taxonomy"
                }

                if edge.source_chunks:
                    edge_props["source_chunks"] = edge.source_chunks

                # Add any additional properties
                if edge.properties:
                    for key, value in edge.properties.items():
                        if isinstance(value, (str, int, float, bool)):
                            edge_props[key] = value

                # Create isA relationship
                # Also get the target (ConceptType) label to add to source entity
                cypher = """
                MATCH (source:Entity {id: $source_id})
                MATCH (target {id: $target_id})
                MERGE (source)-[r:isA]->(target)
                SET r += $properties
                WITH source, target
                SET source += {taxonomy_label: target.label}
                RETURN source, target
                """

                try:
                    self._run_with_retry(
                                session, cypher,
                                source_id=edge.source_id,
                                target_id=edge.target_id,
                                properties=edge_props,
                            )
                    edges_written += 1
                except Exception as e:
                    logger.warning(f"Error writing isA relationship {edge.source_id} -> {edge.target_id}: {e}")
                    continue

        return edges_written

    def _write_belongto_relationships(self, session, belongto_edges: List[Edge], batch_size: int) -> int:
        """
        Write belongTo (concept hierarchy) relationships to Neo4j with special handling.

        For belongTo relationships (ConceptType -> ConceptType):
        1. Create the belongTo relationship edge
        2. Store hierarchyLevel as edge property

        Example: Industry:Software -[belongTo {hierarchyLevel: 1}]-> Industry:Technology

        Args:
            session: Neo4j session
            belongto_edges: List of belongTo relationship edges
            batch_size: Batch size

        Returns:
            Number of edges written
        """
        edges_written = 0

        for i in range(0, len(belongto_edges), batch_size):
            batch = belongto_edges[i:i + batch_size]

            for edge in batch:
                # Prepare edge properties
                edge_props = {
                    "confidence": edge.confidence if edge.confidence is not None else 0.9,
                    "relationship_category": "concept_hierarchy"
                }

                if edge.source_chunks:
                    edge_props["source_chunks"] = edge.source_chunks

                # Add hierarchyLevel from SPG edge properties
                if edge.properties and "hierarchyLevel" in edge.properties:
                    edge_props["hierarchyLevel"] = edge.properties["hierarchyLevel"]

                # Add any additional properties
                if edge.properties:
                    for key, value in edge.properties.items():
                        if key != "hierarchyLevel" and isinstance(value, (str, int, float, bool)):
                            edge_props[key] = value

                # Create belongTo relationship between ConceptTypes
                cypher = """
                MATCH (source {id: $source_id})
                MATCH (target {id: $target_id})
                MERGE (source)-[r:belongTo]->(target)
                SET r += $properties
                RETURN source, target
                """

                try:
                    self._run_with_retry(
                                session, cypher,
                                source_id=edge.source_id,
                                target_id=edge.target_id,
                                properties=edge_props,
                            )
                    edges_written += 1
                except Exception as e:
                    logger.warning(f"Error writing belongTo relationship {edge.source_id} -> {edge.target_id}: {e}")
                    continue

        return edges_written

    def __del__(self):
        """Close Neo4j driver on cleanup."""
        if hasattr(self, 'driver'):
            self.driver.close()