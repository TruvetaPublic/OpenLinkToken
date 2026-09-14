"""Protocol for embedding transformers that convert float vectors to token strings."""

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingTransformer(Protocol):
    """Protocol for transformers that convert a float embedding to a list of token strings."""

    def transform(self, embedding: List[float]) -> List[str]:
        """Transform a raw float embedding into a list of token strings."""
        ...
