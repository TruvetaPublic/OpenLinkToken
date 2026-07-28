# Core AI Namespace Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move core-ai implementation code into dedicated Java and Python namespaces while preserving all ML1/rotation behavior and published artifact names.

**Architecture:** Java implementation classes will live under `org.openlinktoken.core.ai`, while base contracts and attributes remain under `org.openlinktoken`. Python modules will move from `openlinktoken_core_ai` to `openlinktoken.core.ai`; the `openlinktoken-core-ai` distribution name and existing entry-point groups remain unchanged. ServiceLoader and Python entry-point registrations will resolve the new implementation paths.

**Tech Stack:** Java 17+ source compiled with Maven, Python 3.10-3.13, setuptools, uv workspace, pytest, JUnit, ServiceLoader, Python entry points, ONNX Runtime, and repository `prek` hooks.

## Global Constraints

- Java namespace: `org.openlinktoken.core.ai`.
- Python import namespace: `openlinktoken.core.ai`.
- Keep Maven artifact and Python distribution names unchanged.
- Keep `org.openlinktoken.tokens` contracts and `org.openlinktoken.attributes` classes in the base module.
- Perform a clean migration; do not add compatibility wrappers or aliases for old implementation paths.
- Do not change ML1 payload construction, inference, rotation, hashing, quantization, assets, defaults, or serialized output.
- Java code must use imports and short class names, never fully qualified class names in executable code.
- Python must use the shared environment at `/home/vscode/.local/share/openlinktoken/.venv`.
- After edits, run `prek run --files <exact changed files>`.

---

### Task 1: Relocating Java core-ai implementation packages

