# Metadata format

`package` and `tokenize` write processing metadata:

- CSV and Parquet output: `<output stem>.metadata.json`
- ZIP output from `package`: metadata is stored in the archive
- `encrypt` and `decrypt`: no metadata output

The file is UTF-8 JSON. It contains counters and runtime information, not raw
person data or secret values.

## Fields

| Field                            | Type    | Description                                           |
| -------------------------------- | ------- | ----------------------------------------------------- |
| `Platform`                       | string  | `Java` or `Python`                                    |
| `JavaVersion` or `PythonVersion` | string  | Runtime version for the selected implementation       |
| `Version`                        | string  | Open Link Token library version                       |
| `OutputFormat`                   | string  | `JSON`, `CSV`, or `Parquet`                           |
| `TotalRows`                      | integer | Number of input records processed                     |
| `TotalRowsWithInvalidAttributes` | integer | Number of records with one or more invalid attributes |
| `InvalidAttributesByType`        | object  | Invalid-attribute occurrence counts by attribute name |
| `BlankTokensByRule`              | object  | Blank-token counts by token rule                      |

The implementation can also add SHA-256 digests for supplied secrets under
caller-defined keys. It never writes the raw secret.

## Example

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.5",
  "Version": "2.1.1",
  "OutputFormat": "CSV",
  "TotalRows": 101,
  "TotalRowsWithInvalidAttributes": 9,
  "InvalidAttributesByType": {
    "BirthDate": 3,
    "FirstName": 1
  },
  "BlankTokensByRule": {
    "T1": 5,
    "T2": 12,
    "ML1": 4
  }
}
```

`TotalRowsWithInvalidAttributes` counts records, while
`InvalidAttributesByType` counts invalid attribute occurrences. A record with
two invalid attributes contributes once to the former and twice to the latter.
`BlankTokensByRule` includes `ML1` when ML1 inference is enabled.
