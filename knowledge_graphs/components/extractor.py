"""
Extractor components for KAG-LangGraph pipeline.

This module contains extractor implementations that extract structured knowledge
(entities, relationships) from text chunks using LLMs and other techniques.
"""

import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Set, Tuple
import re

from .base import Extractor
from ..models.chunk import Chunk
from ..models.graph import SubGraph, Node, Edge
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component
from ..utils.llm_client import LLMClient, create_llm_client, LLMMessage, extract_json_from_response, create_extraction_prompt
from ..utils.template_loader import load_prompt_template, get_template_loader

logger = logging.getLogger(__name__)


@register_component(
    "extractor",
    "llm_extractor",
    description="Extracts entities and relationships using LLM",
    config_schema={
        "type": "object",
        "properties": {
            "llm_provider": {
                "type": "string",
                "enum": ["openai", "ollama"],
                "description": "LLM provider to use",
                "default": "openai"
            },
            "model": {
                "type": "string", 
                "description": "Model name to use",
                "default": "gpt-3.5-turbo"
            },
            "api_key": {
                "type": "string",
                "description": "API key for the LLM provider"
            },
            "temperature": {
                "type": "number",
                "description": "Temperature for LLM generation",
                "default": 0.1
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens for LLM response",
                "default": 2000
            },
            "entity_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Types of entities to extract",
                "default": ["Person", "Organization", "Location", "Concept"]
            },
            "relation_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Types of relationships to extract",
                "default": ["works_for", "located_in", "related_to", "part_of"]
            },
            "extraction_schema": {
                "type": "object",
                "description": "Custom extraction schema",
                "default": {}
            },
            "batch_size": {
                "type": "integer",
                "description": "Number of chunks to process in parallel",
                "default": 5
            },
            "use_template": {
                "type": "boolean",
                "description": "Whether to use Jinja2 templates for prompts",
                "default": False
            },
            "template_name": {
                "type": "string",
                "description": "Name of the template file to use (e.g., 'ner.md')",
                "default": "ner.md"
            }
        }
    }
)
class LLMExtractor(Extractor):
    """
    Extractor that uses Large Language Models to extract structured knowledge.
    
    Extracts entities and relationships from text chunks and creates
    SubGraph objects containing the extracted knowledge.
    """
    
    def __init__(self, config):
        """Initialize LLM extractor."""
        super().__init__(config)
        
        # Initialize LLM client
        llm_provider = self.get_config_value("llm_provider", "openai")
        model = self.get_config_value("model", "gpt-3.5-turbo")
        api_key = self.get_config_value("api_key")
        temperature = self.get_config_value("temperature", 0.1)
        max_tokens = self.get_config_value("max_tokens", 2000)
        
        # Create LLM client
        try:
            self.llm_client = create_llm_client(
                provider=llm_provider,
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise
        
        # Setup extraction schema
        self.entity_types = self.get_config_value("entity_types", ["Person", "Organization", "Location", "Concept"])
        self.relation_types = self.get_config_value("relation_types", ["works_for", "located_in", "related_to", "part_of"])
        
        custom_schema = self.get_config_value("extraction_schema", {})
        self.extraction_schema = self._build_extraction_schema(custom_schema)
        
        logger.info(f"Initialized LLM extractor with {llm_provider} {model}")
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Extract knowledge from text chunks using LLM.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with extracted subgraphs
        """
        chunks = state.get("split_chunks", state.get("chunks", []))
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")
        
        batch_size = self.get_config_value("batch_size", 5)
        
        subgraphs = []
        
        # Process chunks in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            try:
                batch_subgraphs = self._process_chunk_batch(batch)
                subgraphs.extend(batch_subgraphs)
            except Exception as e:
                logger.error(f"Error processing chunk batch {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"Extracted knowledge from {len(chunks)} chunks, created {len(subgraphs)} subgraphs")
        
        # Merge subgraphs to resolve duplicate entities
        merged_subgraphs = self._merge_subgraphs(subgraphs)
        
        # Update state
        updated_state = state.copy()
        updated_state["subgraphs"] = merged_subgraphs
        
        return updated_state
    
    def _process_chunk_batch(self, chunks: List[Chunk]) -> List[SubGraph]:
        """
        Process a batch of chunks.
        
        Args:
            chunks: List of chunks to process
            
        Returns:
            List of extracted subgraphs
        """
        subgraphs = []
        
        for chunk in chunks:
            try:
                subgraph = self._extract_from_chunk(chunk)
                if not subgraph.is_empty():
                    subgraphs.append(subgraph)
            except Exception as e:
                logger.error(f"Error extracting from chunk {chunk.id}: {e}")
                continue
        
        return subgraphs
    
    def _extract_from_chunk(self, chunk: Chunk) -> SubGraph:
        """
        Extract knowledge from a single chunk.

        Args:
            chunk: Chunk to extract from

        Returns:
            SubGraph with extracted knowledge
        """
        text = chunk.content

        # Create extraction prompt - use template if configured
        use_template = self.get_config_value("use_template", False)

        if use_template:
            prompt = self._create_template_prompt(text)
        else:
            # Use traditional prompt creation
            prompt = create_extraction_prompt(
                text=text,
                schema=self.extraction_schema,
                instructions=self._get_extraction_instructions()
            )
        
        # Call LLM
        try:
            response = self.llm_client.simple_chat(prompt)
            extraction_result = extract_json_from_response(response)
            
            if not extraction_result:
                logger.warning(f"No valid JSON found in LLM response for chunk {chunk.id}")
                return SubGraph(source_chunk_id=chunk.id)
            
            # Convert to SubGraph
            subgraph = self._create_subgraph_from_extraction(chunk, extraction_result)
            return subgraph
            
        except Exception as e:
            logger.error(f"Error calling LLM for chunk {chunk.id}: {e}")
            return SubGraph(source_chunk_id=chunk.id)
    
    def _build_extraction_schema(self, custom_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the extraction schema for the LLM.
        
        Args:
            custom_schema: Custom schema to merge
            
        Returns:
            Complete extraction schema
        """
        default_schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "type": {"type": "string", "enum": self.entity_types},
                            "description": {"type": "string"},
                            "properties": {"type": "object"}
                        },
                        "required": ["id", "name", "type"]
                    }
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object", 
                        "properties": {
                            "source_id": {"type": "string"},
                            "target_id": {"type": "string"},
                            "relation_type": {"type": "string", "enum": self.relation_types},
                            "description": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                        },
                        "required": ["source_id", "target_id", "relation_type"]
                    }
                }
            },
            "required": ["entities", "relationships"]
        }
        
        # Merge with custom schema
        if custom_schema:
            # Check if it's a domain schema file path
            if isinstance(custom_schema, str) and custom_schema.endswith('.schema'):
                custom_schema = self._parse_domain_schema_file(custom_schema)
            elif isinstance(custom_schema, str):
                # Assume it's domain schema content
                custom_schema = self._parse_domain_schema_content(custom_schema)

            # Simple merge - could be more sophisticated
            if isinstance(custom_schema, dict):
                default_schema.update(custom_schema)

        return default_schema

    def _parse_domain_schema_file(self, schema_file_path: str) -> Dict[str, Any]:
        """
        Parse domain schema from a .schema file.

        Args:
            schema_file_path: Path to the .schema file

        Returns:
            Parsed schema dictionary
        """
        try:
            with open(schema_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._parse_domain_schema_content(content)
        except Exception as e:
            logger.error(f"Failed to parse domain schema file {schema_file_path}: {e}")
            return {}

    def _parse_domain_schema_content(self, content: str) -> Dict[str, Any]:
        """
        Parse domain schema content in the custom format.

        Expected format:
        namespace DomainKG

        EntityType(中文名): EntityType
             properties:
                property_name(中文名): Type
                    index: IndexType

        Args:
            content: Schema content string

        Returns:
            Schema dictionary compatible with the extractor
        """
        try:
            entity_types = []
            lines = content.strip().split('\n')
            current_entity = None

            for line in lines:
                line = line.strip()
                if not line or line.startswith('namespace'):
                    continue

                # Parse entity type definition
                if line.endswith(': EntityType'):
                    # Extract entity name (before parentheses if present)
                    entity_full = line.replace(': EntityType', '')
                    if '(' in entity_full:
                        entity_name = entity_full.split('(')[0]
                    else:
                        entity_name = entity_full

                    entity_types.append(entity_name)
                    current_entity = entity_name
                    logger.debug(f"Found entity type: {entity_name}")

            # Update the entity types for the schema
            if entity_types:
                self.entity_types = entity_types
                logger.info(f"Updated entity types from domain schema: {entity_types}")

            # Return empty dict as the main schema structure doesn't need to change
            # The entity types are already updated in self.entity_types
            return {}

        except Exception as e:
            logger.error(f"Failed to parse domain schema content: {e}")
            return {}

    def _get_extraction_instructions(self) -> str:
        """
        Get instructions for the extraction task.
        
        Returns:
            Instruction string for the LLM
        """
        entity_types_str = ", ".join(self.entity_types)
        relation_types_str = ", ".join(self.relation_types)
        
        instructions = f"""
Extract entities and relationships from the provided text:

Entity Types: {entity_types_str}
Relationship Types: {relation_types_str}

Guidelines:
1. Extract only entities that are explicitly mentioned or clearly implied
2. Use meaningful IDs that relate to the entity name (e.g., "john_doe", "acme_corp")
3. Include brief descriptions for entities when possible
4. Only create relationships between extracted entities
5. Assign confidence scores to relationships (0.0-1.0)
6. Focus on factual, verifiable information
7. Avoid creating entities for abstract concepts unless they are clearly defined

Return only valid JSON matching the schema.
        """.strip()
        
        return instructions

    def _create_template_prompt(self, text: str) -> str:
        """
        Create extraction prompt using Jinja2 template.

        Args:
            text: Input text to extract from

        Returns:
            Rendered prompt string
        """
        template_name = self.get_config_value("template_name", "ner.md")

        try:
            # Load and render template
            prompt = load_prompt_template(
                template_name=template_name,
                schema=self.extraction_schema,
                input_text=text,
                entity_types=self.entity_types,
                relation_types=self.relation_types
            )

            logger.debug(f"Created prompt using template: {template_name}")
            return prompt

        except Exception as e:
            logger.warning(f"Failed to load template {template_name}: {e}")
            logger.info("Falling back to traditional prompt creation")

            # Fallback to traditional prompt
            return create_extraction_prompt(
                text=text,
                schema=self.extraction_schema,
                instructions=self._get_extraction_instructions()
            )

    def _create_subgraph_from_extraction(self, chunk: Chunk, extraction: Dict[str, Any]) -> SubGraph:
        """
        Create SubGraph from LLM extraction result.
        
        Args:
            chunk: Source chunk
            extraction: Extraction result dictionary
            
        Returns:
            SubGraph with nodes and edges
        """
        subgraph = SubGraph(source_chunk_id=chunk.id)
        
        # Create nodes from entities
        entity_map = {}  # Map entity ID to node
        
        entities = extraction.get("entities", [])
        for entity_data in entities:
            try:
                node = self._create_node_from_entity(chunk, entity_data)
                subgraph.add_node(node)
                entity_map[entity_data.get("id", "")] = node
            except Exception as e:
                logger.warning(f"Error creating node from entity: {e}")
                continue
        
        # Create edges from relationships
        relationships = extraction.get("relationships", [])
        for relationship_data in relationships:
            try:
                edge = self._create_edge_from_relationship(chunk, relationship_data, entity_map)
                if edge:
                    subgraph.add_edge(edge)
            except Exception as e:
                logger.warning(f"Error creating edge from relationship: {e}")
                continue
        
        # Add extraction metadata
        subgraph.extraction_metadata = {
            "extraction_method": "llm_extractor",
            "llm_provider": self.get_config_value("llm_provider"),
            "model": self.get_config_value("model"),
            "entities_extracted": len(entities),
            "relationships_extracted": len(relationships),
        }
        
        return subgraph
    
    def _create_node_from_entity(self, chunk: Chunk, entity_data: Dict[str, Any]) -> Node:
        """
        Create Node from entity data.
        
        Args:
            chunk: Source chunk
            entity_data: Entity dictionary from LLM
            
        Returns:
            Node object
        """
        entity_id = entity_data.get("id", str(uuid.uuid4()))
        name = entity_data.get("name", "")
        node_type = entity_data.get("type", "Unknown")
        description = entity_data.get("description", "")
        properties = entity_data.get("properties", {})
        
        # Ensure we have required fields
        if not name:
            raise ValueError("Entity name is required")
        
        # Create node
        node = Node(
            id=entity_id,
            name=name,
            node_type=node_type,
            properties=properties
        )
        
        # Add description as property if provided
        if description:
            node.add_property("description", description)
        
        # Add source information
        node.add_source_chunk(chunk.id)
        if chunk.source_file:
            node.add_property("source_file", chunk.source_file)
        if chunk.page_number:
            node.add_property("page_number", chunk.page_number)
        
        return node
    
    def _create_edge_from_relationship(
        self,
        chunk: Chunk,
        relationship_data: Dict[str, Any],
        entity_map: Dict[str, Node]
    ) -> Optional[Edge]:
        """
        Create Edge from relationship data.
        
        Args:
            chunk: Source chunk
            relationship_data: Relationship dictionary from LLM
            entity_map: Map of entity IDs to nodes
            
        Returns:
            Edge object or None if invalid
        """
        source_id = relationship_data.get("source_id", "")
        target_id = relationship_data.get("target_id", "")
        relation_type = relationship_data.get("relation_type", "")
        description = relationship_data.get("description", "")
        confidence = relationship_data.get("confidence", 0.8)
        
        # Validate required fields
        if not all([source_id, target_id, relation_type]):
            logger.warning("Missing required relationship fields")
            return None
        
        # Check that both entities exist
        if source_id not in entity_map or target_id not in entity_map:
            logger.warning(f"Relationship references unknown entities: {source_id} -> {target_id}")
            return None
        
        # Create edge
        edge_id = f"{source_id}_{relation_type}_{target_id}"
        
        edge = Edge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence
        )
        
        # Add description as property if provided
        if description:
            edge.add_property("description", description)
        
        # Add source information
        edge.add_source_chunk(chunk.id)
        
        return edge
    
    def _merge_subgraphs(self, subgraphs: List[SubGraph]) -> List[SubGraph]:
        """
        Merge subgraphs to resolve duplicate entities and relationships.
        
        Args:
            subgraphs: List of subgraphs to merge
            
        Returns:
            List of merged subgraphs
        """
        if len(subgraphs) <= 1:
            return subgraphs
        
        # For now, implement simple deduplication
        # More sophisticated entity resolution could be added later
        
        merged_nodes: Dict[str, Node] = {}  # name -> node
        merged_edges: Dict[str, Edge] = {}  # edge_key -> edge
        merged_subgraphs = []
        
        for subgraph in subgraphs:
            # Merge nodes (simple name-based deduplication)
            for node in subgraph.nodes:
                node_key = f"{node.node_type}:{node.name.lower()}"
                
                if node_key in merged_nodes:
                    # Merge source chunks
                    existing_node = merged_nodes[node_key]
                    for chunk_id in node.source_chunks:
                        existing_node.add_source_chunk(chunk_id)
                else:
                    merged_nodes[node_key] = node
            
            # Merge edges
            for edge in subgraph.edges:
                edge_key = f"{edge.source_id}:{edge.relation_type}:{edge.target_id}"
                
                if edge_key in merged_edges:
                    # Merge source chunks
                    existing_edge = merged_edges[edge_key]
                    for chunk_id in edge.source_chunks:
                        existing_edge.add_source_chunk(chunk_id)
                else:
                    merged_edges[edge_key] = edge
        
        # Create final merged subgraph
        if merged_nodes or merged_edges:
            final_subgraph = SubGraph(
                nodes=list(merged_nodes.values()),
                edges=list(merged_edges.values())
            )
            merged_subgraphs.append(final_subgraph)
        
        return merged_subgraphs


