# Open Link Token PQC Overview Presentation

## Purpose and audience

Create an easy-to-follow, editable PowerPoint for a mixed audience of
non-specialists and engineers. By the end, viewers should understand what
post-quantum cryptography changes in Open Link Token, how the available suites
differ, and when each profile is appropriate.

The presentation compares the current `ecdh-sha256` profile
(SHA-256/HMAC-SHA256 with ECDH) with the SHA-3 and post-quantum profiles. It
explains the documented reasons for each profile without implying that the
legacy suite is already broken or that every algorithm in it must be replaced.

## Deliverable and scope

- One editable, 16:9 PowerPoint at `docs/presentations/pqc-overview.pptx`.
- Approximately 10 slides, with brief text, plain-language analogies, simple
  diagrams, a suite comparison table, and a references slide.
- No source-code, runtime behavior, or crypto-suite changes.

## Narrative and slide sequence

1. **Title:** Post-quantum cryptography in Open Link Token.
2. **Why it matters:** Future quantum computers threaten some widely used
   public-key cryptography; stored encrypted data can motivate “harvest now,
   decrypt later” concerns.
3. **Three different jobs:** Deterministic token digest/MAC, exchange key
   establishment, and token content encryption are separate functions.
4. **The current default:** Show the `ecdh-sha256` path: SHA-256 and
   HMAC-SHA256 for deterministic tokens, ECDH/JWE for exchange, and
   AES-256-GCM for token content encryption.
5. **What PQC changes:** Explain ML-KEM as a key-encapsulation mechanism and
   contrast ML-KEM exchange with classical ECDH exchange.
6. **Suite comparison:** Compare all four supported suites by token digest,
   token MAC, key agreement, exchange version, and intended use.
7. **Why these combinations exist:** Cover compatibility, the SHA-3 token
   option, the recommended PQ profile, and the SHAKE/KMAC alternative.
   Distinguish documented use-case rationale
   from historical selection details that are not recorded.
8. **Choosing a suite:** Recommend retaining the suite for an existing
   exchange; use `mlkem768-sha3-256` as the standard new PQ-only choice unless a
   policy or interoperability need calls for SHAKE/KMAC.
9. **What changes operationally:** Explain version-1 PEM keys versus
   version-2 JSON key bundles, larger version-2 artifacts and processing
   overhead, the need for every participant to agree on one suite, and the
   fact that changing suites creates a different token namespace.
10. **Takeaway and references:** Recap the separation of crypto jobs and cite
    repository guidance and the relevant NIST standards.

## Suite content

| Suite               | Token digest and MAC       | Exchange key agreement | Intended explanation                                                                                                |
| ------------------- | -------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `ecdh-sha256`       | SHA-256 / HMAC-SHA256      | ECDH/JWE, version 1    | Backward-compatible default for existing exchanges.                                                                 |
| `ecdh-sha3-256`     | SHA3-256 / HMAC-SHA3-256   | ECDH/JWE, version 1    | SHA-3 token primitives without changing the version-1 ECDH exchange; this is not a PQ suite.                        |
| `mlkem768-sha3-256` | SHA3-256 / HMAC-SHA3-256   | ML-KEM-768, version 2  | Standard PQ-only profile; the documented default when no policy or interoperability requirement selects SHAKE/KMAC. |
| `mlkem768-shake256` | SHAKE256-256 / KMAC256-256 | ML-KEM-768, version 2  | PQ-only exchange with the SHAKE/KMAC token primitive family, for a specific policy or interoperability need.        |

All currently supported suites use AES-256-GCM for token content encryption.
Suite IDs have no version suffix. The ML-KEM profiles use exchange format
version 2; the ECDH profiles use exchange format version 1.

## Technical framing and guardrails

- Explain that quantum algorithms threaten ECDH key establishment differently
  from hash and MAC operations; do not say SHA-256 or HMAC-SHA256 is broken by
  Shor’s algorithm.
- Make clear that the primary PQ change is ML-KEM-768 for exchange key
  establishment. The SHA-3/HMAC or SHAKE/KMAC token primitives are a separate
  suite choice, and AES-256-GCM remains the token content-encryption layer.
- Describe ML-KEM-768 as a NIST-standardized parameter set. NIST lists
  ML-KEM-512, -768, and -1024 in order of increasing security strength and
  decreasing performance; present -768 as the middle profile, not as a
  universally optimal choice.
- Explain that each exchange uses either ECDH or ML-KEM, not both.
- Never label `ecdh-sha3-256` as post-quantum.
- Avoid implying SHAKE/KMAC is more quantum-safe than SHA3/HMAC. The repository
  recommends `mlkem768-sha3-256` unless a policy or interoperability requirement
  calls for SHAKE/KMAC.
- Do not invent an undocumented historical reason for the original
  SHA-256/HMAC-SHA256 + ECDH selection; explain its documented compatibility
  role and clearly label standards-based tradeoffs as technical context.
- State that suite changes alter deterministic token values; participants in
  an exchange must use the same suite and hashing secret.

## Visual direction

Use a clean, high-contrast 16:9 layout with a small amount of copy per slide.
Use labeled colors consistently: neutral tones for the existing classical
profile and teal for PQ components.
Pair color with labels and shapes so the comparison remains understandable
without color. Prefer process diagrams and one legible comparison table over
cryptographic equations or dense prose.

## Sources

Repository sources:

- `pages/concepts/crypto-suites.md`
- `pages/concepts/token-hashing-and-encryption.md`
- `docs/exchange-config-format.md`

Standards and background:

- NIST FIPS 203, _Module-Lattice-Based Key-Encapsulation Mechanism Standard_
  (ML-KEM): <https://csrc.nist.gov/pubs/fips/203/final>
- NIST FIPS 202, _SHA-3 Standard_: <https://csrc.nist.gov/pubs/fips/202/final>
- NIST SP 800-185, _SHA-3 Derived Functions: cSHAKE, KMAC, TupleHash, and
  ParallelHash_: <https://csrc.nist.gov/pubs/sp/800/185/final>
- NIST Post-Quantum Cryptography project:
  <https://csrc.nist.gov/projects/post-quantum-cryptography>

## Validation

- Confirm that the PowerPoint file is a valid, readable presentation.
- Confirm the deck has approximately 10 slides and contains all five exact
  suite IDs, the SHA-256/HMAC-SHA256 + ECDH baseline, ML-KEM-768, and the
  AES-256-GCM continuity message.
- Check that the text is legible and that no slide overflows or relies only on
  color to distinguish suites.
