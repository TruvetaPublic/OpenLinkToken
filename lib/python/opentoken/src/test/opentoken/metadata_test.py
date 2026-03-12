"""
Copyright (c) Truveta. All rights reserved.
"""

from opentoken.metadata import HashCalculationException, Metadata


class TestMetadata:
    def test_initialize_only(self):
        metadata = Metadata()
        result = metadata.initialize()

        assert Metadata.PYTHON_VERSION in result
        assert Metadata.PLATFORM in result
        assert Metadata.OPENTOKEN_VERSION in result

        assert Metadata.HASHING_SECRET_HASH not in result
        assert Metadata.ENCRYPTION_SECRET_HASH not in result

        assert result[Metadata.PLATFORM] == Metadata.PLATFORM_PYTHON
        assert result[Metadata.OPENTOKEN_VERSION] == Metadata.DEFAULT_VERSION

    def test_add_hashed_secret_with_hashing_secret(self):
        metadata = Metadata()
        metadata.initialize()

        hashing_secret = "test-hashing-secret"
        result = metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)

        assert Metadata.HASHING_SECRET_HASH in result
        assert Metadata.ENCRYPTION_SECRET_HASH not in result
        assert result[Metadata.HASHING_SECRET_HASH] is not None

    def test_add_hashed_secret_with_encryption_key(self):
        metadata = Metadata()
        metadata.initialize()

        encryption_key = "test-encryption-key"
        result = metadata.add_hashed_secret(Metadata.ENCRYPTION_SECRET_HASH, encryption_key)

        assert Metadata.HASHING_SECRET_HASH not in result
        assert Metadata.ENCRYPTION_SECRET_HASH in result
        assert result[Metadata.ENCRYPTION_SECRET_HASH] is not None

    def test_add_hashed_secret_with_both_secrets(self):
        metadata = Metadata()
        metadata.initialize()

        hashing_secret = "test-hashing-secret"
        encryption_key = "test-encryption-key"

        metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)
        result = metadata.add_hashed_secret(Metadata.ENCRYPTION_SECRET_HASH, encryption_key)

        assert Metadata.HASHING_SECRET_HASH in result
        assert Metadata.ENCRYPTION_SECRET_HASH in result
        assert result[Metadata.HASHING_SECRET_HASH] is not None
        assert result[Metadata.ENCRYPTION_SECRET_HASH] is not None

        # Verify hashes are different for different inputs
        assert result[Metadata.HASHING_SECRET_HASH] != result[Metadata.ENCRYPTION_SECRET_HASH]

    def test_add_hashed_secret_with_null_secrets(self):
        metadata = Metadata()
        metadata.initialize()

        metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, None)
        result = metadata.add_hashed_secret(Metadata.ENCRYPTION_SECRET_HASH, None)

        assert Metadata.HASHING_SECRET_HASH not in result
        assert Metadata.ENCRYPTION_SECRET_HASH not in result

    def test_add_hashed_secret_with_empty_secrets(self):
        metadata = Metadata()
        metadata.initialize()

        metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, "")
        result = metadata.add_hashed_secret(Metadata.ENCRYPTION_SECRET_HASH, "")

        assert Metadata.HASHING_SECRET_HASH not in result
        assert Metadata.ENCRYPTION_SECRET_HASH not in result

    def test_add_hashed_secret_with_custom_key(self):
        metadata = Metadata()
        metadata.initialize()

        custom_key = "CustomSecretHash"
        custom_secret = "my-custom-secret"
        result = metadata.add_hashed_secret(custom_key, custom_secret)

        assert custom_key in result
        assert result[custom_key] is not None
        assert result[custom_key] == Metadata.calculate_secure_hash(custom_secret)

    def test_calculate_secure_hash_with_valid_input(self):
        input_str = "test-input"
        hash_result = Metadata.calculate_secure_hash(input_str)

        assert hash_result is not None
        assert len(hash_result) > 0
        assert len(hash_result) == 64  # SHA-256 produces 64 character hex string

        # Verify the hash is consistent
        hash2 = Metadata.calculate_secure_hash(input_str)
        assert hash_result == hash2

    def test_calculate_secure_hash_with_known_value(self):
        # Test with a known SHA-256 value to ensure compatibility
        input_str = "hello"
        expected_hash = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

        actual_hash = Metadata.calculate_secure_hash(input_str)
        assert actual_hash == expected_hash

    def test_calculate_secure_hash_with_different_inputs(self):
        input1 = "input1"
        input2 = "input2"

        hash1 = Metadata.calculate_secure_hash(input1)
        hash2 = Metadata.calculate_secure_hash(input2)

        assert hash1 != hash2

    def test_calculate_secure_hash_with_null_input(self):
        hash_result = Metadata.calculate_secure_hash(None)
        assert hash_result is None

    def test_calculate_secure_hash_with_empty_input(self):
        hash_result = Metadata.calculate_secure_hash("")
        assert hash_result is None

    def test_calculate_secure_hash_with_unicode_input(self):
        input_str = "こんにちは"  # Japanese "hello"
        hash_result = Metadata.calculate_secure_hash(input_str)

        assert hash_result is not None
        assert len(hash_result) == 64

        # Verify UTF-8 encoding produces consistent results
        hash2 = Metadata.calculate_secure_hash(input_str)
        assert hash_result == hash2

    def test_calculate_secure_hash_with_raw_bytes(self):
        input_bytes = b"\xff\x00bytes"

        hash_result = Metadata.calculate_secure_hash(input_bytes)

        assert hash_result is not None
        assert len(hash_result) == 64

    def test_metadata_constants(self):
        # Verify that the new constants are properly defined
        assert Metadata.ENCRYPTION_SECRET_HASH is not None
        assert Metadata.HASHING_SECRET_HASH is not None

        assert Metadata.ENCRYPTION_SECRET_HASH == "EncryptionSecretHash"
        assert Metadata.HASHING_SECRET_HASH == "HashingSecretHash"

    def test_hash_calculation_exception_creation(self):
        message = "Test message"
        cause = RuntimeError("Test cause")

        exception = HashCalculationException(message, cause)

        assert str(exception) == message
        assert exception.cause == cause
