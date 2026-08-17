---
layout: default
---

# Metadata Format

Metadata is a JSON run summary written by the CLI. It records processing
counts and runtime information; it is not a complete audit log.

## When metadata is written

The `package` and `tokenize` commands write metadata:

- CSV and Parquet outputs get a `<output-stem>.metadata.json` sidecar.
- ZIP output embeds `<output-stem>.metadata.json` in the archive.

`package` ZIP archives also contain the exchange configuration. The `encrypt`
and `decrypt` commands do not write metadata.

The current CLI metadata does not include raw person data, timestamps, user
identity, input/output paths, or secret hashes. Library callers can add their
own fields, so protect metadata according to the same operational policy as
the associated token output.

## Schema

The Python CLI emits fields like these:

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.5",
  "Version": "2.1.1",
  "TotalRows": 101,
  "TotalRowsWithInvalidAttributes": 9,
  "InvalidAttributesByType": {
    "BirthDate": 3,
    "FirstName": 1
  },
  "BlankTokensByRule": {
    "T1": 5,
    "T2": 12
  }
}
```

`Platform` and `Version` identify the producer. Python metadata uses
`PythonVersion`; the Java metadata helper uses `JavaVersion`.

## Field descriptions

| Field                            | Meaning                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `Platform`                       | Producer platform, such as `Python` or `Java`                     |
| `PythonVersion` / `JavaVersion`  | Runtime version for the producer platform                         |
| `Version`                        | Open Link Token library/CLI version                               |
| `TotalRows`                      | Number of input records processed                                 |
| `TotalRowsWithInvalidAttributes` | Number of distinct records with one or more invalid attributes    |
| `InvalidAttributesByType`        | Counts of invalid attribute observations, keyed by attribute name |
| `BlankTokensByRule`              | Counts of blank token outputs, keyed by active rule ID            |

The runtime fields vary by producer. The processing counters are populated by
the CLI processing path.

## Interpreting the counters

### Invalid attributes

```text
Valid records = TotalRows - TotalRowsWithInvalidAttributes
```

`TotalRowsWithInvalidAttributes` counts each affected record once. A record
with two invalid attributes contributes once to that field and once to each
corresponding `InvalidAttributesByType` count. Therefore, the sum of
`InvalidAttributesByType` values can be greater than
`TotalRowsWithInvalidAttributes`.

The keys in `InvalidAttributesByType` are the attribute names used by the
active token definition; healthy runs can therefore contain zero values.

### Blank tokens

`BlankTokensByRule` counts records for which a rule produced a blank token,
usually because a required value was missing or invalid. The dictionary is
initialized from the active rule definition, so it can contain zero-valued
entries. Rule IDs may be built-in (`T1`–`T5`), optional (`ML1`), or custom.

Disabling ML1 inferencing stops ML1 generation. If an ML1 definition is still
registered by the installed provider, its metadata key may remain with a zero
count.

## Example

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.5",
  "Version": "2.1.1",
  "TotalRows": 3,
  "TotalRowsWithInvalidAttributes": 1,
  "InvalidAttributesByType": {
    "BirthDate": 1,
    "PostalCode": 1
  },
  "BlankTokensByRule": {
    "T1": 1,
    "T2": 1,
    "T3": 1,
    "T4": 1,
    "T5": 0
  }
}
```

Store metadata with the corresponding token output when you need processing
statistics for troubleshooting or reproducibility. Metadata cannot decrypt
tokens or reconstruct the source values, but its counts and runtime details
may still be operationally sensitive.

## Related documentation

- [Concepts: Metadata and Audit](../concepts/metadata-and-audit.md)
- [Concepts: Token Rules](../concepts/token-rules.md)
- [Normalization and Validation](../concepts/normalization-and-validation.md)
- [CLI Reference](cli.md)
