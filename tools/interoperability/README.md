# Interoperability Tests

This directory contains interoperability checks for the Java core library and the
Python CLI implementation of Open Link Token.

## CLI Parity Tests

The `cli_parity_test.py` script tests that the Python CLI provides the expected
command structure and behavior.

**Python:**

```bash
cd lib/python/openlinktoken
uv pip install -r requirements.txt
cd ../openlinktoken-cli
uv pip install -r requirements.txt
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

The `multi_language_interoperability_test.py` script executes two parity checks:

- **Unit-level fixture parity:** verifies that the Python library reproduces the
  same deterministic token fixture values already asserted by the Java
  `TokenGeneratorIntegrationTest`
- **Java harness vs Python CLI parity:** invokes a thin Java harness built on the
  Java core library API and compares its `tokenize`-compatible CSV output against
  the Python CLI `tokenize` command

The script also verifies that the Python CLI metadata file contains the expected
fields for tokenized output.

### Running the Tests

```bash
cd <repo-root>/lib/java
mvn -pl openlinktoken -DskipTests test-compile
cd <repo-root>
python tools/interoperability/multi_language_interoperability_test.py
```
