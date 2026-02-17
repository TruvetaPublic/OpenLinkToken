"""
Copyright (c) Truveta. All rights reserved.
"""

import base64
import json
import logging

from jwcrypto import jwe, jwk
from opentoken_cli.io.token_reader import TokenReader
from opentoken_cli.io.token_writer import TokenWriter
from opentoken_cli.processor.token_constants import TokenConstants
from opentoken.tokens.token import Token
from opentoken.tokentransformer.decrypt_token_transformer import DecryptTokenTransformer
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_PPID
from opentoken.tokentransformer.match_token_constants import V1_TOKEN_PREFIX


logger = logging.getLogger(__name__)


class TokenDecryptionProcessor:
    """
    Process encrypted tokens for decryption.
    
    This class is used to read encrypted tokens from input source,
    decrypt them, and write the decrypted tokens to the output data source.
    """

    @staticmethod
    def process(reader: TokenReader, writer: TokenWriter, decryptor: DecryptTokenTransformer):
        """
        Reads encrypted tokens from the input data source, decrypts them, and
        writes the result back to the output data source.
        
        Args:
            reader: Iterator providing encrypted token rows
            writer: Writer instance with write_token method
            decryptor: The decryption transformer
        """
        TokenDecryptionProcessor.process_with_key(reader, writer, decryptor, None)

    @staticmethod
    def process_with_key(
        reader: TokenReader,
        writer: TokenWriter,
        decryptor: DecryptTokenTransformer,
        encryption_key: str | None,
    ):
        """
        Reads encrypted tokens from the input data source, decrypts them, and
        writes the result back to the output data source.

        Args:
            reader: Iterator providing encrypted token rows
            writer: Writer instance with write_token method
            decryptor: The decryption transformer
            encryption_key: Encryption key for decrypting JWE tokens
        """
        row_counter = 0
        decrypted_counter = 0
        error_counter = 0

        for row in reader:
            row_counter += 1
            
            token = row.get(TokenConstants.TOKEN, '')
            
            # Decrypt the token if it's not blank
            if token and token != Token.BLANK:
                try:
                    decrypted_token = TokenDecryptionProcessor._decrypt_token(
                        token, decryptor, encryption_key
                    )
                    row[TokenConstants.TOKEN] = decrypted_token
                    decrypted_counter += 1
                except Exception as e:
                    logger.error(
                        f"Failed to decrypt token for RecordId {row.get(TokenConstants.RECORD_ID)}, "
                        f"RuleId {row.get(TokenConstants.RULE_ID)}: {e}")
                    error_counter += 1
                    # Keep the encrypted token in case of error
            
            writer.write_token(row)

            if row_counter % 10000 == 0:
                logger.info(f'Processed "{row_counter:,}" tokens')

        logger.info(f'Processed a total of {row_counter:,} tokens')
        logger.info(f'Successfully decrypted {decrypted_counter:,} tokens')
        if error_counter > 0:
            logger.warning(f'Failed to decrypt {error_counter:,} tokens')

    @staticmethod
    def _decrypt_token(
        token: str,
        decryptor: DecryptTokenTransformer,
        encryption_key: str | None,
    ) -> str:
        if token.startswith(V1_TOKEN_PREFIX):
            return TokenDecryptionProcessor._decrypt_v1_token(token, decryptor, encryption_key)
        return decryptor.transform(token)

    @staticmethod
    def _decrypt_v1_token(
        token: str,
        decryptor: DecryptTokenTransformer,
        encryption_key: str | None,
    ) -> str:
        if not encryption_key:
            raise ValueError("Encryption key is required for JWE token decryption")

        jwe_compact = token[len(V1_TOKEN_PREFIX):]
        key_bytes = encryption_key.encode('utf-8')
        key_b64 = base64.urlsafe_b64encode(key_bytes).decode('utf-8').rstrip('=')
        jwk_key = jwk.JWK(kty="oct", k=key_b64)

        jwe_token = jwe.JWE()
        jwe_token.deserialize(jwe_compact)
        jwe_token.decrypt(jwk_key)

        payload = json.loads(jwe_token.payload.decode('utf-8'))
        ppid_value = payload.get(PAYLOAD_KEY_PPID, [])
        if isinstance(ppid_value, list):
            ppid_value = ppid_value[0] if ppid_value else ""

        if not ppid_value or ppid_value == Token.BLANK:
            return ppid_value

        try:
            return decryptor.transform(ppid_value)
        except Exception as e:
            logger.debug("Failed to decrypt legacy token inside JWE payload", exc_info=e)
            return ppid_value