**Files:**
- Move:
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/ML1InferenceConfig.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/ML1InferenceConfig.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/ML1OnnxSignatureGenerator.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/ML1OnnxSignatureGenerator.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/OnnxML1SignatureProvider.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/OnnxML1SignatureProvider.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/RotationConfig.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/RotationConfig.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/definitions/ML1Token.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/definitions/ML1Token.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/EmbeddingRotator.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/EmbeddingRotator.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/EmbeddingTransformer.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/EmbeddingTransformer.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/RotationEmbeddingTransformer.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationEmbeddingTransformer.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/RotationMatrixGenerator.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationMatrixGenerator.java`
  - `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/RotationQuantizer.java` -> `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationQuantizer.java`
- Move tests:
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tokens/OnnxML1SignatureProviderTest.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokens/OnnxML1SignatureProviderTest.java`
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tools/Ml1InteropHarness.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tools/Ml1InteropHarness.java`
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tools/RotationMatrixInteropHarness.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tools/RotationMatrixInteropHarness.java`
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tokentransformer/rotation/EmbeddingRotatorTest.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokentransformer/rotation/EmbeddingRotatorTest.java`
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tokentransformer/rotation/RotationEmbeddingTransformerTest.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationEmbeddingTransformerTest.java`
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tokentransformer/rotation/RotationMatrixGeneratorTest.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationMatrixGeneratorTest.java`
  - `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/tokentransformer/rotation/RotationQuantizerTest.java` -> `lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationQuantizerTest.java`
- Modify every moved Java file’s `package` declaration and import of another moved core-ai class.
- Modify: `lib/java/openlinktoken-core-ai/src/main/resources/META-INF/services/org.openlinktoken.tokens.Token`
- Modify: `lib/java/openlinktoken-core-ai/src/main/resources/META-INF/services/org.openlinktoken.tokens.InferenceSignatureProvider`

**Interfaces:**
- Consumes: Base-module contracts in `org.openlinktoken.attributes` and `org.openlinktoken.tokens`.
- Produces: Java implementation classes discoverable at `org.openlinktoken.core.ai.tokens.*` and `org.openlinktoken.core.ai.tokentransformer.rotation.*`; ServiceLoader entries that resolve those classes.

- [ ] **Step 1: Move the Java production and test files without changing contents.**

```bash
rtk mkdir -p lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/definitions \
  lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation \
  lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokens \
  lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tools \
  lib/java/openlinktoken-core-ai/src/test/java/org/openlinktoken/core/ai/tokentransformer/rotation
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/ML1InferenceConfig.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/ML1InferenceConfig.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/ML1OnnxSignatureGenerator.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/ML1OnnxSignatureGenerator.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/OnnxML1SignatureProvider.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/OnnxML1SignatureProvider.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/RotationConfig.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/RotationConfig.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokens/definitions/ML1Token.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/definitions/ML1Token.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/EmbeddingRotator.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/EmbeddingRotator.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/EmbeddingTransformer.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/EmbeddingTransformer.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/RotationEmbeddingTransformer.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationEmbeddingTransformer.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/RotationMatrixGenerator.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationMatrixGenerator.java
rtk git mv lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/tokentransformer/rotation/RotationQuantizer.java lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationQuantizer.java
```

Move the seven listed test/harness files with the same `rtk git mv` pattern,
placing each under the matching `org/openlinktoken/core/ai` directory.

- [ ] **Step 2: Update package declarations and moved-class imports.**

Replace declarations as follows:

```java
package org.openlinktoken.core.ai.tokens;
package org.openlinktoken.core.ai.tokens.definitions;
package org.openlinktoken.core.ai.tokentransformer.rotation;
package org.openlinktoken.core.ai.tools;
```

In moved files, update only imports that refer to moved core-ai classes:

```java
import org.openlinktoken.core.ai.tokens.ML1InferenceConfig;
import org.openlinktoken.core.ai.tokens.ML1OnnxSignatureGenerator;
import org.openlinktoken.core.ai.tokens.RotationConfig;
import org.openlinktoken.core.ai.tokens.definitions.ML1Token;
import org.openlinktoken.core.ai.tokentransformer.rotation.RotationEmbeddingTransformer;
```

Keep imports of `org.openlinktoken.attributes.*` and base
`org.openlinktoken.tokens.*` contracts unchanged.

- [ ] **Step 3: Update Java ServiceLoader entries.**

The implementation lines must be exactly:

```text
org.openlinktoken.core.ai.tokens.definitions.ML1Token
```

and:

```text
org.openlinktoken.core.ai.tokens.OnnxML1SignatureProvider
```

Do not rename either service interface file.

- [ ] **Step 4: Run the focused Java module tests.**

Run:

```bash
cd lib/java && rtk mvn -pl openlinktoken-core-ai -am test
```

Expected: Maven compiles both modules, ServiceLoader-backed ML1 tests load the
new provider, and all core-ai JUnit tests pass.

- [ ] **Step 5: Commit the Java namespace migration.**

```bash
rtk git add lib/java/openlinktoken-core-ai
rtk git commit -m "refactor(java): isolate core-ai namespace" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Relocating Python core-ai imports and package metadata

**Files:**
- Move all files under `lib/python/openlinktoken-core-ai/src/main/openlinktoken_core_ai/` to `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/`.
- Move all files under `lib/python/openlinktoken-core-ai/src/test/openlinktoken_core_ai/` to `lib/python/openlinktoken-core-ai/src/test/openlinktoken/core/ai/`.
- Create: `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/__init__.py`
- Modify: `lib/python/openlinktoken-core-ai/pyproject.toml`
- Modify: `lib/python/openlinktoken-core-ai/setup.py`
- Modify all moved Python source and test imports.

**Interfaces:**
- Consumes: Existing base Python modules under `openlinktoken.attributes` and `openlinktoken.tokens`.
- Produces: Importable `openlinktoken.core.ai` modules, package data under `openlinktoken.core.ai.tokens`, and entry points targeting the new namespace.

- [ ] **Step 1: Create the regular-package parent and move the Python source tree.**

```bash
rtk mkdir -p lib/python/openlinktoken-core-ai/src/main/openlinktoken/core \
  lib/python/openlinktoken-core-ai/src/test/openlinktoken/core
rtk git mv lib/python/openlinktoken-core-ai/src/main/openlinktoken_core_ai lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai
rtk git mv lib/python/openlinktoken-core-ai/src/test/openlinktoken_core_ai lib/python/openlinktoken-core-ai/src/test/openlinktoken/core/ai
```