@register_component(
    "extractor",
    "regex_extractor",
    description="Extracts entities using regular expression patterns",
    config_schema={
        "type": "object",
        "properties": {
            "patterns": {
                "type": "object",
                "description": "Entity type to regex pattern mapping",
                "default": {
                    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                    "url": r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?'
                }
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether pattern matching is case sensitive",
                "default": False
            }
        }
    }
)
class RegexExtractor(Extractor):
    """
    Extractor that uses regular expressions to find entities in text.
    
    Useful for extracting structured information like emails, phone numbers,
    URLs, dates, and other pattern-based entities.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Extract entities using regex patterns.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with extracted subgraphs
        """
        chunks = state.get("split_chunks", state.get("chunks", []))
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")
        
        patterns = self.get_config_value("patterns", {})
        case_sensitive = self.get_config_value("case_sensitive", False)
        
        subgraphs = []
        
        for chunk in chunks:
            try:
                subgraph = self._extract_with_regex(chunk, patterns, case_sensitive)
                if not subgraph.is_empty():
                    subgraphs.append(subgraph)
            except Exception as e:
                logger.error(f"Error extracting with regex from chunk {chunk.id}: {e}")
                continue
        
        logger.info(f"Extracted {len(subgraphs)} subgraphs using regex patterns")
        
        # Update state
        updated_state = state.copy()
        updated_state["subgraphs"] = subgraphs
        
        return updated_state
    
    def _extract_with_regex(
        self,
        chunk: Chunk,
        patterns: Dict[str, str],
        case_sensitive: bool
    ) -> SubGraph:
        """
        Extract entities from chunk using regex patterns.
        
        Args:
            chunk: Chunk to extract from
            patterns: Entity type to pattern mapping
            case_sensitive: Whether matching is case sensitive
            
        Returns:
            SubGraph with extracted entities
        """
        text = chunk.content
        subgraph = SubGraph(source_chunk_id=chunk.id)
        
        for entity_type, pattern in patterns.items():
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                matches = re.finditer(pattern, text, flags)
                
                for match in matches:
                    entity_value = match.group().strip()
                    if entity_value:
                        # Create entity node
                        entity_id = f"{entity_type}_{hash(entity_value) % 10000}"
                        
                        node = Node(
                            id=entity_id,
                            name=entity_value,
                            node_type=entity_type.title(),
                            properties={
                                "pattern": pattern,
                                "match_start": match.start(),
                                "match_end": match.end()
                            }
                        )
                        
                        node.add_source_chunk(chunk.id)
                        subgraph.add_node(node)
                        
            except re.error as e:
                logger.warning(f"Invalid regex pattern for {entity_type}: {e}")
                continue
        
        return subgraph


