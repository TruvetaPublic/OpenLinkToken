"""
Copyright (c) Truveta. All rights reserved.

JWE Match Token Formatter for OpenToken V1 format.
"""

import base64
import json
import time
from typing import Optional

from jwcrypto import jwe, jwk
from opentoken.tokentransformer.match_token_constants import HEADER_KEY_ALGORITHM
from opentoken.tokentransformer.match_token_constants import HEADER_KEY_ENCRYPTION
from opentoken.tokentransformer.match_token_constants import HEADER_KEY_KEY_ID
from opentoken.tokentransformer.match_token_constants import HEADER_KEY_TYPE
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_HASH_ALGORITHM
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_ISSUED_AT
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_ISSUER
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_MAC_ALGORITHM
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_PPID
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_RING_ID
from opentoken.tokentransformer.match_token_constants import PAYLOAD_KEY_RULE_ID
from opentoken.tokentransformer.match_token_constants import TOKEN_TYPE
from opentoken.tokentransformer.match_token_constants import V1_TOKEN_PREFIX
from opentoken.tokentransformer.token_transformer import TokenTransformer


class JweMatchTokenFormatter(TokenTransformer):
    """
    Formats tokens in the JWE-based match token format (ot.V1.<JWE>).
    
    This formatter wraps the privacy-protected identifier (PPID) in a 
    self-contained JWE structure with all necessary metadata for versioning
    and cryptographic agility.
    
    See RFC 7516 - JSON Web Encryption (JWE)
    """
    
    def __init__(self, encryption_key: str, ring_id: str, rule_id: str, issuer: Optional[str] = None):
        """
        Initialize the JWE match token formatter.
        
        Args:
            encryption_key: The encryption key (must be 32 bytes for AES-256)
            ring_id: The ring identifier for key management
            rule_id: The token rule identifier (e.g., "T1", "T2", etc.)
            issuer: The issuer identifier (optional, defaults to "truveta.opentoken")
            
        Raises:
            ValueError: If encryption_key, ring_id, or rule_id are invalid
        """
        if not encryption_key or len(encryption_key) != 32:
            raise ValueError("Encryption key must be exactly 32 characters (256 bits)")
        if not ring_id:
            raise ValueError("Ring ID must not be None or empty")
        if not rule_id:
            raise ValueError("Rule ID must not be None or empty")
        
        self.ring_id = ring_id
        self.rule_id = rule_id
        self.issuer = issuer if issuer else "truveta.opentoken"
        
        # Create JWK from the encryption key - needs to be base64url-encoded
        key_bytes = encryption_key.encode('utf-8')
        key_b64 = base64.urlsafe_b64encode(key_bytes).decode('utf-8').rstrip('=')
        self.jwk_key = jwk.JWK(kty="oct", k=key_b64)
    
    def transform(self, token: str) -> str:
        """
        Transform a token (PPID) into the JWE match token format.
        
        The input token should be the base64-encoded HMAC output from previous transformers.
        This method wraps it in a JWE structure with metadata and prepends the "ot.V1." prefix.
        
        Args:
            token: The privacy-protected identifier (PPID) to wrap in JWE format
            
        Returns:
            The formatted match token: ot.V1.<JWE compact serialization>
            
        Raises:
            Exception: If JWE encryption or serialization fails
        """
        if not token:
            # Return as-is for blank tokens
            return token
        
        try:
            # Build the JWE payload with metadata
            payload = {
                PAYLOAD_KEY_RULE_ID: self.rule_id,
                PAYLOAD_KEY_HASH_ALGORITHM: "SHA-256",
                PAYLOAD_KEY_MAC_ALGORITHM: "HS256",
                PAYLOAD_KEY_PPID: [token],  # PPID as an array (single element for hash-based tokens)
                PAYLOAD_KEY_RING_ID: self.ring_id,
                PAYLOAD_KEY_ISSUER: self.issuer,
                PAYLOAD_KEY_ISSUED_AT: int(time.time()),
            }
            
            # Create JWE header with algorithm and encryption method
            protected_header = {
                HEADER_KEY_ALGORITHM: "dir",  # Direct encryption (key used directly)
                HEADER_KEY_ENCRYPTION: "A256GCM",  # AES-256-GCM encryption
                HEADER_KEY_TYPE: TOKEN_TYPE,
                HEADER_KEY_KEY_ID: self.ring_id,
            }
            
            # Create JWE object
            jwe_token = jwe.JWE(
                plaintext=json.dumps(payload).encode('utf-8'),
                recipient=self.jwk_key,
                protected=protected_header
            )
            
            # Serialize to compact form and prepend the ot.V1. prefix
            jwe_compact = jwe_token.serialize(compact=True)
            return V1_TOKEN_PREFIX + jwe_compact
            
        except Exception as e:
            raise Exception(f"JWE token generation failed for rule {self.rule_id}: {str(e)}")
