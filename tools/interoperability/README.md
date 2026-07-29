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

The `multi_language_interoperability_test.py` script executes four parity checks:

- **Unit-level fixture parity:** verifies that the Python library reproduces the
  same deterministic token fixture values already asserted by the Java
  `TokenGeneratorIntegrationTest`
- **Java harness vs Python CLI parity:** invokes a thin Java harness built on the
  Java core library API and compares its T1-T5 `tokenize`-compatible CSV output
  against the Python CLI `tokenize` command with ML1 inferencing disabled
- **Java ML1 harness vs Python ML1 provider parity:** invokes
  `Ml1InteropHarness` from the Java core-AI module and compares its
  `RecordId`-to-signature JSON against the Python ML1 provider
- **Python ML1 provider vs Python CLI parity:** runs the Python CLI `tokenize`
  command with ML1 inferencing enabled and compares its emitted `ML1` CSV rows
  against the direct Python provider by `RecordId`; the provider-vs-Java check
  above establishes the cross-language link without launching a second Java
  ONNX process

The script also verifies that the Python CLI metadata file contains the expected
fields for tokenized output.

### Running the Tests

```bash
cd <repo-root>/lib/java
mvn -pl openlinktoken -DskipTests test-compile
cd <repo-root>
python tools/interoperability/multi_language_interoperability_test.py
```

The ML1 checks create a temporary two-row CSV containing one valid person and
one invalid birth date. They send both rows through the Java
`org.openlinktoken.core.ai.tools.Ml1InteropHarness` and Python
`ML1OnnxSignatureProvider`; the CLI check additionally runs the complete
Python `tokenize` path and compares the emitted `ML1` rows with a direct
provider run. The provider-vs-Java and CLI-vs-provider checks together compare
the complete `RecordId`-to-signature mapping, including the expected `null` or
missing CLI row for the invalid input. The Java side explicitly uses the
bundled `model.onnx` and `tokenizer.json` assets with the default rotation
configuration. The CLI harness provisions the same default rotation IV in its
exchange config so its output uses identical rotation settings. The script installs the Java
`openlinktoken-core-ai` reactor artifacts before running the test-scope harness,
so the comparison uses the current source tree rather than a stale local Maven
artifact.

To run only the ML1 parity test:

```bash
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate
python -m pytest tools/interoperability/multi_language_interoperability_test.py -k ml1 -v
```

## Rotation Matrix Interoperability Tests

`rotation_matrix_interop_test.py` verifies that the Java and Python
`RotationMatrixGenerator` implementations produce deterministic rotation
matrices within a tolerance for the same IV, rotation count, and dimension.
This is the parity gate for ML1 inferencing tokens: if the rotation matrices
diverge beyond the tolerance, ML1 tokens will not match across platforms.

### How It Works

The test runs in two steps for each test vector:

1. **Java side** — invokes `RotationMatrixInteropHarness` (in
   `lib/java/openlinktoken-core-ai/src/test/.../core/ai/tools/`) via the Maven exec plugin.
   The harness generates matrices from the IV and writes them to a temporary JSON
   file.
2. **Python side** — calls
   `openlinktoken.core.ai.tokentransformer.rotation.rotation_matrix_generator.generate()`
   directly in-process.

Both sets of matrices are compared element-by-element with a tolerance of
`1e-12` to accommodate platform-specific variation in transcendental functions.
Java uses Householder QR and Python uses NumPy QR, followed by matching
diagonal-sign normalization and determinant correction. Both implementations
use IEEE 754 double precision, HMAC-SHA256 counter input, and Box-Muller
sampling; the test does not promise bit-for-bit equality on every platform.

### Test Vectors

| IV (truncated)            | Rotation count | Dimension |
| ------------------------- | -------------- | --------- |
| `test-rotation-iv-2024`   | 3              | 4         |
| `different-iv-abc`        | 2              | 4         |
| `unicode-iv-éàü`          | 1              | 4         |
| `empty-like-iv-`          | 5              | 6         |
| `single-char-iv-x`        | 1              | 2         |
| `long-iv-aaa…` (64 chars) | 2              | 8         |

### Prerequisites

Java test classes must be compiled before the test runs. The test script handles
this automatically via a `mvn test-compile` invocation on the first call, but you
can also compile manually:

```bash
cd <repo-root>/lib/java
mvn -pl openlinktoken-core-ai -am -DskipTests test-compile
```

### Running the Tests

From the repository root with the shared Python virtual environment active:

```bash
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate
python tools/interoperability/rotation_matrix_interop_test.py
```

Or via pytest (picks up `TestRotationMatrixInterop` automatically):

```bash
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate
pytest tools/interoperability/rotation_matrix_interop_test.py -v
```

### What Is Tested

- **Cross-language parity**: Java and Python produce identical matrices (within
  `1e-12`) for every test vector
- **Structural correctness**: Python matrices satisfy `Q @ Q^T = I` and
  `det(Q) = +1` (fixture test, no Java build required)

### Java Harness

The Java side of the test is `RotationMatrixInteropHarness.java` in
`lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tools/`.
It accepts four arguments — `<iv> <rotation_count> <dimension> <output.json>` —
and writes a JSON file in the format:

```json
{
  "iv": "...",
  "rotation_count": 3,
  "dimension": 4,
  "matrices": [
    [[r0c0, r0c1, ...], [r1c0, ...], ...],
    ...
  ]
}
```

The harness can also be run standalone for manual spot-checks:

```bash
cd <repo-root>/lib/java
mvn -pl openlinktoken-core-ai -DskipTests \
  org.codehaus.mojo:exec-maven-plugin:3.5.0:java \
  -Dexec.mainClass=org.openlinktoken.core.ai.tools.RotationMatrixInteropHarness \
  -Dexec.classpathScope=test \
  "-Dexec.args=my-iv 3 4 /tmp/matrices.json"
cat /tmp/matrices.json
```
