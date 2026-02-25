"""Multi-step extraction strategy: NER -> STD -> TRP."""

import logging
from typing import Any, Dict

from .strategies import ExtractionStrategy
from .response_parser import ResponseParser
from .subgraph_builder import SubGraphBuilder
from ...models.chunk import Chunk
from ...models.graph import SubGraph
from ...utils.llm_client import LLMClient, create_extraction_prompt
from ...utils.template_loader import load_prompt_template

logger = logging.getLogger(__name__)


class MultiStepExtractionStrategy(ExtractionStrategy):
    """Three-step extraction: NER -> STD -> TRP.

    1. **NER** -- Named Entity Recognition: discover entities in the text.
    2. **STD** -- Standardization: resolve official / canonical names.
    3. **TRP** -- Triple / Relationship extraction: find edges between entities.

    Parameters:
        llm_client: The LLM client used to send prompts.
        extraction_schema: Schema dict passed into prompt templates.
        subgraph_builder: Builder that converts raw dicts into ``SubGraph``.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        extraction_schema: Dict[str, Any],
        subgraph_builder: SubGraphBuilder,
    ) -> None:
        self.llm_client = llm_client
        self.extraction_schema = extraction_schema
        self.builder = subgraph_builder
        self.parser = ResponseParser()

    def extract(self, chunk: Chunk) -> SubGraph:
        """Run the 3-step extraction pipeline on a single chunk."""
        text = chunk.content

        # Step 1: NER
        ner_prompt = self._create_template_prompt("ner.md", text, None)
        ner_response = self.llm_client.simple_chat(ner_prompt)
        ner_result = self.parser.parse_extraction_response(ner_response)

        if not self.parser.has_valid_entities(ner_result):
            logger.warning("No valid entities in NER for chunk %s", chunk.id)
            return SubGraph(source_chunk_id=chunk.id)

        normalized_ner = self.parser.normalize_to_dict(ner_result, "entities")

        # Step 2: STD
        std_prompt = self._create_template_prompt("std.md", text, normalized_ner)
        std_response = self.llm_client.simple_chat(std_prompt)
        std_result = self.parser.parse_extraction_response(std_response)

        if not self.parser.has_valid_entities(std_result):
            logger.warning(
                "STD failed for chunk %s, using NER results", chunk.id
            )
            std_result = normalized_ner
        else:
            std_result = self.parser.normalize_to_dict(std_result, "entities")

        # Step 3: TRP
        trp_prompt = self._create_template_prompt("trp.md", text, std_result)
        trp_response = self.llm_client.simple_chat(trp_prompt)
        trp_result = self.parser.parse_extraction_response(trp_response)

        if not trp_result:
            trp_result = {"relationships": []}
        else:
            trp_result = self.parser.normalize_to_dict(trp_result, "relationships")

        return self.builder.build_from_extraction(chunk, std_result, trp_result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_template_prompt(
        self, template_name: str, text: str, named_entities: dict | None
    ) -> str:
        """Create a prompt by rendering a Jinja2 template.

        Falls back to a basic extraction prompt when template loading fails.
        """
        try:
            return load_prompt_template(
                template_name=template_name,
                schema=self.extraction_schema,
                input_text=text,
                named_entities=named_entities,
            )
        except Exception as e:
            logger.warning("Failed to load template %s: %s", template_name, e)
            logger.info("Falling back to traditional prompt creation")
            return create_extraction_prompt(
                text=text, schema=self.extraction_schema
            )
