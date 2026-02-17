# Interoperability Tests

This directory contains tests that validate compatibility and consistency between the Java and Python implementations of OpenToken.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

- Java 21 SDK or higher (JAR output compatible with Java 17)

## Test Categories

- **Token Generation Compatibility**: Verify both implementations generate identical tokens for the same input
- **Data Format Compatibility**: Ensure serialized data can be read cross-platform
- **Encryption/Decryption Compatibility**: Validate encrypted tokens from both implementations can be decrypted using the same decryptor tool
- **Metadata Consistency**: Check that metadata formats are consistent between implementations

## Running Tests

These tests require both Java and Python environments to be properly configured.

```bash
# Run all interoperability tests
python -m pytest tools/interoperability/ -v

# Run the java_python_interoperability_test.py file, which will run all tests
python3 tools/interoperability/java_python_interoperability_test.py
```

## Test Data

Shared test data and expected outputs are stored in the `test_data/` subdirectory.