Create `src/main/openlinktoken/core/__init__.py` with a concise package
docstring. Preserve the existing `__init__.py` files in the moved source and
test subpackages.

- [ ] **Step 2: Update all moved Python module imports and resource references.**

Replace the old prefix in the moved source and test code:

```python
from openlinktoken.core.ai.ml1_signature_provider import OnnxML1SignatureProvider
from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig
from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import ML1OnnxSignatureGenerator
from openlinktoken.core.ai.tokens.rotation_config import RotationConfig
from openlinktoken.core.ai.tokentransformer.rotation.rotation_embedding_transformer import (
    RotationEmbeddingTransformer,
)
```

In the moved `ml1_onnx_signature_generator.py`, change
`importlib.resources.files("openlinktoken_core_ai.tokens")` to
`importlib.resources.files("openlinktoken.core.ai.tokens")`. Do not change
resource filenames or ONNX loading behavior.

- [ ] **Step 3: Update Python packaging metadata and entry points.**

In `lib/python/openlinktoken-core-ai/pyproject.toml`, change the two entry
point targets to:

```toml
ml1 = "openlinktoken.core.ai.ml1_signature_provider:OnnxML1SignatureProvider"
ml1_token = "openlinktoken.core.ai.tokens.ml1_token:ML1Token"
```

In `setup.py`, change `INFERENCING_ASSETS_PKG`,
`package_data`, and both `entry_points` targets to
`openlinktoken.core.ai.tokens` and the matching new module paths. Keep
`find_packages(where="src/main")`, the distribution name, and dependency
versions unchanged.

- [ ] **Step 4: Run focused Python package and CLI tests.**

Run with the shared environment:

```bash
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate
cd lib/python/openlinktoken-core-ai && rtk pytest -q
cd ../openlinktoken-cli && rtk pytest -q src/test/openlinktoken_cli/package_command_zip_test.py src/test/openlinktoken_cli/processor/person_attributes_processor_test.py
```

Expected: core-ai tests import from `openlinktoken.core.ai`, CLI tests resolve
ML1 and rotation configuration, and no module-not-found errors occur.

- [ ] **Step 5: Commit the Python namespace migration.**

```bash
rtk git add lib/python/openlinktoken-core-ai
rtk git commit -m "refactor(python): isolate core-ai namespace" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: Updating integration tooling and documentation

**Files:**
- Modify: `lib/python/openlinktoken-cli/src/main/openlinktoken_cli/commands/package_command.py`
- Modify: `lib/python/openlinktoken-cli/src/main/openlinktoken_cli/commands/tokenize_command.py`
- Modify: `lib/python/openlinktoken-cli/src/main/openlinktoken_cli/processor/person_attributes_processor.py`
- Modify: `lib/python/openlinktoken-cli/src/test/openlinktoken_cli/package_command_zip_test.py`
- Modify: `tools/interoperability/rotation_matrix_interop_test.py`
- Modify: `tools/interoperability/README.md`
- Modify: `docs/rotation-matrix-support.md`
- Modify: `pages/reference/token-registration.md`
- Modify any additional tracked documentation or source file found by the stale-reference search.

**Interfaces:**
- Consumes: New Java and Python core-ai import paths from Tasks 1 and 2.
- Produces: Repository examples, interop tools, CLI code, and registration docs that all describe and exercise the new namespaces.

- [ ] **Step 1: Update CLI and interoperability imports.**

Change every remaining Python import of the old prefix to the corresponding
`openlinktoken.core.ai` module. The affected CLI imports are the ML1 and
rotation configuration imports in `package_command.py`,
`tokenize_command.py`, and `person_attributes_processor.py`; the CLI test
imports `RotationConfig` from the same new namespace.

Update the interoperability test import to:

```python
from openlinktoken.core.ai.tokentransformer.rotation.rotation_matrix_generator import generate
```

- [ ] **Step 2: Update Java and Python documentation references.**

In `docs/rotation-matrix-support.md`, replace every old Java implementation
path with its `org/openlinktoken/core/ai` source path and every old Python
source path with `openlinktoken/core/ai`. Update prose that names the old
Java package or Python import namespace.

In `pages/reference/token-registration.md`, change the ML1 ServiceLoader
implementation entry to:

```text
org.openlinktoken.core.ai.tokens.definitions.ML1Token
```

Update `tools/interoperability/README.md` to show the new Python import path.
Do not alter token IDs, registration interface names, or algorithm examples.

- [ ] **Step 3: Prove no stale implementation namespace remains.**

Run:

```bash
rtk rg "openlinktoken_core_ai|org\.openlinktoken\.tokens\.definitions\.ML1Token|org\.openlinktoken\.tokens\.OnnxML1SignatureProvider|org\.openlinktoken\.tokentransformer\.rotation" \
  lib docs pages tools
