# SPDX-License-Identifier: MIT
"""
Tests for OpenLinkToken PySpark token processor.
"""

import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jwcrypto import jwe, jwk
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructField, StructType

from openlinktoken.ec_key_utils import fingerprint_to_kid, generate_key_pair, public_key_fingerprint
from openlinktoken.exchange_config import derive_transport_encryption_key, resolve_exchange_config_inputs
from openlinktoken.exchange_jwe import (
    EXCHANGE_JWE_CONTENT_TYPE,
    EXCHANGE_JWE_ENCRYPTION,
    EXCHANGE_JWE_RECIPIENT_ALGORITHM,
    EXCHANGE_JWE_TYPE,
    build_exchange_envelope,
)
from openlinktoken_pyspark import OpenLinkTokenOverlapAnalyzer, OpenLinkTokenProcessor
from openlinktoken_pyspark import token_processor as token_processor_module


@pytest.fixture(scope="module")
def spark():
    """Create a Spark session for testing."""
    spark = (
        SparkSession.builder.appName("OpenLinkTokenTest")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture
def sample_data():
    """Sample person data for testing."""
    return [
        {
            "RecordId": "891dda6c-961f-4154-8541-b48fe18ee620",
            "FirstName": "John",
            "LastName": "Doe",
            "PostalCode": "98004",
            "Sex": "Male",
            "BirthDate": "2000-01-01",
            "SocialSecurityNumber": "123-45-6789",
        },
        {
            "RecordId": "2f97f0f1-4617-40bd-8264-4d24a9adf20a",
            "FirstName": "Joe",
            "LastName": "Price",
            "PostalCode": "15635",
            "Sex": "Male",
            "BirthDate": "1951-10-22",
            "SocialSecurityNumber": "172-10-0983",
        },
    ]


class TestOpenLinkTokenProcessor:
    """Tests for OpenLinkTokenProcessor class."""

    def test_initialization_with_valid_secrets(self):
        """Test that processor initializes with valid secrets."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")
        assert processor.hashing_secret == "HashingKey"
        assert processor.encryption_key == "Secret-Encryption-Key-Goes-Here."

    def test_initialization_accepts_bytes_secrets(self, spark, sample_data):
        """Test that processor stores and uses raw byte secrets."""
        hashing_secret = b"HashingKey"
        encryption_key = b"12345678901234567890123456789012"
        processor = OpenLinkTokenProcessor(hashing_secret=hashing_secret, encryption_key=encryption_key)

        assert processor.hashing_secret == hashing_secret
        assert processor.encryption_key == encryption_key

        result_df = processor.process_dataframe(spark.createDataFrame(sample_data))
        tokens = [row.Token for row in result_df.collect()]

        assert tokens
        assert any(token.startswith("olt.V1.") for token in tokens)

    def test_from_exchange_config_resolves_bytes_and_uses_derived_transport_key(self, spark, sample_data, tmp_path):
        """Test exchange-config factory resolves byte secrets and emits olt.V1 tokens with the derived key."""
        exchange_config_path, private_key_path = _write_exchange_config(tmp_path)
        exchange = resolve_exchange_config_inputs(exchange_config_path, private_key_path=private_key_path)

        processor = OpenLinkTokenProcessor.from_exchange_config(
            exchange_config_path=exchange_config_path,
            private_key_path=private_key_path,
            ring_id="ring-from-config",
        )

        assert processor.hashing_secret == exchange.hashing_secret
        assert processor.encryption_key == derive_transport_encryption_key(exchange)

        exchange_config_path.unlink()
        private_key_path.unlink()

        result_df = processor.process_dataframe(spark.createDataFrame(sample_data))
        tokens = [row.Token for row in result_df.collect()]

        assert tokens
        payload = _decrypt_v1_payload(tokens[0], processor.encryption_key)
        assert payload["rid"] == "ring-from-config"
        assert payload["ppid"]

    def test_from_exchange_config_accepts_direct_exchange_config_and_private_key_values(
        self,
        spark,
        sample_data,
        tmp_path,
    ):
        """Direct exchange-config JSON and private-key PEM values should configure the processor."""
        exchange_config_path, private_key_path = _write_exchange_config(tmp_path)
        exchange = resolve_exchange_config_inputs(exchange_config_path, private_key_path=private_key_path)

        processor = OpenLinkTokenProcessor.from_exchange_config(
            exchange_config_value=exchange_config_path.read_text(encoding="utf-8"),
            private_key_value=private_key_path.read_text(encoding="utf-8"),
            ring_id="ring-from-direct-values",
        )

        assert processor.hashing_secret == exchange.hashing_secret
        assert processor.encryption_key == derive_transport_encryption_key(exchange)

        result_df = processor.process_dataframe(spark.createDataFrame(sample_data))
        tokens = [row.Token for row in result_df.collect()]

        assert tokens
        payload = _decrypt_v1_payload(tokens[0], processor.encryption_key)
        assert payload["rid"] == "ring-from-direct-values"
        assert payload["ppid"]

    def test_from_exchange_config_derives_transport_key_without_version_fallback(self, monkeypatch):
        """Test exchange-config factory always derives the transport key for resolved configs."""
        resolved_exchange = SimpleNamespace(version=1, hashing_secret=b"resolved-hashing-secret")
        derived_transport_key = b"12345678901234567890123456789012"
        derive_call_count = 0

        def fake_resolve_exchange_config_inputs(*args, **kwargs):
            assert kwargs == {
                "exchange_config_path": "config.json",
                "exchange_config_value": None,
                "private_key_path": "private.pem",
                "private_key_env": "OLT_PRIVATE_KEY",
                "private_key_value": None,
            }
            return resolved_exchange

        def fake_derive_transport_encryption_key(exchange):
            nonlocal derive_call_count
            derive_call_count += 1
            assert exchange is resolved_exchange
            return derived_transport_key

        monkeypatch.setattr(
            token_processor_module,
            "resolve_exchange_config_inputs",
            fake_resolve_exchange_config_inputs,
        )
        monkeypatch.setattr(
            token_processor_module,
            "derive_transport_encryption_key",
            fake_derive_transport_encryption_key,
        )

        processor = OpenLinkTokenProcessor.from_exchange_config(
            exchange_config_path="config.json",
            private_key_path="private.pem",
            private_key_env="OLT_PRIVATE_KEY",
            ring_id="ring-from-config",
        )

        assert derive_call_count == 1
        assert processor.hashing_secret == resolved_exchange.hashing_secret
        assert processor.encryption_key == derived_transport_key

    def test_from_exchange_config_rejects_future_exchange_config_versions(self, tmp_path):
        """Test exchange-config factory rejects unsupported version 2 exchange configs."""
        exchange_config_path, private_key_path = _write_future_exchange_config(tmp_path)

        with pytest.raises(ValueError, match="Unsupported exchange config version '2'. Supported versions: 1."):
            OpenLinkTokenProcessor.from_exchange_config(
                exchange_config_path=exchange_config_path,
                private_key_path=private_key_path,
            )

    def test_initialization_with_empty_hashing_secret(self):
        """Test that initialization fails with empty hashing secret."""
        with pytest.raises(ValueError, match="Hashing secret cannot be empty"):
            OpenLinkTokenProcessor("", "Secret-Encryption-Key-Goes-Here.")

    def test_initialization_with_empty_encryption_key(self):
        """Test that initialization fails with empty encryption key."""
        with pytest.raises(ValueError, match="Encryption key cannot be empty"):
            OpenLinkTokenProcessor("HashingKey", "")

    def test_initialization_with_whitespace_secrets(self):
        """Test that initialization fails with whitespace-only secrets."""
        with pytest.raises(ValueError, match="Hashing secret cannot be empty"):
            OpenLinkTokenProcessor("   ", "Secret-Encryption-Key-Goes-Here.")

    def test_initialization_with_empty_bytes_hashing_secret(self):
        """Test that initialization fails with empty bytes hashing secret."""
        with pytest.raises(ValueError, match="Hashing secret cannot be empty"):
            OpenLinkTokenProcessor(b"", "Secret-Encryption-Key-Goes-Here.")

    def test_initialization_with_empty_bytes_encryption_key(self):
        """Test that initialization fails with empty bytes encryption key."""
        with pytest.raises(ValueError, match="Encryption key cannot be empty"):
            OpenLinkTokenProcessor("HashingKey", b"")

    def test_initialization_with_whitespace_bytes_hashing_secret(self):
        """Test that initialization fails with whitespace-only bytes hashing secret."""
        with pytest.raises(ValueError, match="Hashing secret cannot be empty"):
            OpenLinkTokenProcessor(b"   ", "Secret-Encryption-Key-Goes-Here.")

    def test_initialization_with_whitespace_bytes_encryption_key(self):
        """Test that initialization fails with whitespace-only bytes encryption key."""
        with pytest.raises(ValueError, match="Encryption key cannot be empty"):
            OpenLinkTokenProcessor("HashingKey", b"   ")

    def test_process_dataframe_with_valid_data(self, spark, sample_data):
        """Test processing a DataFrame with valid data and ot.V1 encrypted output."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")

        # Create DataFrame
        df = spark.createDataFrame(sample_data)

        # Process the DataFrame
        result_df = processor.process_dataframe(df)

        # Verify result structure
        assert "RecordId" in result_df.columns
        assert "RuleId" in result_df.columns
        assert "Token" in result_df.columns

        # Collect results
        results = result_df.collect()

        # Should have tokens for each record (5 tokens per record)
        assert len(results) > 0

        # Verify we have multiple rule IDs
        rule_ids = set(row.RuleId for row in results)
        assert len(rule_ids) > 1

        # Encrypted output should use olt.V1 JWE format
        assert any(row.Token.startswith("olt.V1.") for row in results if row.Token)

    def test_process_dataframe_with_alternative_column_names(self, spark):
        """Test processing with alternative column names."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")

        # Create DataFrame with alternative column names
        data = [
            {
                "Id": "test-123",
                "GivenName": "John",
                "Surname": "Doe",
                "ZipCode": "98004",
                "Gender": "Male",
                "DateOfBirth": "2000-01-01",
                "NationalIdentificationNumber": "123-45-6789",
            }
        ]

        df = spark.createDataFrame(data)

        # Process should work with alternative names
        result_df = processor.process_dataframe(df)

        # Verify result
        assert result_df.count() > 0

    def test_process_dataframe_with_missing_required_column(self, spark):
        """Test that processing fails with missing required columns."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")

        # Create DataFrame missing SocialSecurityNumber
        data = [
            {
                "RecordId": "test-123",
                "FirstName": "John",
                "LastName": "Doe",
                "PostalCode": "98004",
                "Sex": "Male",
                "BirthDate": "2000-01-01",
            }
        ]

        df = spark.createDataFrame(data)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Missing required columns"):
            processor.process_dataframe(df)

    def test_process_dataframe_with_none_dataframe(self):
        """Test that processing fails with None DataFrame."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")

        with pytest.raises(ValueError, match="DataFrame cannot be None"):
            processor.process_dataframe(None)

    def test_tokens_are_consistent(self, spark, sample_data):
        """Test that the same input produces the same underlying hashed tokens.

        Encrypted token ciphertext differs due to random IV; decrypt before comparison.
        """
        encryption_key = "Secret-Encryption-Key-Goes-Here."
        processor = OpenLinkTokenProcessor("HashingKey", encryption_key)
        analyzer = OpenLinkTokenOverlapAnalyzer(encryption_key)

        df = spark.createDataFrame(sample_data)
        result1 = processor.process_dataframe(df).collect()
        result2 = processor.process_dataframe(df).collect()

        # Decrypt tokens to compare deterministic hashed content
        decrypted1 = {(r.RecordId, r.RuleId, analyzer._decrypt_token(r.Token)) for r in result1}
        decrypted2 = {(r.RecordId, r.RuleId, analyzer._decrypt_token(r.Token)) for r in result2}
        assert decrypted1 == decrypted2

    def test_different_secrets_produce_different_tokens(self, spark, sample_data):
        """Different hashing secrets should yield different decrypted hashed tokens."""
        key1 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # 32 chars
        key2 = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"  # 32 chars
        processor1 = OpenLinkTokenProcessor("HashingKey1", key1)
        processor2 = OpenLinkTokenProcessor("HashingKey2", key2)
        analyzer1 = OpenLinkTokenOverlapAnalyzer(key1)
        analyzer2 = OpenLinkTokenOverlapAnalyzer(key2)

        df = spark.createDataFrame(sample_data)
        result1 = processor1.process_dataframe(df).collect()
        result2 = processor2.process_dataframe(df).collect()

        decrypted1 = {(r.RecordId, r.RuleId, analyzer1._decrypt_token(r.Token)) for r in result1}
        decrypted2 = {(r.RecordId, r.RuleId, analyzer2._decrypt_token(r.Token)) for r in result2}
        assert decrypted1 != decrypted2

    def test_column_mapping(self, spark):
        """Test that column mapping works correctly."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")

        # Create DataFrame with various column names
        data = [
            {
                "RecordId": "test-1",
                "FirstName": "John",
                "LastName": "Doe",
                "PostalCode": "98004",
                "Sex": "Male",
                "BirthDate": "2000-01-01",
                "SocialSecurityNumber": "123-45-6789",
            }
        ]

        df = spark.createDataFrame(data)

        # Get column mapping
        mapping = processor._get_column_mapping(df)

        # Verify mapping
        assert mapping["RecordId"] == "RecordId"
        assert mapping["FirstName"] == "FirstName"
        assert mapping["LastName"] == "LastName"
        assert mapping["PostalCode"] == "PostalCode"
        assert mapping["Sex"] == "Sex"
        assert mapping["BirthDate"] == "BirthDate"
        assert mapping["SocialSecurityNumber"] == "SocialSecurityNumber"

    def test_validation_with_empty_dataframe(self, spark):
        """Test validation with an empty DataFrame."""
        processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")

        # Create empty DataFrame with correct schema
        schema = StructType(
            [
                StructField("RecordId", StringType(), True),
                StructField("FirstName", StringType(), True),
                StructField("LastName", StringType(), True),
                StructField("PostalCode", StringType(), True),
                StructField("Sex", StringType(), True),
                StructField("BirthDate", StringType(), True),
                StructField("SocialSecurityNumber", StringType(), True),
            ]
        )

        df = spark.createDataFrame([], schema)

        # Should not raise an error during validation
        processor._validate_dataframe(df)

        # Process should return empty DataFrame
        result = processor.process_dataframe(df)
        assert result.count() == 0

    def test_custom_token_definition(self, spark, sample_data):
        """Test using custom token definition with processor."""
        from openlinktoken_pyspark.notebook_helpers import CustomTokenDefinition, TokenBuilder

        # Create a custom T6 token
        t6_token = TokenBuilder("T6").add("last_name", "T|U").add("first_name", "T|U").add("birth_date", "T|D").build()

        custom_definition = CustomTokenDefinition().add_token(t6_token)

        # Create processor with custom definition
        processor = OpenLinkTokenProcessor(
            hashing_secret="test-hash-secret",
            encryption_key="12345678901234567890123456789012",
            token_definition=custom_definition,
        )

        # Create DataFrame
        df = spark.createDataFrame(sample_data)

        # Process with custom tokens
        result = processor.process_dataframe(df)

        # Verify we got T6 tokens (not default T1-T5)
        rule_ids = [row.RuleId for row in result.select("RuleId").distinct().collect()]
        assert "T6" in rule_ids
        assert "T1" not in rule_ids  # Default tokens should not be present

        # Verify we have tokens for each record
        assert result.count() == len(sample_data)  # One T6 token per record

    def test_multiple_custom_tokens(self, spark, sample_data):
        """Test using multiple custom tokens."""
        from openlinktoken_pyspark.notebook_helpers import CustomTokenDefinition, TokenBuilder

        # Create two custom tokens
        t6_token = TokenBuilder("T6").add("last_name", "T|U").add("first_name", "T|U").build()

        t7_token = TokenBuilder("T7").add("last_name", "T|S(0,3)|U").add("birth_date", "T|D").build()

        custom_definition = CustomTokenDefinition().add_token(t6_token).add_token(t7_token)

        # Create processor with multiple custom tokens
        processor = OpenLinkTokenProcessor(
            hashing_secret="test-hash-secret",
            encryption_key="12345678901234567890123456789012",
            token_definition=custom_definition,
        )

        # Create DataFrame
        df = spark.createDataFrame(sample_data)

        # Process with custom tokens
        result = processor.process_dataframe(df)

        # Verify we got both T6 and T7 tokens
        rule_ids = [row.RuleId for row in result.select("RuleId").distinct().collect()]
        assert "T6" in rule_ids
        assert "T7" in rule_ids
        assert "T1" not in rule_ids  # Default tokens should not be present

        # Verify we have 2 tokens per record (T6 and T7)
        assert result.count() == len(sample_data) * 2

    def test_init_with_both_secrets_none(self, spark):
        """Test initialization with both secrets None (plain passthrough mode)."""
        # Both None is allowed - produces plain concatenated tokens
        processor = OpenLinkTokenProcessor(hashing_secret=None, encryption_key=None)

        # Verify it can process a DataFrame
        data = [
            {
                "RecordId": "test-1",
                "FirstName": "John",
                "LastName": "Doe",
                "PostalCode": "98004",
                "Sex": "Male",
                "BirthDate": "2000-01-01",
                "SocialSecurityNumber": "123-45-6789",
            }
        ]
        df = spark.createDataFrame(data)
        result = processor.process_dataframe(df)
        assert result.count() > 0

    def test_init_with_invalid_encryption_key_length(self):
        """Test initialization with wrong encryption key length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid secrets provided"):
            OpenLinkTokenProcessor(
                hashing_secret="test",
                encryption_key="short-key",  # Not 32 bytes
            )

    def test_passthrough_tokenizer_with_encryption_only(self, spark, sample_data):
        """Test processor with encryption but no hashing (passthrough tokenizer)."""
        processor = OpenLinkTokenProcessor(hashing_secret=None, encryption_key="12345678901234567890123456789012")

        df = spark.createDataFrame(sample_data)
        result = processor.process_dataframe(df)

        # Should produce tokens without hashing
        assert result.count() > 0
        # Verify tokens are encrypted (olt.V1 JWE strings)
        token_sample = result.select("Token").first()[0]
        assert isinstance(token_sample, str)
        assert token_sample.startswith("olt.V1.")

    def test_process_with_bad_data_handles_errors(self, spark):
        """Test that processor handles bad data gracefully by returning empty token lists."""
        processor = OpenLinkTokenProcessor("HashingKey", "12345678901234567890123456789012")

        # Create DataFrame with invalid data that will fail token generation
        data = [
            {
                "RecordId": "test-1",
                "FirstName": "John",
                "LastName": "Doe",
                "PostalCode": "INVALID",
                "Sex": "Invalid",
                "BirthDate": "invalid-date",
                "SocialSecurityNumber": "invalid",
            }
        ]
        df = spark.createDataFrame(data)

        # Should not crash, but may produce fewer/no tokens
        result = processor.process_dataframe(df)
        # Result exists but may have zero rows due to validation failures
        assert result is not None


def _write_exchange_config(tmp_path: Path) -> tuple[Path, Path]:
    """Write a current exchange config plus matching sender private key file."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    exchange_config_path = tmp_path / "current.exchange.json"
    exchange_config_path.write_text(
        json.dumps(
            build_exchange_envelope(
                exchange_name="shared-exchange",
                hashing_secret=b"shared-hashing-secret",
                sender_public_pem=sender_public_pem,
                recipient_public_pem=recipient_public_pem,
                curve="P-256",
                created_at="2026-03-12T00:00:00Z",
                exchange_id="exchange-pyspark",
            )
        ),
        encoding="utf-8",
    )
    private_key_path = tmp_path / "sender.private.pem"
    private_key_path.write_bytes(sender_private_pem)
    return exchange_config_path, private_key_path


