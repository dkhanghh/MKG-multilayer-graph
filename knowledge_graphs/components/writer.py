"""
Writer components for KAG-LangGraph pipeline.

This module contains writer implementations that output knowledge graphs
in various formats including JSON, CSV, GraphML, and database storage.
"""

import json
import csv
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import datetime

from .base import Writer
from ..models.graph import SubGraph, Node, Edge
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component

logger = logging.getLogger(__name__)

# Optional imports for database connectivity
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
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
                writer.writerow(["id", "name", "node_type", "properties", "source_chunks"])
            return str(output_path)
        
        # Determine all property keys
        all_property_keys = set()
        for node in nodes:
            all_property_keys.update(node.properties.keys())
        
        # Create CSV header
        header = ["id", "name", "node_type", "aliases", "source_chunks", "confidence"]
        
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
                    node.node_type,
                    "|".join(node.aliases) if node.aliases else "",
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
        
        try:
            with self.driver.session(database=database) as session:
                # Clear database if requested
                if clear_database:
                    session.run("MATCH (n) DETACH DELETE n")
                    logger.info("Cleared Neo4j database")
                
                # Write nodes in batches
                nodes_written = self._write_nodes_to_neo4j(
                    session, merged_graph.nodes, batch_size
                )
                
                # Write edges in batches
                edges_written = self._write_edges_to_neo4j(
                    session, merged_graph.edges, batch_size
                )
                
                logger.info(f"Wrote {nodes_written} nodes and {edges_written} edges to Neo4j")
            
            output_path = f"neo4j://{self.get_config_value('username')}@{self.get_config_value('uri').split('//')[-1]}/{database}"
        
        except Exception as e:
            logger.error(f"Error writing to Neo4j: {e}")
            output_path = ""
        
        # Update state
        updated_state = state.copy()
        updated_state["output_path"] = output_path
        
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
    
    def _write_nodes_to_neo4j(self, session, nodes: List[Node], batch_size: int) -> int:
        """
        Write nodes to Neo4j in batches.
        
        Args:
            session: Neo4j session
            nodes: List of nodes to write
            batch_size: Batch size
            
        Returns:
            Number of nodes written
        """
        nodes_written = 0
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            
            # Prepare node data for batch
            node_data = []
            for node in batch:
                node_dict = {
                    "id": node.id,
                    "name": node.name,
                    "node_type": node.node_type
                }
                
                # Add properties
                if node.properties:
                    # Filter out complex objects that Neo4j can't store directly
                    simple_props = {}
                    for key, value in node.properties.items():
                        if isinstance(value, (str, int, float, bool)):
                            simple_props[key] = value
                        elif isinstance(value, list) and all(isinstance(v, (str, int, float, bool)) for v in value):
                            simple_props[key] = value
                        else:
                            # Convert complex objects to strings
                            simple_props[key] = str(value)
                    
                    node_dict.update(simple_props)
                
                # Add metadata
                if node.aliases:
                    node_dict["aliases"] = node.aliases
                if node.source_chunks:
                    node_dict["source_chunks"] = node.source_chunks
                if node.confidence is not None:
                    node_dict["confidence"] = node.confidence
                
                node_data.append(node_dict)
            
            # Create nodes in Neo4j
            cypher = """
            UNWIND $nodes as nodeData
            MERGE (n {id: nodeData.id})
            SET n += nodeData
            SET n:Entity
            SET n:` + nodeData.node_type + `
            """
            
            session.run(cypher, nodes=node_data)
            nodes_written += len(batch)
        
        return nodes_written
    
    def _write_edges_to_neo4j(self, session, edges: List[Edge], batch_size: int) -> int:
        """
        Write edges to Neo4j in batches.
        
        Args:
            session: Neo4j session
            edges: List of edges to write
            batch_size: Batch size
            
        Returns:
            Number of edges written
        """
        edges_written = 0
        
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            
            # Prepare edge data for batch
            edge_data = []
            for edge in batch:
                edge_dict = {
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation_type": edge.relation_type,
                    "directed": edge.directed
                }
                
                # Add optional properties
                if edge.weight is not None:
                    edge_dict["weight"] = edge.weight
                if edge.confidence is not None:
                    edge_dict["confidence"] = edge.confidence
                if edge.source_chunks:
                    edge_dict["source_chunks"] = edge.source_chunks
                
                # Add custom properties
                if edge.properties:
                    # Filter out complex objects
                    simple_props = {}
                    for key, value in edge.properties.items():
                        if isinstance(value, (str, int, float, bool)):
                            simple_props[key] = value
                        elif isinstance(value, list) and all(isinstance(v, (str, int, float, bool)) for v in value):
                            simple_props[key] = value
                        else:
                            simple_props[key] = str(value)
                    
                    edge_dict.update(simple_props)
                
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
                session.run(cypher, edges=edge_data)
            except Exception:
                # Use simpler approach without APOC
                for edge_dict in edge_data:
                    simple_cypher = f"""
                    MATCH (source {{id: $source_id}})
                    MATCH (target {{id: $target_id}})
                    MERGE (source)-[r:`{edge_dict['relation_type']}`]->(target)
                    SET r += $properties
                    """
                    
                    properties = {k: v for k, v in edge_dict.items() 
                                 if k not in ['source_id', 'target_id', 'relation_type']}
                    
                    session.run(simple_cypher, 
                               source_id=edge_dict['source_id'],
                               target_id=edge_dict['target_id'], 
                               properties=properties)
            
            edges_written += len(batch)
        
        return edges_written
    
    def __del__(self):
        """Close Neo4j driver on cleanup."""
        if hasattr(self, 'driver'):
            self.driver.close()