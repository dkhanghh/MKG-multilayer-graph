"""
Extractor components for KAG-LangGraph pipeline.

This module contains extractor implementations that extract structured knowledge
(entities, relationships) from text chunks using LLMs and other techniques.
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from .base import Extractor
from .extraction import MultiStepExtractionStrategy, SubGraphBuilder
from ..models.chunk import Chunk
from ..models.graph import SubGraph, Node, Edge
from ..models.pipeline_state import PipelineState
from ..models.schema import DomainSchema
from ..utils.registry import register_component
from ..utils.llm_client import (
    LLMClient,
    create_llm_client,
    LLMMessage,
    extract_json_from_response,
    create_extraction_prompt,
)
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
                "default": "openai",
            },
            "model": {
                "type": "string",
                "description": "Model name to use",
                "default": "gpt-3.5-turbo",
            },
            "api_key": {
                "type": "string",
                "description": "API key for the LLM provider",
            },
            "base_url": {
                "type": "string",
                "description": "Optional base URL for OpenAI-compatible API endpoints",
            },
            "temperature": {
                "type": "number",
                "description": "Temperature for LLM generation",
                "default": 0.1,
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens for LLM response",
                "default": 2000,
            },
            "entity_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Types of entities to extract",
                "default": ["Person", "Organization", "Location", "Concept"],
            },
            "relation_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Types of relationships to extract",
                "default": ["works_for", "located_in", "related_to", "part_of"],
            },
            "extraction_schema": {
                "type": "object",
                "description": "Custom extraction schema",
                "default": {},
            },
            "batch_size": {
                "type": "integer",
                "description": "Number of chunks to process in parallel",
                "default": 5,
            },
            "use_template": {
                "type": "boolean",
                "description": "Whether to use Jinja2 templates for prompts",
                "default": False,
            },
            "template_name": {
                "type": "string",
                "description": "Name of the template file to use (e.g., 'ner.md')",
                "default": "ner.md",
            },
        },
    },
)
class LLMExtractor(Extractor):
    """Extractor that uses Large Language Models to extract structured knowledge.

    When ``use_template`` is enabled the extractor delegates to
    :class:`MultiStepExtractionStrategy` (NER -> STD -> TRP).  Otherwise a
    legacy single-prompt path is used with :class:`SubGraphBuilder` for graph
    assembly.
    """

    def __init__(self, config):
        """Initialize LLM extractor."""
        super().__init__(config)

        # ----- LLM client -----
        llm_provider = self.get_config_value("llm_provider", "openai")
        model = self.get_config_value("model", "gpt-3.5-turbo")
        api_key = self.get_config_value("api_key")
        base_url = self.get_config_value("base_url")
        temperature = self.get_config_value("temperature", 0.1)
        max_tokens = self.get_config_value("max_tokens", 2000)

        try:
            client_kwargs: Dict[str, Any] = {
                "provider": llm_provider,
                "model": model,
                "api_key": api_key,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if base_url:
                client_kwargs["base_url"] = base_url
                client_kwargs["default_headers"] = {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36"
                    ),
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            self.llm_client = create_llm_client(**client_kwargs)
        except Exception as e:
            logger.error("Failed to initialize LLM client: %s", e)
            raise

        # ----- extraction schema -----
        self.entity_types = self.get_config_value(
            "entity_types", ["Person", "Organization", "Location", "Concept"]
        )
        self.relation_types = self.get_config_value(
            "relation_types", ["works_for", "located_in", "related_to", "part_of"]
        )

        custom_schema = self.get_config_value("extraction_schema", {})
        self.domain_schema: Optional[DomainSchema] = None

        if isinstance(custom_schema, str) and (
            custom_schema.endswith(".schema")
            or custom_schema.endswith(".yaml")
            or custom_schema.endswith(".yml")
        ):
            try:
                self.domain_schema = DomainSchema.from_file(custom_schema)
                self.entity_types = self.domain_schema.entity_type_names
                self.relation_types = self.domain_schema.relation_type_names
                self.extraction_schema = self.domain_schema.to_extraction_schema()
                logger.info(
                    "Loaded domain schema from %s — %d entities, %d relation types",
                    custom_schema,
                    len(self.domain_schema.entities),
                    len(self.relation_types),
                )
            except Exception as exc:
                logger.error(
                    "Failed to load domain schema from %s: %s", custom_schema, exc
                )
                logger.warning("Falling back to default extraction schema")
                self.extraction_schema = self._build_extraction_schema({})
        else:
            self.extraction_schema = self._build_extraction_schema(custom_schema)

        # ----- composable extraction components -----
        extraction_metadata = {
            "extraction_method": "llm_extractor",
            "llm_provider": self.get_config_value("llm_provider"),
            "model": self.get_config_value("model"),
        }
        self.subgraph_builder = SubGraphBuilder(extraction_metadata)

        use_template = self.get_config_value("use_template", False)
        if use_template:
            self.strategy: Optional[MultiStepExtractionStrategy] = (
                MultiStepExtractionStrategy(
                    llm_client=self.llm_client,
                    extraction_schema=self.extraction_schema,
                    subgraph_builder=self.subgraph_builder,
                )
            )
        else:
            self.strategy = None  # legacy direct extraction

        logger.info("Initialized LLM extractor with %s %s", llm_provider, model)

    # ------------------------------------------------------------------
    # Pipeline entry point
    # ------------------------------------------------------------------

    def process(self, state: PipelineState) -> PipelineState:
        """Extract knowledge from text chunks using LLM.

        Args:
            state: Current pipeline state.

        Returns:
            Updated pipeline state with extracted subgraphs.
        """
        chunks = state.get("split_chunks", state.get("chunks", []))
        if not chunks:
            raise ValueError("No chunks provided in pipeline state")

        batch_size = self.get_config_value("batch_size", 5)
        max_failure_rate = self.get_config_value("max_failure_rate", 0.5)

        subgraphs: List[SubGraph] = []
        all_failed_items: List[Dict[str, Any]] = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            try:
                batch_subgraphs, batch_failures = self._process_chunk_batch(batch)
                subgraphs.extend(batch_subgraphs)
                all_failed_items.extend(batch_failures)
            except Exception as e:
                logger.error(
                    "Error processing chunk batch %d: %s", i // batch_size + 1, e
                )
                for chunk in batch:
                    all_failed_items.append({"chunk_id": chunk.id, "error": str(e)})
                continue

        total_chunks = len(chunks)
        failed_count = len(all_failed_items)
        failure_rate = failed_count / total_chunks if total_chunks > 0 else 0.0

        if failed_count > 0:
            logger.warning(
                "Extraction failures: %d/%d chunks failed (%.1f%% failure rate)",
                failed_count,
                total_chunks,
                failure_rate * 100,
            )

        if failure_rate > max_failure_rate:
            raise RuntimeError(
                f"Extraction failure rate {failure_rate:.1%} exceeds maximum allowed "
                f"{max_failure_rate:.1%} ({failed_count}/{total_chunks} chunks failed). "
                f"Halting pipeline."
            )

        logger.info(
            "Extracted knowledge from %d chunks, created %d subgraphs, %d chunk(s) failed",
            len(chunks),
            len(subgraphs),
            failed_count,
        )

        merged_subgraphs = self.subgraph_builder.merge_subgraphs(subgraphs)

        updated_state = state.copy()
        updated_state["subgraphs"] = merged_subgraphs

        metadata = dict(updated_state.get("metadata", {}) or {})
        metadata["failed_items"] = all_failed_items
        metadata["extraction_failure_rate"] = failure_rate
        metadata["extraction_failed_count"] = failed_count
        metadata["extraction_total_chunks"] = total_chunks
        updated_state["metadata"] = metadata

        return updated_state

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def _process_chunk_batch(
        self, chunks: List[Chunk]
    ) -> Tuple[List[SubGraph], List[Dict[str, Any]]]:
        """Process a batch of chunks.

        Args:
            chunks: List of chunks to process.

        Returns:
            Tuple of (extracted subgraphs, list of failure records).
        """
        subgraphs: List[SubGraph] = []
        failures: List[Dict[str, Any]] = []

        for chunk in chunks:
            try:
                if not chunk.content or not chunk.content.strip():
                    logger.debug("Skipping empty chunk %s", chunk.id)
                    continue

                min_chunk_length = self.get_config_value("min_chunk_length", 10)
                if len(chunk.content.strip()) < min_chunk_length:
                    logger.debug(
                        "Skipping chunk %s - too short (%d chars)",
                        chunk.id,
                        len(chunk.content),
                    )
                    continue

                subgraph = self._extract_from_chunk(chunk)
                if not subgraph.is_empty():
                    subgraphs.append(subgraph)
            except Exception as e:
                logger.error("Error extracting from chunk %s: %s", chunk.id, e)
                failures.append({"chunk_id": chunk.id, "error": str(e)})
                continue

        return subgraphs, failures

    # ------------------------------------------------------------------
    # Single-chunk extraction (delegates to strategy or legacy path)
    # ------------------------------------------------------------------

    def _extract_from_chunk(self, chunk: Chunk) -> SubGraph:
        """Extract knowledge from a single chunk.

        When a :class:`MultiStepExtractionStrategy` is configured the work is
        fully delegated.  Otherwise the legacy single-prompt path is used.

        Args:
            chunk: Chunk to extract from.

        Returns:
            SubGraph with extracted knowledge.
        """
        if self.strategy:
            return self.strategy.extract(chunk)

        # Legacy single-prompt path
        text = chunk.content
        logger.debug("Processing chunk %s (legacy path)", chunk.id)

        prompt = create_extraction_prompt(
            text=text,
            schema=self.extraction_schema,
            instructions=self._get_extraction_instructions(),
        )

        try:
            response = self.llm_client.simple_chat(prompt)
            extraction_result = extract_json_from_response(response)

            if not extraction_result:
                logger.warning(
                    "No valid JSON found in LLM response for chunk %s", chunk.id
                )
                return SubGraph(source_chunk_id=chunk.id)

            # Normalise: the legacy prompt returns entities + relationships in one dict
            if isinstance(extraction_result, list):
                extraction_result = {"entities": extraction_result, "relationships": []}
            entities_data = extraction_result
            relationships_data = extraction_result

            return self.subgraph_builder.build_from_extraction(
                chunk, entities_data, relationships_data
            )
        except Exception as e:
            logger.error("Error calling LLM for chunk %s: %s", chunk.id, e)
            return SubGraph(source_chunk_id=chunk.id)

    # ------------------------------------------------------------------
    # Schema helpers (kept in LLMExtractor)
    # ------------------------------------------------------------------

    def _build_extraction_schema(
        self, custom_schema: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build the extraction schema for the LLM from a dict-based schema.

        This method handles dictionary and inline-string schemas only.
        File-based schemas (.schema, .yaml) are handled in ``__init__`` via
        ``DomainSchema.from_file()`` before this method is ever called.

        Args:
            custom_schema: Custom schema dict (or empty dict for defaults).

        Returns:
            Complete extraction schema dictionary.
        """
        default_schema: Dict[str, Any] = {
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
                            "properties": {"type": "object"},
                        },
                        "required": ["id", "name", "type"],
                    },
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string"},
                            "target_id": {"type": "string"},
                            "relation_type": {
                                "type": "string",
                                "enum": self.relation_types,
                            },
                            "description": {"type": "string"},
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                        },
                        "required": ["source_id", "target_id", "relation_type"],
                    },
                },
            },
            "required": ["entities", "relationships"],
        }

        if custom_schema and isinstance(custom_schema, dict):
            if self._is_complete_json_schema(custom_schema):
                logger.info("Using complete JSON schema — replacing default schema")
                return custom_schema
            else:
                logger.info("Merging partial custom schema with default schema")
                default_schema.update(custom_schema)

        return default_schema

    def _is_complete_json_schema(self, schema: Dict[str, Any]) -> bool:
        """Check if the provided dict is a complete JSON schema."""
        if (
            schema.get("type") == "object"
            and "properties" in schema
            and "entities" in schema["properties"]
            and "relationships" in schema["properties"]
        ):
            return True
        if "entities" in schema and "relationships" in schema:
            return True
        if any(key in schema for key in ["type", "required", "properties", "$schema"]):
            return True
        return False

    def _get_extraction_instructions(self) -> str:
        """Get instructions for the extraction task (legacy path only).

        Returns:
            Instruction string for the LLM.
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
                    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    "phone": r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
                    "url": r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?",
                },
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether pattern matching is case sensitive",
                "default": False,
            },
        },
    },
)
class RegexExtractor(Extractor):
    """Extractor that uses regular expressions to find entities in text.

    Useful for extracting structured information like emails, phone numbers,
    URLs, dates, and other pattern-based entities.
    """

    def process(self, state: PipelineState) -> PipelineState:
        """Extract entities using regex patterns.

        Args:
            state: Current pipeline state.

        Returns:
            Updated pipeline state with extracted subgraphs.
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
                logger.error(
                    "Error extracting with regex from chunk %s: %s", chunk.id, e
                )
                continue

        logger.info("Extracted %d subgraphs using regex patterns", len(subgraphs))

        updated_state = state.copy()
        updated_state["subgraphs"] = subgraphs

        return updated_state

    def _extract_with_regex(
        self,
        chunk: Chunk,
        patterns: Dict[str, str],
        case_sensitive: bool,
    ) -> SubGraph:
        """Extract entities from chunk using regex patterns.

        Args:
            chunk: Chunk to extract from.
            patterns: Entity type to pattern mapping.
            case_sensitive: Whether matching is case sensitive.

        Returns:
            SubGraph with extracted entities.
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
                        entity_id = f"{entity_type}_{hash(entity_value) % 10000}"

                        node = Node(
                            id=entity_id,
                            name=entity_value,
                            label=entity_type.title(),
                            official_name=entity_value,
                            properties={
                                "pattern": pattern,
                                "match_start": match.start(),
                                "match_end": match.end(),
                            },
                        )

                        node.add_source_chunk(chunk.id)
                        subgraph.add_node(node)

            except re.error as e:
                logger.warning("Invalid regex pattern for %s: %s", entity_type, e)
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
                "default": {},
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether keyword matching is case sensitive",
                "default": False,
            },
            "word_boundaries": {
                "type": "boolean",
                "description": "Whether to require word boundaries around matches",
                "default": True,
            },
        },
    },
)
class KeywordExtractor(Extractor):
    """Extractor that finds predefined keywords and phrases in text.

    Useful for domain-specific entity extraction where you know
    the specific terms you're looking for.
    """

    def process(self, state: PipelineState) -> PipelineState:
        """Extract entities using keyword matching.

        Args:
            state: Current pipeline state.

        Returns:
            Updated pipeline state with extracted subgraphs.
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
                subgraph = self._extract_keywords(
                    chunk, keywords, case_sensitive, word_boundaries
                )
                if not subgraph.is_empty():
                    subgraphs.append(subgraph)
            except Exception as e:
                logger.error(
                    "Error extracting keywords from chunk %s: %s", chunk.id, e
                )
                continue

        logger.info("Extracted %d subgraphs using keyword matching", len(subgraphs))

        updated_state = state.copy()
        updated_state["subgraphs"] = subgraphs

        return updated_state

    def _extract_keywords(
        self,
        chunk: Chunk,
        keywords: Dict[str, List[str]],
        case_sensitive: bool,
        word_boundaries: bool,
    ) -> SubGraph:
        """Extract keywords from chunk text.

        Args:
            chunk: Chunk to extract from.
            keywords: Entity type to keyword list mapping.
            case_sensitive: Whether matching is case sensitive.
            word_boundaries: Whether to use word boundaries.

        Returns:
            SubGraph with found keywords as entities.
        """
        text = chunk.content
        subgraph = SubGraph(source_chunk_id=chunk.id)

        for entity_type, keyword_list in keywords.items():
            for keyword in keyword_list:
                if word_boundaries:
                    pattern = r"\b" + re.escape(keyword) + r"\b"
                else:
                    pattern = re.escape(keyword)

                flags = 0 if case_sensitive else re.IGNORECASE

                try:
                    matches = re.finditer(pattern, text, flags)

                    for match in matches:
                        entity_id = (
                            f"{entity_type}_{keyword}_{hash(keyword) % 10000}"
                        )

                        node = Node(
                            id=entity_id,
                            name=keyword,
                            label=entity_type.title(),
                            official_name=keyword,
                            properties={
                                "keyword": keyword,
                                "match_start": match.start(),
                                "match_end": match.end(),
                            },
                        )

                        node.add_source_chunk(chunk.id)
                        subgraph.add_node(node)

                except re.error as e:
                    logger.warning("Error in keyword pattern '%s': %s", keyword, e)
                    continue

        return subgraph