def _write_future_exchange_config(tmp_path: Path) -> tuple[Path, Path]:
    """Write an unsupported version 2 exchange config plus matching sender private key file."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    payload = {
        "exchangeName": "legacy",
        "hashingSecret": "bGVnYWN5LWhhc2hpbmctc2VjcmV0",
        "hashingSecretEncoding": "base64url",
        "senderKeyFingerprint": public_key_fingerprint(sender_public_pem),
        "recipientKeyFingerprint": public_key_fingerprint(recipient_public_pem),
        "curve": "P-256",
        "createdAt": "2026-03-12T00:00:00Z",
        "exchangeId": "exchange-legacy",
    }
    protected = {
        "typ": EXCHANGE_JWE_TYPE,
        "cty": EXCHANGE_JWE_CONTENT_TYPE,
        "enc": EXCHANGE_JWE_ENCRYPTION,
    }
    envelope = jwe.JWE(
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        protected=json.dumps(protected, separators=(",", ":")),
    )
    for public_pem in (sender_public_pem, recipient_public_pem):
        envelope.add_recipient(
            jwk.JWK.from_pem(public_pem),
            header=json.dumps(
                {
                    "alg": EXCHANGE_JWE_RECIPIENT_ALGORITHM,
                    "kid": fingerprint_to_kid(public_key_fingerprint(public_pem)),
                },
                separators=(",", ":"),
            ),
        )

    exchange_config_path = tmp_path / "future.exchange.json"
    serialized = json.loads(envelope.serialize(compact=False))
    serialized["version"] = 2
    exchange_config_path.write_text(json.dumps(serialized), encoding="utf-8")

    private_key_path = tmp_path / "future.private.pem"
    private_key_path.write_bytes(sender_private_pem)
    return exchange_config_path, private_key_path


def _decrypt_v1_payload(token: str, encryption_key: bytes) -> dict[str, object]:
    """Decrypt an olt.V1 token payload using raw AES key bytes."""
    token_body = token.removeprefix("olt.V1.")
    key_b64 = base64.urlsafe_b64encode(encryption_key).decode("utf-8").rstrip("=")
    jwk_key = jwk.JWK(kty="oct", k=key_b64)
    encrypted_token = jwe.JWE()
    encrypted_token.deserialize(token_body)
    encrypted_token.decrypt(jwk_key)
    return json.loads(encrypted_token.payload.decode("utf-8"))
