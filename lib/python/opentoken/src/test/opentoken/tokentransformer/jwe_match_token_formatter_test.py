"""
Copyright (c) Truveta. All rights reserved.

Unit tests for JweMatchTokenFormatter.
"""

import unittest
import json
from jwcrypto import jwe, jwk

from opentoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter


class TestJweMatchTokenFormatter(unittest.TestCase):
    """Unit tests for JweMatchTokenFormatter."""

    TEST_ENCRYPTION_KEY = "12345678901234567890123456789012"  # 32 chars
    TEST_RING_ID = "test-ring-2026"
    TEST_RULE_ID = "T1"
    TEST_TOKEN = "dGVzdC10b2tlbi1wcGlk"  # base64-encoded test token
    TEST_ISSUER = "test.issuer"

    def test_constructor_with_valid_parameters(self):
        """Test that constructor works with valid parameters."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            self.TEST_ISSUER
        )
        self.assertIsNotNone(formatter)
        self.assertEqual(formatter.ring_id, self.TEST_RING_ID)
        self.assertEqual(formatter.rule_id, self.TEST_RULE_ID)
        self.assertEqual(formatter.issuer, self.TEST_ISSUER)

    def test_constructor_with_null_encryption_key(self):
        """Test that constructor raises error with null encryption key."""
        with self.assertRaises(ValueError) as context:
            JweMatchTokenFormatter(None, self.TEST_RING_ID, self.TEST_RULE_ID, self.TEST_ISSUER)
        self.assertIn("32 characters", str(context.exception))

    def test_constructor_with_invalid_key_length(self):
        """Test that constructor raises error with invalid key length."""
        with self.assertRaises(ValueError) as context:
            JweMatchTokenFormatter("short", self.TEST_RING_ID, self.TEST_RULE_ID, self.TEST_ISSUER)
        self.assertIn("32 characters", str(context.exception))

    def test_constructor_with_null_ring_id(self):
        """Test that constructor raises error with null ring ID."""
        with self.assertRaises(ValueError) as context:
            JweMatchTokenFormatter(self.TEST_ENCRYPTION_KEY, None, self.TEST_RULE_ID, self.TEST_ISSUER)
        self.assertIn("Ring ID", str(context.exception))

    def test_constructor_with_empty_ring_id(self):
        """Test that constructor raises error with empty ring ID."""
        with self.assertRaises(ValueError) as context:
            JweMatchTokenFormatter(self.TEST_ENCRYPTION_KEY, "", self.TEST_RULE_ID, self.TEST_ISSUER)
        self.assertIn("Ring ID", str(context.exception))

    def test_constructor_with_null_rule_id(self):
        """Test that constructor raises error with null rule ID."""
        with self.assertRaises(ValueError) as context:
            JweMatchTokenFormatter(self.TEST_ENCRYPTION_KEY, self.TEST_RING_ID, None, self.TEST_ISSUER)
        self.assertIn("Rule ID", str(context.exception))

    def test_constructor_with_empty_rule_id(self):
        """Test that constructor raises error with empty rule ID."""
        with self.assertRaises(ValueError) as context:
            JweMatchTokenFormatter(self.TEST_ENCRYPTION_KEY, self.TEST_RING_ID, "", self.TEST_ISSUER)
        self.assertIn("Rule ID", str(context.exception))

    def test_transform_creates_valid_jwe_token(self):
        """Test that transform creates a valid JWE token with correct prefix."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            self.TEST_ISSUER
        )

        result = formatter.transform(self.TEST_TOKEN)

        # Verify the token has the correct prefix
        self.assertTrue(result.startswith("ot.V1."))

        # Verify it's a valid JWE token (5 parts separated by dots after the prefix)
        jwe_compact = result[len("ot.V1."):]
        parts = jwe_compact.split(".")
        self.assertEqual(5, len(parts), "JWE compact serialization should have 5 parts")

    def test_transform_with_null_token(self):
        """Test that transform returns None for null token."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            None
        )

        result = formatter.transform(None)
        self.assertIsNone(result)

    def test_transform_with_empty_token(self):
        """Test that transform returns empty string for empty token."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            None
        )

        result = formatter.transform("")
        self.assertEqual("", result)

    def test_jwe_header_contains_correct_metadata(self):
        """Test that JWE header contains correct metadata."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            self.TEST_ISSUER
        )

        result = formatter.transform(self.TEST_TOKEN)
        jwe_compact = result[len("ot.V1."):]

        # Parse the JWE object to inspect the header
        jwe_token = jwe.JWE()
        jwe_token.deserialize(jwe_compact)

        # Get the protected header (already a dict)
        protected_header = jwe_token.jose_header

        # Verify header fields
        self.assertEqual("dir", protected_header["alg"])
        self.assertEqual("A256GCM", protected_header["enc"])
        self.assertEqual("match-token", protected_header["typ"])
        self.assertEqual(self.TEST_RING_ID, protected_header["kid"])

    def test_jwe_payload_contains_correct_data(self):
        """Test that decrypted JWE payload contains correct data."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            self.TEST_ISSUER
        )

        result = formatter.transform(self.TEST_TOKEN)
        jwe_compact = result[len("ot.V1."):]

        # Decrypt and parse the payload using the same method as the formatter
        import base64
        key_bytes = self.TEST_ENCRYPTION_KEY.encode('utf-8')
        key_b64 = base64.urlsafe_b64encode(key_bytes).decode('utf-8').rstrip('=')
        jwk_key = jwk.JWK(kty="oct", k=key_b64)
        
        jwe_token = jwe.JWE()
        jwe_token.deserialize(jwe_compact)
        jwe_token.decrypt(jwk_key)
        
        payload = json.loads(jwe_token.payload.decode('utf-8'))

        # Verify payload fields
        self.assertEqual(self.TEST_RULE_ID, payload["rlid"])
        self.assertEqual("SHA-256", payload["hash_alg"])
        self.assertEqual("HS256", payload["mac_alg"])
        self.assertEqual([self.TEST_TOKEN], payload["ppid"])
        self.assertEqual(self.TEST_RING_ID, payload["rid"])
        self.assertEqual(self.TEST_ISSUER, payload["iss"])
        self.assertIn("iat", payload)
        self.assertIsInstance(payload["iat"], int)

    def test_default_issuer(self):
        """Test that default issuer is used when None is provided."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            None  # null issuer should default to "truveta.opentoken"
        )

        self.assertEqual("truveta.opentoken", formatter.issuer)

    def test_different_tokens_produce_different_outputs(self):
        """Test that different tokens produce different encrypted outputs."""
        formatter = JweMatchTokenFormatter(
            self.TEST_ENCRYPTION_KEY,
            self.TEST_RING_ID,
            self.TEST_RULE_ID,
            self.TEST_ISSUER
        )

        result1 = formatter.transform("token1")
        result2 = formatter.transform("token2")

        self.assertNotEqual(result1, result2)
        # But both should have the same prefix
        self.assertTrue(result1.startswith("ot.V1."))
        self.assertTrue(result2.startswith("ot.V1."))


if __name__ == '__main__':
    unittest.main()
