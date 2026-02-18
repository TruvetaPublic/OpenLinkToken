# Interoperability Tests

This directory contains tests to ensure parity between Java and Python implementations of OpenToken.

## CLI Parity Tests

The `cli_parity_test.py` script tests that Java and Python CLIs provide identical command structures and behavior.

- Java 21 SDK or higher (JAR output compatible with Java 17)

**Java:**
```bash
cd lib/java
mvn clean package -DskipTests
```

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

- Both CLIs support the same commands: `tokenize`, `encrypt`, `decrypt`, `package`, `help`
- Both CLIs support `--help`, `--version`, and `-h` flags
- Each command has consistent help output with required parameters
- The `help` command works for all subcommands
- Command recognition and error handling is consistent

## Token Interoperability Tests

The `java_python_interoperability_test.py` script tests that Java and Python produce byte-identical tokens for the same input.
