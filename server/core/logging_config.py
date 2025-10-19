"""Logging configuration for the server."""
import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure logging for the server.

    Args:
        level: Logging level (default: INFO)
    """
    log_level = level or "INFO"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific loggers
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
