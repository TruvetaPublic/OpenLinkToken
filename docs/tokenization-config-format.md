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
column_mappings:
  RecordId:
    column_name: "member_id"
    type: RecordId
  GivenName:
    column_name: "given_nm"
    type: FirstName
  FamilyName:
    column_name: "surname_txt"
    type: LastName
  DateOfBirth:
    column_name: "dob_iso"
    type: BirthDate
  SexAtBirth:
    column_name: "gender_code"
    type: Sex
  HomeZip:
    column_name: "zip_5"
    type: PostalCode
  NationalId:
    column_name: "national_id"
    type: SocialSecurityNumber

token_rules:
  T1:
    - field: FamilyName
      expression: T|U
    - field: GivenName
      expression: T|S(0,1)|U
    - field: DateOfBirth
      expression: T|D
    - field: SexAtBirth
      expression: T|S(0,1)|U
```

## File Specification

Top-level keys:

| Key               | Required | Type    | Description                                                                  |
| ----------------- | -------- | ------- | ---------------------------------------------------------------------------- |
| `column_mappings` | Yes      | Mapping | Maps logical field IDs to source column names and attribute types.           |
| `token_rules`     | Yes      | Mapping | Defines each token rule as an ordered list of `{field, expression}` entries. |

`column_mappings` entry schema:

| Field         | Required | Type    | Description                                                                                      |
| ------------- | -------- | ------- | ------------------------------------------------------------------------------------------------ |
| `<field_id>`  | Yes      | Mapping | Logical field identifier used by token rules (for example `GivenName`).                          |
| `column_name` | Yes      | String  | Source column name in the CSV or Parquet file (for example `"given_nm"`).                        |
| `type`        | Yes      | String  | Open Link Token attribute type. See [Attribute Types](#attribute-types) for all accepted values. |

`token_rules` entry schema:

| Field        | Required | Type   | Description                                                                                                |
| ------------ | -------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| `<rule_id>`  | Yes      | List   | Token rule identifier (`T1`, `T2`, `T3`, `T4`, `T5`, or custom).                                           |
| `field`      | Yes      | String | Must match one of the `column_mappings` field IDs.                                                         |
| `expression` | Yes      | String | Attribute-expression pipeline used by token generation. See [Expression syntax](#expression-syntax) below. |

## Validation Rules

Validation enforced by the CLI:

- `column_mappings` must be present and non-empty.
- `token_rules` must be present and non-empty.
- Every token-rule entry must contain non-empty `field` and `expression`.
- Every token-rule `field` must reference a declared `column_mappings` field ID.
- Every declared `type` must resolve to a known Open Link Token attribute class/alias.
- Token-rule entry order is preserved and used as-is during token construction.

> **Note:** `expression` values are not validated at config-load time. An unknown operator (for example `Y` instead of `D`) will raise a `ValueError` per row during token generation, not at startup.

## Expression Syntax

See [Expression Syntax](../pages/concepts/token-rules.md#expression-syntax) in the Token Rules concept page.

## Notes

- `--config` works with `tokenize` for both CSV and Parquet input.
- Built-in aliases continue to work when `--config` is omitted.

## Attribute Types

Accepted values for the field `type`. Each type applies its own normalization and validation rules — see [Normalization and Validation](../concepts/normalization-and-validation). |

| `type` value           | Description                    |
| ---------------------- | ------------------------------ |
| `Age`                  | Age (numeric)                  |
| `BirthDate`            | Date of birth                  |
| `BirthYear`            | Year of birth                  |
| `Date`                 | Generic date                   |
| `Decimal`              | Decimal number                 |
| `FirstName`            | Given / first name             |
| `Integer`              | Integer number                 |
| `LastName`             | Family / last name             |
| `PostalCode`           | Postal or ZIP code             |
| `Sex`                  | Biological sex                 |
| `SocialSecurityNumber` | National identification number |
| `String`               | Generic string                 |
| `Year`                 | Generic year                   |
