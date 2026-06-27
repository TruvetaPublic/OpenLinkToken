# Tokenization Configuration Format

## Overview

`tokenize --config` lets you map non-standard input column names to Open Link Token attribute types and define token rules explicitly.

Use this when source data does not use built-in aliases (for example `given_nm` instead of `FirstName`) or when custom token rules are required.

## Example Command

```bash
olt tokenize \
  -i unusual-input.csv -o output.csv \
  --exchange-config ./partner.exchange.json \
  --config ./tokenization-config.yaml
```

## Example Input (Unusual Fields)

```csv
member_id,given_nm,surname_txt,dob_iso,gender_code,zip_5,national_id
A-1001,Ana,Lopez,1988-03-12,F,98052,123-45-6789
A-1002,Marcus,Nguyen,1979-11-05,M,10001,234-56-7890
```

## Example Configuration File

```yaml
attributes:
  given_nm:
    field: FirstName
    type: GivenName
  surname_txt:
    field: FamilyName
    type: LastName
  dob_iso:
    field: DateOfBirth
    type: BirthDate
  gender_code:
    field: SexAtBirth
    type: Sex
  zip_5:
    field: HomeZip
    type: PostalCode
  national_id:
    field: NationalId
    type: SocialSecurityNumber

token_rules:
  T1:
    - field: FamilyName
      expression: T|U
    - field: FirstName
      expression: T|S(0,1)|U
    - field: DateOfBirth
      expression: T|D
    - field: SexAtBirth
      expression: T|S(0,1)|U
```

## File Specification

Top-level keys:

| Key           | Required | Type    | Description                                                                  |
| ------------- | -------- | ------- | ---------------------------------------------------------------------------- |
| `attributes`  | Yes      | Mapping | Maps input column names to logical field IDs and attribute types.            |
| `token_rules` | Yes      | Mapping | Defines each token rule as an ordered list of `{field, expression}` entries. |

`attributes` entry schema:

| Field           | Required | Type    | Description                                                                                            |
| --------------- | -------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `<column_name>` | Yes      | Mapping | Input column name from the CSV or Parquet schema (for example `given_nm`).                             |
| `field`         | Yes      | String  | Logical field identifier used by token rules (for example `FirstName`).                                |
| `type`          | Yes      | String  | Open Link Token attribute type/alias. See [Attribute Types](#attribute-types) for all accepted values. |

`token_rules` entry schema:

| Field        | Required | Type   | Description                                                                                                |
| ------------ | -------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| `<rule_id>`  | Yes      | List   | Token rule identifier (`T1`, `T2`, `T3`, `T4`, `T5`, or custom).                                           |
| `field`      | Yes      | String | Must match one of the `attributes.*.field` values.                                                         |
| `expression` | Yes      | String | Attribute-expression pipeline used by token generation. See [Expression syntax](#expression-syntax) below. |

## Validation Rules

Validation enforced by the CLI:

- `attributes` must be present and non-empty.
- `token_rules` must be present and non-empty.
- Every token-rule entry must contain non-empty `field` and `expression`.
- Every token-rule `field` must reference a declared `attributes.*.field` value.
- Every declared `type` must resolve to a known Open Link Token attribute class/alias.
- Token-rule entry order is preserved and used as-is during token construction.

> **Note:** `expression` values are not validated at config-load time. An unknown operator (for example `Y` instead of `D`) will raise a `ValueError` per row during token generation, not at startup.

## Expression Syntax

An expression is a `|`-separated pipeline of operators applied to an attribute value before token generation:

| Operator       | Description                                             |
| -------------- | ------------------------------------------------------- |
| `T`            | Trim whitespace                                         |
| `U`            | Convert to upper case                                   |
| `S(start,end)` | Substring from `start` (inclusive) to `end` (exclusive) |
| `D`            | Parse as a date in `yyyy-MM-dd` format                  |
| `M(regex)`     | Assert value matches the regular expression             |
| `R(old,new)`   | Replace all occurrences of `old` with `new`             |

Examples:

```
T|S(0,3)|U      # trim, take first 3 chars, uppercase
T|D             # trim, treat as date
T|M("\\d+")    # trim, assert all digits
```

## Notes

- `--config` works with `tokenize` for both CSV and Parquet input.
- Built-in aliases continue to work when `--config` is omitted.

## Attribute Types

All values accepted in the `type` field:

| Valid `type` values                                    |
| ------------------------------------------------------ |
| `Age`                                                  |
| `BirthDate`                                            |
| `BirthYear`, `YearOfBirth`                             |
| `Date`                                                 |
| `Decimal`                                              |
| `FirstName`, `GivenName`                               |
| `Integer`                                              |
| `LastName`, `Surname`                                  |
| `PostalCode`, `ZIP3`, `ZIP4`, `ZIP5`, `ZipCode`        |
| `Id`, `RecordId`                                       |
| `Gender`, `Sex`                                        |
| `NationalIdentificationNumber`, `SocialSecurityNumber` |
| `String`, `Text`                                       |
| `Year`                                                 |
