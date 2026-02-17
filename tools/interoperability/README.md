# Multi-Language Interoperability Tests

This directory contains tests that validate compatibility and consistency between the Java, Python, and Node.js implementations of OpenToken.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Java 21 SDK or higher (JAR output compatible with Java 11)
- Node.js 20.x LTS or higher
- npm (Node package manager)

## Test Categories

- **Token Generation Compatibility**: Verify all three implementations generate identical tokens for the same input
- **Data Format Compatibility**: Ensure serialized data can be read cross-platform
- **Encryption/Decryption Compatibility**: Validate encrypted tokens from all implementations can be decrypted using the same decryptor tool
- **Metadata Consistency**: Check that metadata formats are consistent across all implementations

## Running Tests

These tests require Java, Python, and Node.js environments to be properly configured.

```bash
# Run all interoperability tests
python -m pytest tools/interoperability/ -v

# Run the multilanguage_interoperability_test.py file, which will run all tests
python3 tools/interoperability/multilanguage_interoperability_test.py
```

## Test Data

Shared test data and expected outputs are stored in the `test_data/` subdirectory.
