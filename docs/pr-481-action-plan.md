# PR #481 Action Plan

## Purpose

Make the crypto-suite and post-quantum exchange changes simple, pragmatic, and
explicit about the Java/Python parity boundary before merging PR #481.

This plan is intentionally implementation-oriented. It identifies the decisions
that block merge, the smallest changes needed to address them, and the evidence
required to close the work.

## Recommended decisions

1. **Derive a distinct v2 token transport key.**
   The v2 exchange-envelope content-encryption key should protect only the
   exchange payload. The token transport key should be derived from it with
   HKDF and a versioned domain-separation label, matching the key-separation
   model already used by v1.

2. **Use standard JWE JSON serialization for v2 with explicit custom
   key-management algorithms.**
   Version 2 must use the standard general JWE JSON members so API-side JWE
   implementations can parse the envelope shape. The ML-KEM and hybrid
   algorithms remain custom profiles and require explicit handlers in every
   implementation that creates or decrypts v2 envelopes. Do not add a second
   ML-KEM implementation in Java as part of this change unless Java v2
   exchange consumption is a supported requirement; retain Java marker
   classes only when the synchronization tooling requires them.

3. **Treat omitted optional suite arguments consistently.**
   When an API accepts an optional crypto suite, both languages should use the
   default suite when it is omitted. Invalid non-null suite values must still
   fail immediately.

4. **Freeze the JWE-compatible v2 profile before external consumption.**
   Existing v2 test fixtures and generated artifacts can be regenerated after
   the key-derivation change. Before changing an externally consumed v2
   envelope, preserve and test the protected-header fields, custom `alg`
   identifiers, `encrypted_key` packing, KDF transcript, and transport-key
   derivation contract.

## Work items

### A1. Separate v2 envelope and token transport keys

**Priority:** P0 - merge blocker

**Problem:** `decrypt_exchange_envelope_v2()` currently returns the AES-GCM
content key that decrypts the exchange payload, and consumers reuse that same
key for token encryption.

**Actions:**

- Define a v2-specific transport-key derivation contract:
  - HKDF-SHA256
  - 32-byte output
  - exchange ID as the salt
  - a distinct, versioned `info` value such as
    `openlinktoken:token-encryption:v2`
- Keep the envelope content key internal to the v2 envelope implementation.
- Return or expose only the derived transport key to exchange-config consumers.
- Remove the unconditional pass-through behavior in
  `derive_transport_encryption_key()`.
- Preserve the existing v1 ECDH/HKDF derivation unchanged.
- Keep the v2 wire format as standard general JWE JSON Serialization:
  `protected`, `recipients`, `iv`, `ciphertext`, and `tag` only.
- Encode v2 key agreement through the custom recipient algorithms
  `ML-KEM-768` and `ECDH-ES+ML-KEM-768`; keep the recipient `encrypted_key`
  packing and KDF transcript stable and documented.

**Primary files:**

- [`exchange_kem.py`](../lib/python/openlinktoken/src/main/openlinktoken/exchange_kem.py)
- [`jwe_mlkem.py`](../lib/python/openlinktoken/src/main/openlinktoken/jwe_mlkem.py)
- [`exchange_config.py`](../lib/python/openlinktoken/src/main/openlinktoken/exchange_config.py)

**Tests:**

- Sender and recipient derive identical v2 transport keys.
- The derived v2 transport key is stable for the same envelope and private
  bundle.
- Changing the exchange ID changes the derived transport key.
- Token encryption/decryption succeeds using the derived key.
- The v2 content key is not returned as the transport key.
- v2 output contains only standard general JWE JSON members.
- Pure ML-KEM and hybrid recipients use the documented custom `alg` values
  and recipient key encoding.
- Existing v1 exchange key derivation tests remain unchanged.

**Acceptance criteria:**

- No code path uses the v2 envelope CEK directly as the token transport key.
- Both `package`/`encrypt` and `decrypt` continue to round-trip tokens for all
  three v2 suites.
- A standard JWE JSON parser can parse the v2 envelope shape, while decryption
  still requires an implementation of the documented custom algorithms.
- The v2 derivation label and compatibility behavior are documented.

### A2. Mirror suite-contract validation in Java

**Priority:** P1

**Problem:** Python validates every registered `CryptoSuite`, while Java
accepts registry definitions without checking their internal combinations.

**Actions:**

- Add Java validation for:
  - supported token content encryption (`A256GCM`);
  - version 1 requiring `ECDH`;
  - version 2 requiring a non-ECDH agreement;
  - supported exchange-config versions.
