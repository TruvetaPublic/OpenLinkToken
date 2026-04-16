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

## Rotation Matrix Interoperability Tests

`rotation_matrix_interop_test.py` verifies that the Java and Python
`RotationMatrixGenerator` implementations produce **bit-exact** rotation matrices
for the same IV, rotation count, and dimension. This is the parity gate for T6
inferencing tokens: if the rotation matrices diverge, T6 tokens will never match
across platforms.

### How It Works

The test runs in two steps for each test vector:

1. **Java side** — invokes `RotationMatrixInteropHarness` (in
   `lib/java/openlinktoken-core-ai/src/test/.../tools/`) via the Maven exec plugin.
   The harness generates matrices from the IV and writes them to a temporary JSON
   file.
2. **Python side** — calls
   `openlinktoken_core_ai.tokentransformer.rotation.rotation_matrix_generator.generate()`
   directly in-process.

Both sets of matrices are compared element-by-element with a tolerance of `1e-12`
to accommodate any platform-specific variation in transcendental functions (both
languages use IEEE 754 double precision and the same HMAC-SHA256 + Box-Muller +
Modified Gram-Schmidt algorithm, so results are expected to be identical to
machine epsilon).

### Test Vectors

| IV (truncated) | Rotation count | Dimension |
|---|---|---|
| `test-rotation-iv-2024` | 3 | 4 |
| `different-iv-abc` | 2 | 4 |
| `unicode-iv-éàü` | 1 | 4 |
| `empty-like-iv-` | 5 | 6 |
| `single-char-iv-x` | 1 | 2 |
| `long-iv-aaa…` (64 chars) | 2 | 8 |

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
`lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tools/`.
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
  -Dexec.mainClass=org.openlinktoken.tools.RotationMatrixInteropHarness \
  -Dexec.classpathScope=test \
  "-Dexec.args=my-iv 3 4 /tmp/matrices.json"
cat /tmp/matrices.json
```
