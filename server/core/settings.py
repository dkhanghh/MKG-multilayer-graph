"""Centralized application settings using Pydantic BaseSettings.

Single source of truth for all configuration. Reads from .env file
and environment variables. Validates on import — fails fast if required
values are missing.
"""
import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings, validated from environment variables."""

    # ── Neo4j ──────────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = Field(default="", description="Neo4j password (required for graph features)")
    NEO4J_DATABASE: str = "neo4j"

    # ── Chat LLM ───────────────────────────────────────────────────────
    CHAT_OPENAI_BASE_URL: Optional[str] = None
    CHAT_OPENAI_API_KEY: Optional[str] = None
    CHAT_LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1

    # ── Pipeline LLM ──────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_MAX_TOKENS: int = 2000

    # ── Embedding ─────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    GOOGLE_API_KEY: Optional[str] = None

    # ── Server ────────────────────────────────────────────────────────
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_RELOAD: bool = False
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Auth ──────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── MCP ───────────────────────────────────────────────────────────
    MCP_SERVER_URL: Optional[str] = None
    MCP_TRANSPORT: str = "sse"

    # ── Pipeline ──────────────────────────────────────────────────────
    PIPELINE_CONFIG_PATH: str = "configs/financebench_pipeline.yaml"
    OUTPUT_DIR: str = "./output"
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 100

    # ── LangSmith ─────────────────────────────────────────────────────
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "kag-langgraph-server"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Return a cached Settings instance.

    Uses module-level caching so the .env file is only read once.
    """
    return _settings


# Eagerly create on import so validation errors surface immediately.
_settings = Settings()