- Validate suite constants during Java registry initialization so invalid
  definitions fail early.
- Keep error behavior clear and equivalent to Python's
  `CryptoSuiteError` messages.

**Primary files:**

- [`CryptoSuite.java`](../lib/java/openlinktoken/src/main/java/org/openlinktoken/crypto/CryptoSuite.java)
- [`crypto_suite.py`](../lib/python/openlinktoken/src/main/openlinktoken/crypto_suite.py)

**Tests:**

- Java registry initialization succeeds for all five supported suites.
- Java rejects invalid suite combinations through the public validation path
  or constructor-time validation.
- Python validation tests remain green.
- The Java and Python registries expose the same suite IDs and algorithm
  contracts.

**Acceptance criteria:**

- A future invalid suite definition cannot silently pass in Java while failing
  in Python.
- No duplicate or language-specific suite constants are introduced.

### A3. Align omitted-suite behavior across public APIs

**Priority:** P1

**Problem:** Python defaults an omitted suite to `CryptoSuite.default()` in
several suite-aware components. Some Java constructors instead retain `null`
and fail later, often during tokenization.

**Actions:**

- Audit all suite-aware Java constructors and normalize optional `null` suites
  to the default suite.
- At minimum, cover:
  - `CryptoSuiteTokenizer`
  - `HashTokenTransformer`
  - `JweMatchTokenFormatter`
- Keep explicit invalid suite values fail-fast.
- Add tests for omitted suite and explicit suite behavior in both languages.

**Primary files:**

- [`CryptoSuiteTokenizer.java`](../lib/java/openlinktoken/src/main/java/org/openlinktoken/tokens/tokenizer/CryptoSuiteTokenizer.java)
- [`HashTokenTransformer.java`](../lib/java/openlinktoken/src/main/java/org/openlinktoken/tokentransformer/HashTokenTransformer.java)
- [`JweMatchTokenFormatter.java`](../lib/java/openlinktoken/src/main/java/org/openlinktoken/tokentransformer/JweMatchTokenFormatter.java)
- [`crypto_suite_tokenizer.py`](../lib/python/openlinktoken/src/main/openlinktoken/tokens/tokenizer/crypto_suite_tokenizer.py)
- [`hash_token_transformer.py`](../lib/python/openlinktoken/src/main/openlinktoken/tokentransformer/hash_token_transformer.py)
- [`jwe_match_token_formatter.py`](../lib/python/openlinktoken/src/main/openlinktoken/tokentransformer/jwe_match_token_formatter.py)

**Acceptance criteria:**

- Omitted suite produces the same legacy SHA-256/HMAC-SHA256 behavior in both
  languages.
- Explicit suite selection produces the same digest, MAC, and embedded
  metadata in both languages.
- No delayed null-pointer failure remains for a supported optional argument.

### A4. Define JWE compatibility and the language boundary

**Priority:** P1

**Problem:** Standard JWE serialization makes the v2 envelope structurally
compatible with API-side JWE parsers, but custom ML-KEM and hybrid algorithms
still require explicit implementation. Calling the envelope fully
cross-language compatible without those handlers would overstate support.

**Actions:**

- State clearly in the crypto-suite and exchange-format documentation that:
  - Java and Python are parity targets for token generation and token metadata;
  - v1 exchange remains compatible with the existing Python CLI workflow;
  - v2 uses standard JWE JSON Serialization;
  - v2 `ML-KEM-768` and `ECDH-ES+ML-KEM-768` are custom key-management
    algorithms that require handlers in the consuming implementation;
  - the API-side C# JWE integration can parse the standard envelope shape only
    when it also implements those custom algorithms and the v2 transport-key
    derivation contract.
- Run the synchronization checker against the full PR.
- Determine whether the Java marker classes are required by synchronization
  tooling:
  - If required, keep them as documented boundary markers.
  - If not required, remove them rather than maintaining empty counterparts.
- Do not describe v2 as generically JWE-decryptable merely because its JSON
  serialization is standard; distinguish structural compatibility from
  end-to-end custom-algorithm interoperability.

**Primary files:**

- [`crypto-suites.md`](../pages/concepts/crypto-suites.md)
- [`exchange-config-format.md`](../docs/exchange-config-format.md)
- [`jwe_mlkem.py`](../lib/python/openlinktoken/src/main/openlinktoken/jwe_mlkem.py)
- [`ExchangeKem.java`](../lib/java/openlinktoken/src/main/java/org/openlinktoken/ExchangeKem.java)
- [`ExchangeKeyBundle.java`](../lib/java/openlinktoken/src/main/java/org/openlinktoken/ExchangeKeyBundle.java)
- [`sync-check.sh`](../tools/sync-check.sh)

