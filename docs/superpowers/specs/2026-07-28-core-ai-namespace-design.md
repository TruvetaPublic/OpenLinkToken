# Core AI Namespace Migration Design

## Status

Approved design for implementation planning.

## Goal

Give the core-ai implementation its own import namespace in both supported
languages without changing token algorithms, serialized token output, model
assets, runtime defaults, or published artifact names.

The Java namespace will be `org.openlinktoken.core.ai`. The Python import
namespace will be `openlinktoken.core.ai`. This is a clean migration: old
implementation package and import paths are removed rather than retained as
compatibility wrappers.

## Scope

### Java

Move core-ai implementation classes and their tests into these packages:

- `org.openlinktoken.core.ai.tokens`
  - ML1 inference configuration
  - ONNX signature generation
  - ONNX inference provider
  - rotation configuration
- `org.openlinktoken.core.ai.tokens.definitions`
  - `ML1Token`
- `org.openlinktoken.core.ai.tokentransformer.rotation`
  - embedding projection, rotation, and quantization implementation
- `org.openlinktoken.core.ai.tools`
  - test-only interoperability harnesses

Core contracts remain in the base module. In particular,
`org.openlinktoken.tokens.InferenceSignatureProvider`,
`org.openlinktoken.tokens.InferenceBatchResult`, and
`org.openlinktoken.tokens.TokenGeneratorResult` are not moved.
Attribute classes also remain under `org.openlinktoken.attributes`.

Update Java source paths, declarations, imports, tests, documentation, and
ServiceLoader registrations. The service interface files remain the same:

- `META-INF/services/org.openlinktoken.tokens.Token`
- `META-INF/services/org.openlinktoken.tokens.InferenceSignatureProvider`

Their implementation entries will point to the new core-ai classes.

### Python

Keep the distribution name `openlinktoken-core-ai`, but move its source and
tests from `openlinktoken_core_ai` to `openlinktoken/core/ai`. The resulting
modules include:

- `openlinktoken.core.ai.ml1_signature_provider`
- `openlinktoken.core.ai.tokens`
- `openlinktoken.core.ai.tokentransformer.rotation`

Update all internal imports, CLI imports, interoperability tooling, test
paths, entry points, package discovery, package data, and resource lookup.
The ONNX assets will remain bundled under the new
`openlinktoken.core.ai.tokens` package.

## Runtime and Packaging Behavior

The Maven artifact and Python wheel names stay unchanged. Java ServiceLoader
continues discovering the same core interfaces, but now instantiates the
implementation classes from `org.openlinktoken.core.ai`. Python entry points
continue using the existing entry-point groups and `ml1` names, but target
`openlinktoken.core.ai` modules.

No compatibility aliases will be added. Consumers must update imports to the
new namespaces. This keeps the ownership boundary explicit and avoids two
public paths for the same implementation.

## Verification

Validate the migration with:

1. Core-ai Java compilation and tests, including ServiceLoader-backed ML1
   coverage and interoperability harness compilation.
2. Core-ai Python tests and CLI tests that import core-ai configuration.
3. Existing cross-language and interoperability checks where applicable.
4. Repository searches confirming that stale implementation imports and
   package declarations are absent.
5. `prek run --files` using the exact changed paths.

The verification must demonstrate unchanged ML1 and rotation behavior. Any
missing import, package-data, or registration error must fail visibly rather
than being masked by fallback aliases.

## Non-Goals

- Changing Maven or Python distribution coordinates.
- Moving base Open Link Token interfaces or attributes.
- Changing ML1 payload construction, inference, rotation, hashing, or
  quantization behavior.
- Adding backward-compatible wrappers for old implementation namespaces.
