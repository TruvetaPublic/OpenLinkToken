# SPDX-License-Identifier: MIT
"""
Unified processor for token transformations (encryption/decryption).
"""

import logging
from dataclasses import dataclass
from typing import Callable, Protocol

from openlinktoken.tokens import Token

logger = logging.getLogger(__name__)


class TokenTransformer(Protocol):
    """Protocol for token transformers."""

    def transform(self, token: str) -> str:
        """Transform a token."""
        ...


@dataclass(frozen=True)
class TokenTransformationSummary:
    """Summary counters for token encryption or decryption runs."""

    total_tokens: int
    transformed_tokens: int
    failed_tokens: int


class TokenTransformationProcessor:
    """
    Unified processor for token transformations (encryption/decryption).

    This class provides a generic token transformation pipeline that can handle
    both encryption and decryption operations using the provided TokenTransformer.
    """

    @staticmethod
    def process(
        reader,
        writer,
        transformer: TokenTransformer,
        operation: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> TokenTransformationSummary:
        """
        Read tokens from input, transform them, and write to output.

        Args:
            reader: TokenReader providing input token rows
            writer: TokenWriter for output
            transformer: The token transformer (encryption or decryption)
            operation: The operation name for logging (e.g., "encrypted", "decrypted")
        """
        row_counter = 0
        transformed_counter = 0
        error_counter = 0
        last_reported_count = 0

        for row in reader:
            row_counter += 1

            token = row.get("Token")

            # Transform the token if it's not blank
            if token and token != Token.BLANK:
                try:
                    transformed_token = transformer.transform(token)
                    row["Token"] = transformed_token
                    transformed_counter += 1
                except Exception as e:
                    logger.error(
                        f"Failed to {operation} token for RecordId {row.get('RecordId')}, "
                        f"RuleId {row.get('RuleId')}: {e}"
                    )
                    error_counter += 1
                    # Keep the original token in case of error

            # Write token
            writer.write_token(row)

            if row_counter % 10000 == 0:
                logger.info(f'Processed "{row_counter:,}" tokens')
                last_reported_count = row_counter
                if progress_callback is not None:
                    progress_callback(row_counter)

        logger.info(f"Processed a total of {row_counter:,} tokens")
        logger.info(f"Successfully {operation} {transformed_counter:,} tokens")
        if error_counter > 0:
            logger.warning(f"Failed to {operation} {error_counter:,} tokens")
        if progress_callback is not None and row_counter != last_reported_count:
            progress_callback(row_counter)

        return TokenTransformationSummary(
            total_tokens=row_counter,
            transformed_tokens=transformed_counter,
            failed_tokens=error_counter,
        )
