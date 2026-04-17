# SPDX-License-Identifier: MIT

import pytest

from openlinktoken.tokentransformer.match_token_constants import (
    LEGACY_V1_TOKEN_PREFIX,
    SUPPORTED_V1_TOKEN_PREFIXES,
    V1_TOKEN_PREFIX,
    is_supported_v1_token,
    strip_supported_v1_token_prefix,
)


class TestMatchTokenConstants:
    """Test cases for V1 token prefix helpers."""

    def test_supported_prefixes_include_canonical_and_legacy_values(self):
        """Readers must accept both canonical and legacy V1 prefixes."""
        assert SUPPORTED_V1_TOKEN_PREFIXES == (V1_TOKEN_PREFIX, LEGACY_V1_TOKEN_PREFIX)

    @pytest.mark.parametrize("prefix", [V1_TOKEN_PREFIX, LEGACY_V1_TOKEN_PREFIX])
    def test_is_supported_v1_token_accepts_supported_prefixes(self, prefix):
        """Both supported V1 prefixes should be recognized."""
        assert is_supported_v1_token(f"{prefix}header.payload.tag")

    def test_is_supported_v1_token_rejects_unsupported_prefixes(self):
        """Non-V1 and malformed prefixes must not be treated as supported JWE tokens."""
        assert not is_supported_v1_token("not-a-v1-token")

    @pytest.mark.parametrize("prefix", [V1_TOKEN_PREFIX, LEGACY_V1_TOKEN_PREFIX])
    def test_strip_supported_v1_token_prefix_returns_compact_jwe_body(self, prefix):
        """Prefix stripping should return the JWE body for both accepted formats."""
        token_body = "header.encrypted-key.iv.ciphertext.tag"

        assert strip_supported_v1_token_prefix(f"{prefix}{token_body}") == token_body

    def test_strip_supported_v1_token_prefix_raises_for_unsupported_prefixes(self):
        """Unsupported prefixes should fail loudly instead of being silently accepted."""
        with pytest.raises(ValueError, match="supported V1 prefix"):
            strip_supported_v1_token_prefix("invalid.V1.header.payload.tag")
