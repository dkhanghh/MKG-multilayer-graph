"""Configuration management for the server."""
from typing import Dict, Any
import os


# Default pipeline configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "pipeline": {
        "components": {
            "scanner": {
                "type": "file_scanner",
                "enabled": True
            },
            "reader": {
                "type": "txt_reader",
                "enabled": True
            },
            "splitter": {
                "type": "semantic_splitter",
                "enabled": True,
                "config": {
                    "model_name": "jhu-clsp/mmBERT-small",
                    "similarity_threshold": 0.95,
                    "min_chunk_length": 100,
                    "max_chunk_length": 500
                }
            },
            "extractor": {
                "type": "llm_extractor",
                "enabled": True,
                "config": {
                    "llm_provider": "openai",
                    "model": "gpt-5-mini",
                    "temperature": 1,
                    "max_tokens": 4096,
                    "use_template": True,
                    "extraction_schema": "knowledge_graphs/schema/financebench_spg.schema",
                    "batch_size": 5
                }
            },
            "vectorizer": {
                "type": "gemini_vectorizer",
                "model": "gemini-embedding-001",
                "max_tokens": 4096,
                "embed_nodes": True,
                "embed_edges": True,
                "batch_size": 100,
                "max_retries": 3,
                "retry_delay": 10,
                "enabled": True
            },
            "writer": {
                "type": "neo4j_writer",
                "enabled": True,
                "config": {
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "neo4j@openspg",
                    "database": "financebench1",
                    "clear_database": True
                }
            }
        }
    }
}

# MCP Configuration
MCP_SETTINGS = {
    "servers": {
        "information_tools-mcp": {
            "transport": "sse",
            "url": "https://dev-mcp-server-v3.stock-gpt.ai/sse",
            "enabled_tools": [
                # "get_current_price",
                # "get_market_data_by_symbol",
                "get_financial_data",
                "get_ratio_data",
                # "get_indicator_details",
                "get_industry_metrics",
                # "get_commodity_echart_data",
                # "get_top_companies_by_financial_metrics",
                # "get_top_foreign_buy_stocks",
                # "get_top_market_cap_stocks",
                # "get_top_trading_value_stocks",
                # "get_top_companies_by_valuation_data",
                # "get_top_companies_by_market_data",
                # "get_top_industry_metrics_by_search",
                # "calculate_index_return_excluding_stocks",
                # "calculate_index_ytd_contribution",
            ],
        }
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file or return default.

    Args:
        config_path: Path to YAML configuration file. If None, checks CONFIG_FILE env var.

    Returns:
        Pipeline configuration dictionary

    Raises:
        FileNotFoundError: If config file is specified but not found
    """
    # Check for config path from parameter or environment
    if config_path is None:
        config_path = os.getenv("CONFIG_FILE")

    # If no config path, return default
    if not config_path:
        return DEFAULT_CONFIG.copy()

    # Load from YAML file
    import yaml
    from pathlib import Path

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config