**Acceptance criteria:**

- A reviewer can distinguish standard JWE serialization compatibility from
  custom-algorithm interoperability and identify the supported C# boundary.
- The custom algorithm identifiers, recipient encoding, KDF transcript, and
  transport-key derivation are documented consistently.
- The synchronization checker reports no unexplained parity work.

### A5. Simplify adjacent code and tests

**Priority:** P2

**Actions:**

- Replace double-negative Java assertions such as
  `assertFalse(!suite.isPostQuantum())` with `assertTrue(...)`.
- Remove redundant compatibility wrappers or marker classes only after
  verifying that imports, package consumers, and synchronization checks do not
  require them.
- Prefer one canonical suite registry per language; compatibility exports
  should remain only when they support an existing public import path.
- Avoid adding new abstraction layers for v2 until the transport-key contract
  and implementation boundary are settled.

**Acceptance criteria:**

- No behavior change from cleanup.
- The resulting public API has one obvious suite definition and one obvious
  suite-aware tokenization path per language.

### A6. Separate unrelated PR hygiene changes where practical

**Priority:** P2

**Actions:**

- Review the devcontainer, workflow, instruction, and launch-configuration
  changes separately from the crypto implementation.
- Keep infrastructure changes in this PR only when they are required to run or
  verify the crypto-suite work.
- Otherwise move them to a follow-up PR to make the crypto review smaller and
  easier to validate.

**Acceptance criteria:**

- The final PR has a clear reason for every non-crypto file it changes.
- Unrelated environment or documentation preferences do not obscure the
  security and parity review.

## Parity matrix to verify

| Area                   | Java/Python requirement                                                | Evidence                                            |
| ---------------------- | ---------------------------------------------------------------------- | --------------------------------------------------- |
| Suite registry         | Same five IDs and algorithm fields                                     | Registry tests and sync review                      |
| Digest output          | Byte-identical SHA-256, SHA3-256, and SHAKE256-256 output              | Digest tests and interop harness                    |
| Keyed MAC              | Byte-identical HMAC/KMAC output and validation behavior                | Transformer tests and interop harness               |
| Token metadata         | Same digest/MAC identifiers embedded in JWE payloads                   | Formatter tests                                     |
| v1 exchange            | Existing behavior remains unchanged                                    | Existing v1 exchange tests                          |
| v2 JWE serialization   | Standard general JWE members and documented custom `alg` profile       | JWE structure fixtures and exchange-format docs     |
| v2 exchange algorithms | Matching ML-KEM/hybrid recipient processing and transport-key behavior | v2 exchange tests plus C# fixtures/adapter evidence |
| CLI behavior           | Same selected suite flows through tokenize/package/encrypt/decrypt     | CLI integration tests                               |

## Verification sequence

Run these after implementation, in order:

1. Targeted Python core and CLI tests for exchange, suites, transformers, and
   tokenization.
2. Targeted Java tests for suites, digest selection, MAC selection, formatter
   behavior, and legacy SHA-256 compatibility.
3. Java/Python interoperability tests for every registered suite.
4. JWE structure and custom-algorithm fixture tests covering v1 and all v2
   suites. Where the C# implementation is outside this repository, validate
   against shared serialized fixtures and record the external handler
   requirement rather than claiming generic library interoperability.
5. CLI integration tests covering v1 and all v2 suites.
6. Multi-language synchronization check:

   ```bash
   ./tools/sync-check.sh --languages java,python --since develop
   ```

7. Exact-file pre-commit hooks for every changed file:

   ```bash
   prek run --files <changed-files>
   ```

8. `git diff --check`.

## Definition of done

- [ ] The v2 transport key is domain-separated from the envelope content key.
- [ ] v2 key derivation has tests for both participants and all v2 suites.
- [ ] Java suite validation mirrors Python validation.
- [ ] Optional suite handling is consistent across Java and Python APIs.
- [ ] The standard JWE v2 serialization, custom algorithm profile, and C# API
      integration boundary are explicit and documented.
- [ ] v2 custom-algorithm fixture coverage distinguishes parse compatibility
      from end-to-end decryption interoperability.
- [ ] Placeholder and compatibility modules are justified or removed.
- [ ] Java/Python token outputs match for every registered suite.
- [ ] v1 behavior remains backward compatible.
- [ ] Targeted tests, interoperability tests, sync checks, and exact-file
      pre-commit hooks pass.
- [ ] Every remaining PR file has a clear, reviewable purpose.
