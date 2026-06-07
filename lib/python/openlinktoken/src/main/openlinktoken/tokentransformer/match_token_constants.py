"""Shared constants for match token formatting and parsing."""

# Canonical prefix for version 1 match tokens.
V1_TOKEN_PREFIX = "olt.V1."

# Prefixes accepted by readers that consume JWE-wrapped V1 tokens.
SUPPORTED_V1_TOKEN_PREFIXES = (V1_TOKEN_PREFIX,)

# Token type value used in the protected JWE header.
TOKEN_TYPE = "match-token"

# Payload key for token rule identifier.
PAYLOAD_KEY_RULE_ID = "rlid"

# Payload key for hash algorithm metadata.
PAYLOAD_KEY_HASH_ALGORITHM = "hash_alg"

# Payload key for MAC algorithm metadata.
PAYLOAD_KEY_MAC_ALGORITHM = "mac_alg"

# Payload key for PPID values.
PAYLOAD_KEY_PPID = "ppid"

# Payload key for ring identifier.
PAYLOAD_KEY_RING_ID = "rid"

# Payload key for issuer identifier.
PAYLOAD_KEY_ISSUER = "iss"

# Payload key for issued-at UNIX timestamp.
PAYLOAD_KEY_ISSUED_AT = "iat"

# Protected header key for JOSE algorithm.
HEADER_KEY_ALGORITHM = "alg"

# Protected header key for content encryption algorithm.
HEADER_KEY_ENCRYPTION = "enc"

# Protected header key for token type.
HEADER_KEY_TYPE = "typ"

# Protected header key for key identifier.
HEADER_KEY_KEY_ID = "kid"


def is_supported_v1_token(token: str) -> bool:
    """Return True when the token starts with a recognized V1 JWE prefix."""
    return any(token.startswith(prefix) for prefix in SUPPORTED_V1_TOKEN_PREFIXES)


def strip_supported_v1_token_prefix(token: str) -> str:
    """Strip the recognized V1 JWE prefix from a token and return the JWE body."""
    for prefix in SUPPORTED_V1_TOKEN_PREFIXES:
        if token.startswith(prefix):
            return token[len(prefix) :]

    raise ValueError("Token does not start with a supported V1 prefix")
