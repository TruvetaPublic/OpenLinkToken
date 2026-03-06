# Interoperability Tests

This directory contains tests to ensure correct behavior of the Python CLI implementation of OpenToken.

## CLI Parity Tests

The `cli_parity_test.py` script tests that the Python CLI provides the expected command structure and behavior.

**Python:**
```bash
cd lib/python/opentoken
pip install -r requirements.txt
cd ../opentoken-cli
pip install -r requirements.txt
```

### Running the Tests

```bash
python tools/interoperability/cli_parity_test.py
```

### What is Tested

- Python CLI supports all required commands: `tokenize`, `encrypt`, `decrypt`, `package`, `help`
- Python CLI supports `--help`, `--version`, and `-h` flags
- Each command has help output with required parameters
- The `help` command works for all subcommands
- Command recognition and error handling

## Token Interoperability Tests

The `multi_language_interoperability_test.py` script tests that the Python CLI produces correct token output and consistent metadata.
