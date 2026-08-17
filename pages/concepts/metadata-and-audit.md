---
layout: default
---

# Metadata and Audit

The CLI writes a small metadata summary alongside token outputs. It is useful
for checking data quality and reproducing a run, but it is not a complete audit
log: current CLI metadata does not record timestamps, user identity, paths, or
secret hashes.

## Where it appears

`package` and `tokenize` write metadata for CSV and Parquet outputs as a
`<output-stem>.metadata.json` sidecar. ZIP output embeds the metadata file.
`encrypt` and `decrypt` do not generate metadata.

## What it contains

The summary combines:

- runtime and library information (`Platform`, `Version`, and
  `PythonVersion` or `JavaVersion`);
- total processed rows (`TotalRows`);
- distinct rows with invalid attributes
  (`TotalRowsWithInvalidAttributes`);
- invalid-attribute counts (`InvalidAttributesByType`); and
- blank-token counts by rule (`BlankTokensByRule`).

Use the [Metadata Format reference](../reference/metadata-format.md) for the
schema, file naming, and interpretation details.

## Practical use

Store the metadata with its token output when investigating validation failures
or comparing runs. The default CLI metadata contains no raw person values or
secret bytes, but counts and runtime information may still be operationally
sensitive.

## Related concepts

- [Normalization and Validation](normalization-and-validation.md)
- [Token Rules](token-rules.md)
