"""
Extractor components for KAG-LangGraph pipeline.

This module contains extractor implementations that extract structured knowledge
(entities, relationships) from text chunks using LLMs and other techniques.
"""

import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Set, Tuple, Union
import re

# Set logger level for this module to DEBUG temporarily
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from .base import Extractor
from ..models.chunk import Chunk
from ..models.graph import SubGraph, Node, Edge
from ..models.pipeline_state import PipelineState
from ..utils.registry import register_component
from ..utils.llm_client import LLMClient, create_llm_client, LLMMessage, extract_json_from_response, create_extraction_prompt
from ..utils.template_loader import load_prompt_template, get_template_loader


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
            "base_url": {
                "type": "string",
                "description": "Optional base URL for OpenAI-compatible API endpoints"
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
        base_url = self.get_config_value("base_url")
        temperature = self.get_config_value("temperature", 0.1)
        max_tokens = self.get_config_value("max_tokens", 2000)

        # Create LLM client
        try:
            client_kwargs = {
                "provider": llm_provider,
                "model": model,
                "api_key": api_key,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Add base_url if provided
            if base_url:
                client_kwargs["base_url"] = base_url
                # Add default headers to help bypass Cloudflare protection
                client_kwargs["default_headers"] = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9"
                }

            self.llm_client = create_llm_client(**client_kwargs)
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
                # Skip empty or whitespace-only chunks
                if not chunk.content or not chunk.content.strip():
                    logger.debug(f"Skipping empty chunk {chunk.id}")
                    continue

                # Skip chunks that are too short to contain meaningful information
                min_chunk_length = self.get_config_value("min_chunk_length", 10)
                if len(chunk.content.strip()) < min_chunk_length:
                    logger.debug(f"Skipping chunk {chunk.id} - too short ({len(chunk.content)} chars)")
                    continue

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
        prompt = None

        # Debug logging for chunk content
        logger.debug(f"Processing chunk {chunk.id}")
        logger.debug(f"Chunk content length: {len(text)} characters")
        logger.debug(f"Chunk content preview: {text[:200]}..." if len(text) > 200 else f"Chunk content: {text}")

        # Create extraction prompt - use template if configured
        use_template = self.get_config_value("use_template", False)
        logger.debug(f"Use template: {use_template}")

        if use_template:
            ner = self._create_template_prompt("ner.md", text, None)
        else:
            # Use traditional prompt creation
            prompt = create_extraction_prompt(
                text=text,
                schema=self.extraction_schema,
                instructions=self._get_extraction_instructions()
            )
        
        # Call LLM
        try:
            if prompt:
                response = self.llm_client.simple_chat(prompt)
                extraction_result = extract_json_from_response(response)

                if not extraction_result:
                    logger.warning(f"No valid JSON found in LLM response for chunk {chunk.id}")
                    return SubGraph(source_chunk_id=chunk.id)

                subgraph = self._create_subgraph_from_extraction(chunk, extraction_result, extraction_result)
                return subgraph
            else:
                # Step 1: Extract NER (Named Entity Recognition)
                logger.debug(f"Starting NER extraction for chunk {chunk.id}")
                response_ner = self.llm_client.simple_chat(ner)
                extraction_ner = extract_json_from_response(response_ner)

                # Validate NER results before proceeding
                if not extraction_ner or not self._has_valid_entities(extraction_ner):
                    logger.warning(f"No valid entities found in NER step for chunk {chunk.id}")
                    return SubGraph(source_chunk_id=chunk.id)

                # Count entities (handle both array and dict formats)
                entity_count = len(extraction_ner) if isinstance(extraction_ner, list) else len(extraction_ner.get('entities', []))
                logger.debug(f"NER extraction successful for chunk {chunk.id}, found {entity_count} entities")

                # Normalize extraction_ner to dict format for STD/TRP templates
                # Templates expect: {"entities": [...]}
                if isinstance(extraction_ner, list):
                    normalized_ner = {"entities": extraction_ner}
                else:
                    normalized_ner = extraction_ner

                # Step 2: Extract STD (standardize entities with official names)
                logger.debug(f"Starting STD extraction for chunk {chunk.id}")

                # Create prompt for STD
                # STD expects: {"entities": [...]}
                std = self._create_template_prompt("std.md", text, normalized_ner)

                # Execute STD extraction
                response_std = self.llm_client.simple_chat(std)

                # Process STD results
                extraction_std = extract_json_from_response(response_std)
                if not extraction_std or not self._has_valid_entities(extraction_std):
                    logger.warning(f"STD extraction failed for chunk {chunk.id}, using NER results")
                    extraction_std = normalized_ner  # Fallback to normalized NER results
                else:
                    logger.debug(f"STD extraction completed for chunk {chunk.id}")
                    # Normalize STD results if they're in array format
                    if isinstance(extraction_std, list):
                        extraction_std = {"entities": extraction_std}

                # Step 3: Extract TRP (relationships using STD entities with official names)
                logger.debug(f"Starting TRP extraction for chunk {chunk.id}")

                # TRP should use STD entities (which have official_name) instead of NER entities
                # This ensures relationship IDs match the entity_map built from STD results
                trp = self._create_template_prompt("trp.md", text, extraction_std)

                # Execute TRP extraction
                response_trp = self.llm_client.simple_chat(trp)

                # Process TRP results
                extraction_trp = extract_json_from_response(response_trp)
                if not extraction_trp:
                    logger.warning(f"Triple extraction failed for chunk {chunk.id}, using empty relationships")
                    extraction_trp = {"relationships": []}
                else:
                    # Normalize TRP results if they're in array format
                    if isinstance(extraction_trp, list):
                        extraction_trp = {"relationships": extraction_trp}

                    relationship_count = len(extraction_trp.get('relationships', []))
                    logger.debug(f"Triple extraction completed for chunk {chunk.id}, found {relationship_count} relationships")

                # Convert to SubGraph using validated results
                subgraph = self._create_subgraph_from_extraction(chunk, extraction_std, extraction_trp)
                return subgraph
            
        except Exception as e:
            logger.error(f"Error calling LLM for chunk {chunk.id}: {e}")
            return SubGraph(source_chunk_id=chunk.id)
    
    def _build_extraction_schema(self, custom_schema: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build the extraction schema for the LLM.

        Args:
            custom_schema: Custom schema to merge - can be:
                - String path to .schema file (e.g., "path/to/schema.schema")
                - Dictionary with custom schema structure
                - Empty dict for default schema only

        Returns:
            Complete extraction schema dictionary
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
        
        # Process custom schema
        if custom_schema:
            # Check if it's a domain schema file path
            if isinstance(custom_schema, str) and custom_schema.endswith('.schema'):
                parsed_schema = self._parse_domain_schema_file(custom_schema)
                if parsed_schema and "entities" in parsed_schema:
                    logger.info("Using domain schema from file - returning complete parsed schema")
                    return parsed_schema
                else:
                    logger.warning("Failed to parse domain schema file, using default schema")
            elif isinstance(custom_schema, str):
                # Assume it's domain schema content
                parsed_schema = self._parse_domain_schema_content(custom_schema)
                if parsed_schema and "entities" in parsed_schema:
                    logger.info("Using domain schema content - returning complete parsed schema")
                    return parsed_schema
                else:
                    logger.warning("Failed to parse domain schema content, using default schema")

            # Handle dictionary custom schemas (JSON schema format)
            if isinstance(custom_schema, dict):
                # Check if this is a complete JSON schema replacement
                if self._is_complete_json_schema(custom_schema):
                    logger.info("Using complete JSON schema - replacing default schema")
                    return custom_schema
                else:
                    # Partial schema - merge with default
                    logger.info("Merging partial custom schema with default schema")
                    default_schema.update(custom_schema)

        return default_schema

    def _is_complete_json_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Check if the provided schema is a complete JSON schema.

        Args:
            schema: Schema dictionary to check

        Returns:
            True if this is a complete JSON schema, False if partial
        """
        # Check if it's a JSON schema format
        if (schema.get("type") == "object" and
            "properties" in schema and
            "entities" in schema["properties"] and
            "relationships" in schema["properties"]):
            return True

        # Check if it's a simplified format with direct entities/relationships
        if "entities" in schema and "relationships" in schema:
            return True

        # Check if it contains schema-level configuration that suggests complete replacement
        if any(key in schema for key in ["type", "required", "properties", "$schema"]):
            return True

        return False

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
        Parse domain schema content and return the complete schema structure.

        Args:
            content: Schema content string from .schema file

        Returns:
            Complete schema structure to be used directly by the LLM
        """
        try:
            schema = {
                "namespace": None,
                "entities": {},
                "relations": {},
                "entity_types": [],
                "relation_types": []
            }

            lines = content.strip().split('\n')
            current_entity = None
            current_section = None

            for line in lines:
                original_line = line
                line = line.strip()

                if not line:
                    continue

                # Parse namespace
                if line.startswith('namespace '):
                    schema["namespace"] = line.replace('namespace ', '').strip()
                    continue

                # Parse entity definitions
                if line.endswith(': EntityType') or line.endswith(': ConceptType'):
                    entity_name = line.split(':')[0].strip()
                    entity_type = line.split(':')[1].strip()

                    current_entity = entity_name
                    schema["entities"][entity_name] = {
                        "type": entity_type,
                        "properties": {},
                        "relations": {}
                    }
                    schema["entity_types"].append(entity_name)
                    current_section = None
                    continue

                # Parse sections within entities
                if current_entity and line in ['properties:', 'relations:']:
                    current_section = line.replace(':', '')
                    continue

                # Parse properties and relations
                if current_entity and current_section and original_line.startswith('\t'):
                    if current_section == 'properties':
                        self._parse_property_line(line, schema["entities"][current_entity]["properties"])
                    elif current_section == 'relations':
                        relation_info = self._parse_relation_line(line, schema["entities"][current_entity]["relations"])
                        if relation_info and relation_info["relation_name"] not in schema["relation_types"]:
                            schema["relation_types"].append(relation_info["relation_name"])

            # Update instance variables
            self.entity_types = schema["entity_types"]
            self.relation_types = schema["relation_types"]

            logger.info(f"Parsed domain schema with {len(schema['entities'])} entities and {len(schema['relation_types'])} relation types")
            logger.debug(f"Entity types: {schema['entity_types']}")
            logger.debug(f"Relation types: {schema['relation_types']}")

            return schema

        except Exception as e:
            logger.error(f"Failed to parse domain schema content: {e}")
            return {}

    def _parse_property_line(self, line: str, properties: Dict[str, Any]) -> None:
        """Parse a property line from the schema."""
        try:
            if ':' in line:
                parts = line.split(':', 1)
                prop_name = parts[0].strip()
                prop_type = parts[1].strip() if len(parts) > 1 else "Text"

                properties[prop_name] = {
                    "type": prop_type,
                    "index": None
                }
            elif 'index:' in line:
                # Handle index specification for previous property
                index_type = line.replace('index:', '').strip()
                # Find the last property and update its index
                if properties:
                    last_prop = list(properties.keys())[-1]
                    properties[last_prop]["index"] = index_type
        except Exception as e:
            logger.debug(f"Error parsing property line '{line}': {e}")

    def _parse_relation_line(self, line: str, relations: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a relation line from the schema."""
        try:
            if ':' in line:
                parts = line.split(':', 1)
                relation_name = parts[0].strip()
                target_entity = parts[1].strip() if len(parts) > 1 else ""

                relations[relation_name] = {
                    "target_entity": target_entity,
                    "constraint": None,
                    "properties": {},
                    "rule": None
                }

                return {"relation_name": relation_name, "target_entity": target_entity}
            elif 'constraint:' in line:
                # Handle constraint specification
                constraint = line.replace('constraint:', '').strip()
                if relations:
                    last_relation = list(relations.keys())[-1]
                    relations[last_relation]["constraint"] = constraint
            elif 'rule:' in line:
                # Handle rule specification (for complex relations)
                rule = line.replace('rule:', '').strip()
                if relations:
                    last_relation = list(relations.keys())[-1]
                    relations[last_relation]["rule"] = rule
        except Exception as e:
            logger.debug(f"Error parsing relation line '{line}': {e}")

        return None

    def _has_valid_entities(self, extraction_result: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bool:
        """
        Check if extraction result contains valid entities.

        Args:
            extraction_result: Result from LLM extraction (dict with "entities" key OR array of entities)

        Returns:
            True if result contains valid entities, False otherwise
        """
        # Handle array format: [{...}, {...}]
        if isinstance(extraction_result, list):
            if len(extraction_result) == 0:
                return False
            # Check if at least one entity has required fields
            for entity in extraction_result:
                if isinstance(entity, dict) and "name" in entity and entity.get("name", "").strip():
                    return True
            return False

        # Handle dict format: {"entities": [{...}, {...}]}
        if isinstance(extraction_result, dict):
            entities = extraction_result.get("entities", [])
            if not isinstance(entities, list) or len(entities) == 0:
                return False

            # Check if at least one entity has required fields
            for entity in entities:
                if isinstance(entity, dict) and "name" in entity and entity.get("name", "").strip():
                    return True
            return False

        # Invalid format
        return False

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

    def _create_template_prompt(self, template_name: str, text: str, named_entities: Optional[dict]) -> str:
        """
        Create extraction prompt using Jinja2 template.

        Args:
            text: Input text to extract from

        Returns:
            Rendered prompt string
        """

        try:
            # Debug logging
            logger.debug(f"Creating template prompt: {template_name}")
            logger.debug(f"Input text length: {len(text)} characters")
            logger.debug(f"Input text preview: {text[:200]}..." if len(text) > 200 else f"Input text: {text}")
            logger.debug(f"Named entities: {named_entities}")

            # Load and render template
            prompt = load_prompt_template(
                template_name=template_name,
                schema=self.extraction_schema,
                input_text=text,
                named_entities=named_entities,
            )

            logger.debug(f"Template {template_name} rendered successfully")
            logger.debug(f"Rendered prompt length: {len(prompt)} characters")
            logger.debug(f"Rendered prompt preview: {prompt[:500]}..." if len(prompt) > 500 else f"Rendered prompt: {prompt}")

            return prompt

        except Exception as e:
            logger.warning(f"Failed to load template {template_name}: {e}")
            logger.info("Falling back to traditional prompt creation")

            # Fallback to traditional prompt
            fallback_prompt = create_extraction_prompt(
                text=text,
                schema=self.extraction_schema,
                instructions=self._get_extraction_instructions()
            )

            logger.debug(f"Fallback prompt length: {len(fallback_prompt)} characters")
            return fallback_prompt

    def _create_subgraph_from_extraction(self, chunk: Chunk, extraction_std: Optional[Dict[str, Any]], extraction_trp: Optional[Dict[str, Any]]) -> SubGraph:
        """
        Create SubGraph from LLM extraction result.

        Args:
            chunk: Source chunk
            extraction_std: Standardized entities from STD extraction step (contains "entities" array)
            extraction_trp: Relationships from Triple extraction step (contains "relationships" array)

        Returns:
            SubGraph with nodes and edges
        """
        subgraph = SubGraph(source_chunk_id=chunk.id)
        
        # Create nodes from entities
        entity_map = {}  # Map entity ID to node

        entities = extraction_std.get("entities", [])
        for entity_data in entities:
            try:
                node = self._create_node_from_entity(chunk, entity_data)
                subgraph.add_node(node)
                entity_id = entity_data.get("id", "")
                entity_map[entity_id] = node
                logger.debug(f"Added entity to map: id='{entity_id}', name='{entity_data.get('name')}'")
            except Exception as e:
                logger.warning(f"Error creating node from entity: {e}")
                continue

        logger.debug(f"Entity map has {len(entity_map)} entities: {list(entity_map.keys())}")
        
        # Create edges from relationships
        relationships = extraction_trp.get("relationships", [])
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
        label = entity_data.get("category", "Unknown")
        official_name = entity_data.get("official_name", "")
        description = entity_data.get("description", "")
        properties = entity_data.get("properties", "")

        # Ensure we have required fields
        if not name:
            raise ValueError("Entity name is required")

        # Create node
        node = Node(
            id=entity_id,
            name=name,
            label=label,
            official_name=official_name if official_name else name
        )

        # Add description as property if provided
        if description:
            node.add_property("description", description)

        # Add properties as properties if provided
        if properties:
            node.add_property("properties", properties)

        # Add source information
        node.add_source_chunk(chunk.id)
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

        Handles three types of relationships:
        1. isA (taxonomy): EntityType -> ConceptType
        2. Schema-defined: Relationships from schema's relations section
        3. On-the-fly: Discovered relationships not in schema

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

        # Extract SPG edge properties from relationship_data
        edge_properties = relationship_data.get("properties", {})
        if edge_properties and isinstance(edge_properties, dict):
            # Add all SPG edge properties (financial data, temporal info, etc.)
            edge.add_properties(edge_properties)
            logger.debug(f"Added {len(edge_properties)} SPG edge properties to {relation_type}")

        # Determine relationship category based on relation_type and confidence
        # Priority 1a: isA relationships (Entity -> ConceptType taxonomy)
        if relation_type == "isA":
            edge.add_property("relationship_category", "taxonomy")
            edge.add_property("is_taxonomy", True)
        # Priority 1b: belongTo relationships (ConceptType -> ConceptType hierarchy)
        elif relation_type == "belongTo":
            edge.add_property("relationship_category", "concept_hierarchy")
            edge.add_property("is_hierarchy", True)
        # Priority 2: Schema-defined (inferred from higher confidence and common schema patterns)
        # Priority 3: On-the-fly (typically lower confidence)
        elif confidence >= 0.7:
            edge.add_property("relationship_category", "schema_defined")
        else:
            edge.add_property("relationship_category", "discovered")

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
                node_key = f"{node.label}:{node.name.lower()}"

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
                            label=entity_type.title(),
                            official_name=entity_value,
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
                            label=entity_type.title(),
                            official_name=keyword,
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