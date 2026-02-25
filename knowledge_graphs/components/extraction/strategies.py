"""Base extraction strategy interface."""

from abc import ABC, abstractmethod

from ...models.chunk import Chunk
from ...models.graph import SubGraph


class ExtractionStrategy(ABC):
    """Abstract base class for extraction strategies."""

    @abstractmethod
    def extract(self, chunk: Chunk) -> SubGraph:
        """Extract knowledge from a chunk and return a SubGraph."""
        pass
