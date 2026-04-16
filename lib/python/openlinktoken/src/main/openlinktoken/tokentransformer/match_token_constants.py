"""Shared constants for match token formatting and parsing."""

# Prefix for version 1 match tokens.
V1_TOKEN_PREFIX = "ot.V1."

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
