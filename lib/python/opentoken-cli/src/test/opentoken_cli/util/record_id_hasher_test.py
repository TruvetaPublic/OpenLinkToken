"""
Copyright (c) Truveta. All rights reserved.
"""

from opentoken_cli.util.record_id_hasher import RecordIdHasher


class TestRecordIdHasher:
    """Unit tests for RecordIdHasher."""

    def test_hash_produces_consistent_output(self):
        """Same input must always produce the same hash."""
        record_id = "test-record-001"
        assert RecordIdHasher.hash(record_id) == RecordIdHasher.hash(record_id)

    def test_hash_produces_64_char_hex_string(self):
        """SHA-256 digest must be a 64-character lowercase hex string."""
        result = RecordIdHasher.hash("some-record-id")
        assert len(result) == 64
        assert result == result.lower()
        # Must be valid hex
        int(result, 16)

    def test_hash_different_inputs_produce_different_hashes(self):
        """Different inputs must produce different hashes."""
        assert RecordIdHasher.hash("record-001") != RecordIdHasher.hash("record-002")

    def test_hash_known_value(self):
        """Verify against a known SHA-256 value: sha256('hello')."""
        expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert RecordIdHasher.hash("hello") == expected

    def test_hash_empty_string(self):
        """SHA-256 of the empty string is a well-known constant."""
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert RecordIdHasher.hash("") == expected
