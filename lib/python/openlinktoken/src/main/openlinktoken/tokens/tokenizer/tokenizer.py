# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import List

from openlinktoken.tokentransformer.token_transformer import TokenTransformer


class Tokenizer(ABC):
    """
    Interface for tokenizing values into tokens.

    A tokenizer takes a string value (typically a token signature) and
    transforms it into a token using various cryptographic or encoding
    techniques.
    """

    @abstractmethod
    def tokenize(self, value: str) -> str:
        """
        Generate a token from the given value.

        Args:
            value: The value to tokenize (e.g., a token signature).

        Returns:
            The generated token. Returns a default empty token value
            if the input value is null or blank.

        Raises:
            Exception: If an error occurs during tokenization, such as
                       unsupported encoding or cryptographic algorithm issues.
        """
        pass

    def get_token_transformer_list(self) -> List[TokenTransformer]:
        """Return transformers configured after tokenization."""
        return []
