#!/usr/bin/env python3
"""
Simple example demonstrating OpenLinkToken PySpark usage.

This script shows how to use the OpenLinkToken PySpark bridge to generate
tokens from person data in a PySpark DataFrame.

Prerequisites:
    cd /path/to/OpenLinkToken/lib/python/openlinktoken
    uv pip install -e .
    cd ../openlinktoken-pyspark
    uv pip install -e .[spark40]

Usage:
    python simple_example.py

Recommended environment variables:
    OPENTOKEN_EXCHANGE_CONFIG_PATH=/path/to/initiate-exchange-config.json
    OPENTOKEN_PRIVATE_KEY_PATH=/path/to/participant-private-key.pem

Azure Key Vault pattern:
    Keep Azure Key Vault lookups on the driver. Fetch the initiate-exchange
    config JSON and participant private key from Key Vault, then pass those
    resolved values directly to ``from_exchange_config(...)``. The sender and
    recipient public keys belong in the generated exchange config; if you also
    store them in Key Vault, use them for
    exchange creation, rotation, or validation rather than passing them directly
    to the PySpark bridge.

    Example:
        import os

        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        vault = SecretClient(
            vault_url=os.environ["AZURE_KEY_VAULT_URL"],
            credential=DefaultAzureCredential(),
        )
        exchange_config_json = vault.get_secret("openlinktoken-initiate-exchange-config").value
        participant_private_key_pem = vault.get_secret("openlinktoken-participant-private-key-pem").value

        # Optional: public keys can stay in Key Vault for exchange management.
        sender_public_key_pem = vault.get_secret("openlinktoken-sender-public-key-pem").value
        recipient_public_key_pem = vault.get_secret("openlinktoken-recipient-public-key-pem").value

        processor = OpenLinkTokenProcessor.from_exchange_config(
            exchange_config_value=exchange_config_json,
            private_key_value=participant_private_key_pem,
        )

Optional direct-secret environment variables:
    OPENTOKEN_HASHING_SECRET=...
    OPENTOKEN_ENCRYPTION_KEY=...
"""

import os
import sys

from pyspark.sql import SparkSession

from openlinktoken_pyspark import OpenLinkTokenProcessor


def create_processor() -> OpenLinkTokenProcessor:
    """Create a processor using exchange-config inputs when available."""
    exchange_config_path = os.environ.get("OPENTOKEN_EXCHANGE_CONFIG_PATH")
    private_key_path = os.environ.get("OPENTOKEN_PRIVATE_KEY_PATH")
    private_key_env = "OPENTOKEN_PRIVATE_KEY" if os.environ.get("OPENTOKEN_PRIVATE_KEY") else None

    if exchange_config_path or private_key_path or private_key_env:
        print(
            "Using exchange-config flow; secrets are resolved on the driver before Spark workers receive derived bytes."
        )
        return OpenLinkTokenProcessor.from_exchange_config(
            exchange_config_path=exchange_config_path,
            private_key_path=private_key_path,
            private_key_env=private_key_env,
        )

    hashing_secret = os.environ.get("OPENTOKEN_HASHING_SECRET")
    encryption_key = os.environ.get("OPENTOKEN_ENCRYPTION_KEY")
    if hashing_secret:
        print("Using direct-secret flow from environment variables.")
        return OpenLinkTokenProcessor(hashing_secret=hashing_secret, encryption_key=encryption_key)

    raise RuntimeError(
        "Set OPENTOKEN_EXCHANGE_CONFIG_PATH with OPENTOKEN_PRIVATE_KEY_PATH or OPENTOKEN_PRIVATE_KEY. "
        "For direct-secret usage, set OPENTOKEN_HASHING_SECRET and OPENTOKEN_ENCRYPTION_KEY."
    )


def main():
    """Main function demonstrating token generation with PySpark."""

    # Initialize Spark session
    print("Initializing Spark session...")
    # Spark 4.0.1+ provides native Java 21 support with improved Arrow integration.
    # The executorEnv.PYTHONPATH configuration ensures pandas/pyarrow are available to executors.
    spark = (
        SparkSession.builder.appName("OpenLinkTokenSimpleExample")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.executorEnv.PYTHONPATH", os.pathsep.join(sys.path))
        .getOrCreate()
    )

    print(f"Spark version: {spark.version}\n")

    # Create sample data
    print("Creating sample data...")
    sample_data = [
        {
            "RecordId": "test-001",
            "FirstName": "John",
            "LastName": "Doe",
            "PostalCode": "98004",
            "Sex": "Male",
            "BirthDate": "2000-01-01",
            "SocialSecurityNumber": "123-45-6789",
        },
        {
            "RecordId": "test-002",
            "FirstName": "Jane",
            "LastName": "Smith",
            "PostalCode": "15635",
            "Sex": "Female",
            "BirthDate": "1995-06-15",
            "SocialSecurityNumber": "987-65-4321",
        },
    ]

    # Create DataFrame
    df = spark.createDataFrame(sample_data)

    print("Input DataFrame:")
    df.show(truncate=False)

    # Initialize OpenLinkToken processor
    print("\nInitializing OpenLinkToken processor...")
    processor = create_processor()

    # Generate tokens
    print("Generating tokens...")
    tokens_df = processor.process_dataframe(df)

    # Display results
    print("\nGenerated Tokens:")
    tokens_df.show(truncate=False)

    # Show token count by rule
    print("\nToken Count by RuleId:")
    tokens_df.groupBy("RuleId").count().orderBy("RuleId").show()

    # Show tokens for first record
    first_record_id = sample_data[0]["RecordId"]
    print(f"\nAll tokens for RecordId: {first_record_id}")
    tokens_df.filter(tokens_df.RecordId == first_record_id).show(truncate=False)

    # Stop Spark session
    print("\nStopping Spark session...")
    spark.stop()

    print("Example completed successfully!")


if __name__ == "__main__":
    main()
