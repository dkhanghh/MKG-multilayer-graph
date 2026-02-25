"""Response parsing and validation utilities for extraction results."""

import logging
from typing import Any, Dict, List, Optional, Union

from ...utils.llm_client import extract_json_from_response

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parses and validates LLM extraction responses."""

    def parse_extraction_response(
        self, response: str
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Parse an LLM response string into a structured extraction result.

        Wraps ``extract_json_from_response`` with additional error handling and
        logging so callers get ``None`` instead of an uncaught exception.

        Args:
            response: Raw LLM response text.

        Returns:
            Parsed JSON as a dict or list, or ``None`` when parsing fails.
        """
        if not response or not response.strip():
            logger.warning("Received empty LLM response")
            return None

        try:
            result = extract_json_from_response(response)
            if result is None:
                logger.warning("No valid JSON found in LLM response")
            return result
        except Exception as e:
            logger.error("Error parsing extraction response: %s", e)
            return None

    def has_valid_entities(
        self, extraction_result: Union[Dict[str, Any], List[Dict[str, Any]], None]
    ) -> bool:
        """Check whether an extraction result contains at least one valid entity.

        Supports both array format ``[{...}, ...]`` and dict format
        ``{"entities": [{...}, ...]}``.

        Args:
            extraction_result: Result from LLM extraction.

        Returns:
            ``True`` if at least one entity has a non-empty ``name`` field.
        """
        if extraction_result is None:
            return False

        # Handle array format: [{...}, {...}]
        if isinstance(extraction_result, list):
            if len(extraction_result) == 0:
                return False
            for entity in extraction_result:
                if (
                    isinstance(entity, dict)
                    and "name" in entity
                    and entity.get("name", "").strip()
                ):
                    return True
            return False

        # Handle dict format: {"entities": [{...}, {...}]}
        if isinstance(extraction_result, dict):
            entities = extraction_result.get("entities", [])
            if not isinstance(entities, list) or len(entities) == 0:
                return False
            for entity in entities:
                if (
                    isinstance(entity, dict)
                    and "name" in entity
                    and entity.get("name", "").strip()
                ):
                    return True
            return False

        # Invalid format
        return False

    def normalize_to_dict(
        self,
        result: Union[Dict[str, Any], List[Dict[str, Any]]],
        key: str,
    ) -> Dict[str, Any]:
        """Normalize an array-or-dict result into ``{key: [...]}``.

        If *result* is already a dict that contains *key*, it is returned
        unchanged.  If it is a bare list, it is wrapped as ``{key: result}``.

        Args:
            result: Extraction result (list or dict).
            key: The key name to use (e.g. ``"entities"`` or ``"relationships"``).

        Returns:
            A dict guaranteed to have *key* mapping to a list.
        """
        if isinstance(result, list):
            return {key: result}

        if isinstance(result, dict):
            if key not in result:
                # The dict might have data under another key; wrap it to be safe.
                return {key: result.get(key, [])}
            return result

        # Fallback for unexpected types
        logger.warning("Unexpected result type %s in normalize_to_dict", type(result))
        return {key: []}
