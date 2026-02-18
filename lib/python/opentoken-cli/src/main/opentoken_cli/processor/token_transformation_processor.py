"""
Copyright (c) Truveta. All rights reserved.

Unified processor for token transformations (encryption/decryption).
"""

import logging
from typing import Protocol

from opentoken.tokens import Token


logger = logging.getLogger(__name__)


class TokenTransformer(Protocol):
    """Protocol for token transformers."""
    
    def transform(self, token: str) -> str:
        """Transform a token."""
        ...


class TokenTransformationProcessor:
    """
    Unified processor for token transformations (encryption/decryption).
    
    This class provides a generic token transformation pipeline that can handle
    both encryption and decryption operations using the provided TokenTransformer.
    """
    
    @staticmethod
    def process(reader, writer, transformer: TokenTransformer, operation: str):
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
        
        logger.info(f"Processed a total of {row_counter:,} tokens")
        logger.info(f"Successfully {operation} {transformed_counter:,} tokens")
        if error_counter > 0:
            logger.warning(f"Failed to {operation} {error_counter:,} tokens")
