# SPDX-License-Identifier: MIT

from openlinktoken.metadata import HashCalculationException, Metadata

PRIMARY_SECRET_DIGEST = "PrimarySecretDigest"
SECONDARY_SECRET_DIGEST = "SecondarySecretDigest"


class TestMetadata:
    """
    Test metadata defaults and version reporting.
    """

    def test_initialize_only(self):
        """
        Verify that initialize only.
        """
        metadata = Metadata()
        result = metadata.initialize()

        assert Metadata.PYTHON_VERSION in result
        assert Metadata.PLATFORM in result
        assert Metadata.VERSION in result
        assert len(result) == 3

        assert result[Metadata.PLATFORM] == Metadata.PLATFORM_PYTHON
        assert result[Metadata.VERSION] == Metadata.DEFAULT_VERSION

    def test_add_hashed_secret_with_custom_key(self):
        """
        Verify that add hashed secret with custom key.
        """
        metadata = Metadata()
        metadata.initialize()

        result = metadata.add_hashed_secret(PRIMARY_SECRET_DIGEST, "test-hashing-secret")

        assert PRIMARY_SECRET_DIGEST in result
        assert SECONDARY_SECRET_DIGEST not in result
        assert result[PRIMARY_SECRET_DIGEST] is not None

    def test_add_hashed_secret_with_second_custom_key(self):
        """
        Verify that add hashed secret with second custom key.
        """
        metadata = Metadata()
        metadata.initialize()

        result = metadata.add_hashed_secret(SECONDARY_SECRET_DIGEST, "test-encryption-key")

        assert PRIMARY_SECRET_DIGEST not in result
        assert SECONDARY_SECRET_DIGEST in result
        assert result[SECONDARY_SECRET_DIGEST] is not None

    def test_add_hashed_secret_with_both_custom_keys(self):
        """
        Verify that add hashed secret with both custom keys.
        """
        metadata = Metadata()
        metadata.initialize()

        metadata.add_hashed_secret(PRIMARY_SECRET_DIGEST, "test-hashing-secret")
        result = metadata.add_hashed_secret(SECONDARY_SECRET_DIGEST, "test-encryption-key")

        assert PRIMARY_SECRET_DIGEST in result
        assert SECONDARY_SECRET_DIGEST in result
        assert result[PRIMARY_SECRET_DIGEST] is not None
        assert result[SECONDARY_SECRET_DIGEST] is not None
        assert result[PRIMARY_SECRET_DIGEST] != result[SECONDARY_SECRET_DIGEST]

    def test_add_hashed_secret_with_null_secrets(self):
        """
        Verify that add hashed secret with null secrets.
        """
        metadata = Metadata()
        metadata.initialize()

        metadata.add_hashed_secret(PRIMARY_SECRET_DIGEST, None)
        result = metadata.add_hashed_secret(SECONDARY_SECRET_DIGEST, None)

        assert PRIMARY_SECRET_DIGEST not in result
        assert SECONDARY_SECRET_DIGEST not in result

    def test_add_hashed_secret_with_empty_secrets(self):
        """
        Verify that add hashed secret with empty secrets.
        """
        metadata = Metadata()
        metadata.initialize()

        metadata.add_hashed_secret(PRIMARY_SECRET_DIGEST, "")
        result = metadata.add_hashed_secret(SECONDARY_SECRET_DIGEST, "")

        assert PRIMARY_SECRET_DIGEST not in result
        assert SECONDARY_SECRET_DIGEST not in result

    def test_add_hashed_secret_with_custom_key_value(self):
        """
        Verify that add hashed secret with custom key value.
        """
        metadata = Metadata()
        metadata.initialize()

        custom_key = "CustomSecretHash"
        custom_secret = "my-custom-secret"
        result = metadata.add_hashed_secret(custom_key, custom_secret)

        assert custom_key in result
        assert result[custom_key] is not None
        assert result[custom_key] == Metadata.calculate_secure_hash(custom_secret)

    def test_calculate_secure_hash_with_valid_input(self):
        """
        Verify that calculate secure hash with valid input.
        """
        input_str = "test-input"
        hash_result = Metadata.calculate_secure_hash(input_str)

        assert hash_result is not None
        assert len(hash_result) > 0
        assert len(hash_result) == 64

        hash2 = Metadata.calculate_secure_hash(input_str)
        assert hash_result == hash2

    def test_calculate_secure_hash_with_known_value(self):
        """
        Verify that calculate secure hash with known value.
        """
        input_str = "hello"
        expected_hash = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

        actual_hash = Metadata.calculate_secure_hash(input_str)
        assert actual_hash == expected_hash

    def test_calculate_secure_hash_with_different_inputs(self):
        """
        Verify that calculate secure hash with different inputs.
        """
        input1 = "input1"
        input2 = "input2"

        hash1 = Metadata.calculate_secure_hash(input1)
        hash2 = Metadata.calculate_secure_hash(input2)

        assert hash1 != hash2

    def test_calculate_secure_hash_with_null_input(self):
        """
        Verify that calculate secure hash with null input.
        """
        hash_result = Metadata.calculate_secure_hash(None)
        assert hash_result is None

    def test_calculate_secure_hash_with_empty_input(self):
        """
        Verify that calculate secure hash with empty input.
        """
        hash_result = Metadata.calculate_secure_hash("")
        assert hash_result is None

    def test_calculate_secure_hash_return_type_allows_none_for_empty_input(self):
        """
        Verify that calculate secure hash return type allows none for empty input.
        """
        hash_result: str | None = Metadata.calculate_secure_hash("")
        assert hash_result is None

    def test_calculate_secure_hash_with_unicode_input(self):
        """
        Verify that calculate secure hash with unicode input.
        """
        input_str = "こんにちは"
        hash_result = Metadata.calculate_secure_hash(input_str)

        assert hash_result is not None
        assert len(hash_result) == 64

        hash2 = Metadata.calculate_secure_hash(input_str)
        assert hash_result == hash2

    def test_calculate_secure_hash_with_raw_bytes(self):
        """
        Verify that calculate secure hash with raw bytes.
        """
        input_bytes = b"\xff\x00bytes"

        hash_result = Metadata.calculate_secure_hash(input_bytes)

        assert hash_result is not None
        assert len(hash_result) == 64

    def test_metadata_no_longer_defines_secret_hash_constants(self):
        """
        Verify that metadata no longer defines secret hash constants.
        """
        assert not hasattr(Metadata, "ENCRYPTION_SECRET_HASH")
        assert not hasattr(Metadata, "HASHING_SECRET_HASH")

    def test_hash_calculation_exception_creation(self):
        """
        Verify that hash calculation exception creation.
        """
        message = "Test message"
        cause = RuntimeError("Test cause")

        exception = HashCalculationException(message, cause)

        assert str(exception) == message
        assert exception.cause == cause