@register_component(
    "extractor",
    "keyword_extractor",
    description="Extracts predefined keywords and phrases as entities",
    config_schema={
        "type": "object",
        "properties": {
            "keywords": {
                "type": "object",
                "description": "Entity type to keyword list mapping",
                "default": {}
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether keyword matching is case sensitive",
                "default": False
            },
            "word_boundaries": {
                "type": "boolean", 
                "description": "Whether to require word boundaries around matches",
                "default": True
            }
        }
    }
)
class KeywordExtractor(Extractor):
    """
    Extractor that finds predefined keywords and phrases in text.
    
    Useful for domain-specific entity extraction where you know
    the specific terms you're looking for.
    """
    
    def process(self, state: PipelineState) -> PipelineState:
        """
        Extract entities using keyword matching.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with extracted subgraphs
        """
        chunks = state.get("split_chunks", state.get("chunks", []))
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")
        
        keywords = self.get_config_value("keywords", {})
        case_sensitive = self.get_config_value("case_sensitive", False)
        word_boundaries = self.get_config_value("word_boundaries", True)
        
        subgraphs = []
        
        for chunk in chunks:
            try:
                subgraph = self._extract_keywords(chunk, keywords, case_sensitive, word_boundaries)
                if not subgraph.is_empty():
                    subgraphs.append(subgraph)
            except Exception as e:
                logger.error(f"Error extracting keywords from chunk {chunk.id}: {e}")
                continue
        
        logger.info(f"Extracted {len(subgraphs)} subgraphs using keyword matching")
        
        # Update state
        updated_state = state.copy()
        updated_state["subgraphs"] = subgraphs
        
        return updated_state
    
    def _extract_keywords(
        self,
        chunk: Chunk,
        keywords: Dict[str, List[str]],
        case_sensitive: bool,
        word_boundaries: bool
    ) -> SubGraph:
        """
        Extract keywords from chunk text.
        
        Args:
            chunk: Chunk to extract from
            keywords: Entity type to keyword list mapping
            case_sensitive: Whether matching is case sensitive
            word_boundaries: Whether to use word boundaries
            
        Returns:
            SubGraph with found keywords as entities
        """
        text = chunk.content
        subgraph = SubGraph(source_chunk_id=chunk.id)
        
        for entity_type, keyword_list in keywords.items():
            for keyword in keyword_list:
                # Build regex pattern
                if word_boundaries:
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                else:
                    pattern = re.escape(keyword)
                
                flags = 0 if case_sensitive else re.IGNORECASE
                
                try:
                    matches = re.finditer(pattern, text, flags)
                    
                    for match in matches:
                        # Create entity node
                        entity_id = f"{entity_type}_{keyword}_{hash(keyword) % 10000}"
                        
                        node = Node(
                            id=entity_id,
                            name=keyword,
                            node_type=entity_type.title(),
                            properties={
                                "keyword": keyword,
                                "match_start": match.start(),
                                "match_end": match.end()
                            }
                        )
                        
                        node.add_source_chunk(chunk.id)
                        subgraph.add_node(node)
                        
                except re.error as e:
                    logger.warning(f"Error in keyword pattern '{keyword}': {e}")
                    continue
        
        return subgraph