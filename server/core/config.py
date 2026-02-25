"""Configuration management for the server.

Pipeline-specific defaults live here. For application-wide settings
(credentials, ports, etc.) see ``server.core.settings``.
"""
from typing import Any, Dict
import os

from server.core.settings import get_settings


def _build_default_config() -> Dict[str, Any]:
    """Build the default pipeline config from settings (no hardcoded creds)."""
    settings = get_settings()

    return {
        "pipeline": {
            "components": {
                "scanner": {
                    "type": "file_scanner",
                    "enabled": True,
                },
                "reader": {
                    "type": "txt_reader",
                    "enabled": True,
                },
                "splitter": {
                    "type": "semantic_splitter",
                    "enabled": True,
                    "config": {
                        "model_name": "jhu-clsp/mmBERT-small",
                        "similarity_threshold": 0.95,
                        "min_chunk_length": 100,
                        "max_chunk_length": 500,
                    },
                },
                "extractor": {
                    "type": "llm_extractor",
                    "enabled": True,
                    "config": {
                        "llm_provider": settings.LLM_PROVIDER,
                        "model": settings.LLM_MODEL,
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "use_template": True,
                        "extraction_schema": "knowledge_graphs/schema/financebench_spg.schema",
                        "batch_size": 5,
                    },
                },
                "vectorizer": {
                    "type": "gemini_vectorizer",
                    "model": settings.EMBEDDING_MODEL,
                    "max_tokens": 4096,
                    "embed_nodes": True,
                    "embed_edges": True,
                    "batch_size": 100,
                    "max_retries": 3,
                    "retry_delay": 10,
                    "enabled": True,
                },
                "writer": {
                    "type": "neo4j_writer",
                    "enabled": True,
                    "config": {
                        "uri": settings.NEO4J_URI,
                        "username": settings.NEO4J_USERNAME,
                        "password": settings.NEO4J_PASSWORD,
                        "database": settings.NEO4J_DATABASE,
                        "clear_database": True,
                    },
                },
            }
        }
    }


# Lazy-built on first access so settings are validated first.
_default_config: Dict[str, Any] | None = None


def get_default_config() -> Dict[str, Any]:
    """Return the default pipeline configuration (built from settings)."""
    global _default_config
    if _default_config is None:
        _default_config = _build_default_config()
    return _default_config



# MCP Configuration
MCP_SETTINGS: Dict[str, Any] = {
    "servers": {
        "information_tools-mcp": {
            "transport": "sse",
            "url": os.getenv("MCP_SERVER_URL", "https://dev-mcp-server-v3.stock-gpt.ai/sse"),
            "enabled_tools": [
                "get_financial_data",
                "get_ratio_data",
                "get_industry_metrics",
            ],
        }
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file or return default.

    Args:
        config_path: Path to YAML configuration file.
                     Falls back to ``CONFIG_FILE`` env var, then default config.

    Returns:
        Pipeline configuration dictionary.
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_FILE")

    if not config_path:
        return get_default_config().copy()

    import yaml
    from pathlib import Path

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config
