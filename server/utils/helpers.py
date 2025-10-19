"""Helper utility functions for the server."""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Check if LangSmith is available
try:
    from langsmith import get_current_run_tree
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False


def convert_metrics_to_dict(metrics: Any) -> Optional[Dict[str, Any]]:
    """
    Convert metrics to dictionary format.

    Args:
        metrics: Metrics object (various formats)

    Returns:
        Dictionary representation of metrics or None
    """
    if metrics is None:
        return None

    # If already a dict, return as-is
    if isinstance(metrics, dict):
        return metrics

    # Try pydantic dict() method
    if hasattr(metrics, 'dict'):
        return metrics.dict()

    # Try dict() conversion on object with __dict__
    if hasattr(metrics, '__dict__'):
        return dict(metrics.__dict__)

    # Fallback: try direct conversion
    try:
        return dict(metrics)
    except (TypeError, ValueError):
        logger.warning(f"Could not convert metrics to dict: {type(metrics)}")
        return {}


def add_tracing_metadata(execution_mode: str, request: Any) -> None:
    """
    Add tracing metadata to current LangSmith run.

    Args:
        execution_mode: Type of execution (synchronous, asynchronous, batch, stream)
        request: Request object containing pipeline parameters
    """
    if not HAS_LANGSMITH:
        return

    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.add_metadata({
                "execution_mode": execution_mode,
                "server_version": "1.0.0",
                "input_path": getattr(request, 'input_path', None),
                "output_path": getattr(request, 'output_path', None),
                "has_custom_config": getattr(request, 'config', None) is not None,
                "batch_size": getattr(request, 'batch_size', None)
            })
            logger.debug(f"Added tracing metadata for {execution_mode} execution")
    except Exception as e:
        logger.debug(f"Failed to add tracing metadata: {e}")
