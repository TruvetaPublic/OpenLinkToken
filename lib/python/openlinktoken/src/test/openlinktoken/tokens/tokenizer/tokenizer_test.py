# SPDX-License-Identifier: MIT

from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer


class ConcreteTokenizer(Tokenizer):
    """Minimal tokenizer implementation for testing base behavior."""

    def tokenize(self, value: str) -> str:
        """Return the value unchanged."""
        return value


def test_get_token_transformer_list_defaults_to_empty_list():
    """The base tokenizer has no configured token transformers by default."""
    assert ConcreteTokenizer().get_token_transformer_list() == []