```

Expected: no old implementation imports, package declarations, ServiceLoader
entries, or source-path documentation remain. Base-module references such as
`org.openlinktoken.tokens.InferenceSignatureProvider` are expected and must
not be changed.

- [ ] **Step 4: Run the interoperability checks.**

Run:

```bash
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate
rtk python tools/interoperability/rotation_matrix_interop_test.py
```

Expected: the existing Java/Python rotation matrix comparison passes with its
current tolerance, demonstrating that namespace edits did not alter numeric
behavior.

- [ ] **Step 5: Commit integration and documentation updates.**

```bash
rtk git add lib/python/openlinktoken-cli tools/interoperability docs/rotation-matrix-support.md pages/reference/token-registration.md
rtk git commit -m "docs: update core-ai namespace references" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: Running final repository verification

**Files:**
- Verify all files changed by Tasks 1-3.
- Modify only files that fail an existing formatter or hook, preserving the
  approved namespace and behavior.

**Interfaces:**
- Consumes: Completed Java/Python namespace migration and updated registrations.
- Produces: A clean, buildable, hook-compliant tree with no stale namespace references.

- [ ] **Step 1: Inspect the final change set.**

```bash
rtk git status --short
rtk git diff --stat develop...HEAD
rtk git diff --check develop...HEAD
```

Expected: only core-ai namespace source, tests, packaging, registrations,
tooling, docs, and the committed design/plan files are present; whitespace
validation reports no errors.

- [ ] **Step 2: Run the Java module test suite again from the final tree.**

```bash
cd lib/java && rtk mvn -pl openlinktoken-core-ai -am test
```

Expected: all base-module and core-ai tests pass, including discovery of
`org.openlinktoken.core.ai.tokens.OnnxML1SignatureProvider` and the new token
definition package.

- [ ] **Step 3: Run the Python core-ai and affected CLI suites again.**

```bash
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate
cd lib/python/openlinktoken-core-ai && rtk pytest -q
cd ../openlinktoken-cli && rtk pytest -q src/test/openlinktoken_cli/package_command_zip_test.py src/test/openlinktoken_cli/processor/person_attributes_processor_test.py
```

Expected: all selected tests pass with imports resolved from
`openlinktoken.core.ai`.

- [ ] **Step 4: Run `prek` against the exact changed files.**

From the repository root, pass every changed path reported by
`rtk git status --short`:

```bash
rtk prek run --files <exact-changed-path-1> <exact-changed-path-2> <exact-changed-path-3>
```

Expected: all configured hooks pass. If a hook modifies a file, re-run it
with the complete updated changed-file list and inspect the resulting diff.

- [ ] **Step 5: Confirm the final namespace contract.**

```bash
rtk rg "package org\.openlinktoken\.core\.ai|openlinktoken\.core\.ai|openlinktoken_core_ai" lib docs pages tools
```

Expected: implementation declarations/imports and documentation use the new
namespaces; the old underscore prefix produces no matches. Confirm Maven's
`<artifactId>` and Python's `name` field both remain
`openlinktoken-core-ai`.

- [ ] **Step 6: Commit any hook-only corrections, if needed.**

```bash
rtk git add <exact-hook-corrected-paths>
rtk git commit -m "chore: apply namespace migration hook fixes" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Skip this step when no hook-only corrections are made.
