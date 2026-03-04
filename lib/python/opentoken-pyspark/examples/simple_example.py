#!/usr/bin/env python3
"""
Simple example demonstrating OpenToken PySpark usage.

This script shows how to use the OpenToken PySpark bridge to generate
tokens from person data in a PySpark DataFrame.

Prerequisites:
    pip install -e ../opentoken-pyspark
    pip install -e .

Usage:
    python simple_example.py
"""

from pyspark.sql import SparkSession

from opentoken_pyspark import OpenTokenProcessor


def main():
    """Main function demonstrating token generation with PySpark."""

    # Initialize Spark session
    print("Initializing Spark session...")
    # Spark 4.0.1+ provides native Java 21 support with improved Arrow integration.
    # The executorEnv.PYTHONPATH configuration ensures pandas/pyarrow are available to executors.
    import os
    import sys

    spark = (
        SparkSession.builder.appName("OpenTokenSimpleExample")
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

    # Initialize OpenToken processor with secrets
    print("\nInitializing OpenToken processor...")
    processor = OpenTokenProcessor(hashing_secret="HashingKey", encryption_key="Secret-Encryption-Key-Goes-Here.")

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
