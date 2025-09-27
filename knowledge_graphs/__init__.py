"""
KAG-LangGraph: A portable knowledge graph construction pipeline using LangGraph

This package provides a simplified, portable version of the KAG (Knowledge Augmented Generation)
pipeline that uses LangGraph instead of NetworkX for workflow orchestration.

Key Components:
- Scanner: File discovery and path generation
- Reader: Document content extraction (PDF, TXT, DOCX)
- Splitter: Text chunking and segmentation
- Extractor: Knowledge extraction using LLMs
- Vectorizer: Text embedding generation
- Writer: Graph output in various formats

The pipeline processes documents through these components sequentially using LangGraph's
stateful workflow management.
"""

__version__ = "0.1.0"
__author__ = "KAG-LangGraph Project"

from .components import *
from .models import *
from .pipeline import *
from .utils import *

__all__ = [
    "Scanner",
    "Reader", 
    "Splitter",
    "Extractor",
    "Vectorizer",
    "Writer",
    "Chunk",
    "SubGraph",
    "Node",
    "Edge",
    "PipelineState",
    "LangGraphExecutor",
    "ComponentRegistry",
]