---
layout: default
---

# Tokenization Configuration Reference

The Python CLI `package` and `tokenize` commands accept
`--config <path>` for non-standard input columns and explicitly defined token
rules. A configuration-driven run replaces the built-in T1–T5 definition with
the rules in the file; optional CLI inferencing is a separate provider.

## Example command

```bash
olt tokenize \
  -i unusual-input.csv -o output.csv \
  --exchange-config ./partner.exchange.json \
  --config ./tokenization-config.yaml
```

Use the same `--config` option with `olt package`.

## Example input

```csv
member_id,given name,surname_txt,dob_iso,gender_code,zip_5,national_id
A-1001,Ana,Lopez,1988-03-12,F,98052,123-45-6789
A-1002,Marcus,Nguyen,1979-11-05,M,10001,234-56-7890
```

## Example configuration

```yaml
column_mappings:
  RecordId:
    column_name: "member_id"
    type: RecordId
  GivenName:
    column_name: "given name"
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

## File specification

The top-level sections are both required and must be non-empty:

| Key               | Shape   | Meaning                                                          |
| ----------------- | ------- | ---------------------------------------------------------------- |
| `column_mappings` | Mapping | Maps logical field IDs to source columns and attribute types     |
| `token_rules`     | Mapping | Maps each rule ID to an ordered list of field/expression entries |

Each `column_mappings` entry requires:

| Field         | Meaning                                        |
| ------------- | ---------------------------------------------- |
| `<field_id>`  | Logical ID referenced by a token rule          |
| `column_name` | Source column name in the CSV or Parquet input |
| `type`        | Registered attribute type name or alias        |

Each entry in a `token_rules` list requires:

| Field        | Meaning                                               |
| ------------ | ----------------------------------------------------- | ----------------------------------------- |
| `field`      | Must match a logical ID declared in `column_mappings` |
| `expression` | `                                                     | `-separated attribute-expression pipeline |

Rule-entry order is preserved when the token signature is built. Rule IDs can
be `T1`–`T5` or custom identifiers.

## Validation and record IDs

The CLI rejects configurations when:

- `column_mappings` or `token_rules` is missing, not a mapping, or empty;
- a rule is not a non-empty list;
- an entry is missing a non-empty `field` or `expression`;
- a rule references an undeclared field ID; or
- an attribute `type` cannot be resolved.

If no mapping has type `RecordId`, the loader warns and output record IDs fall
back to generated UUIDs rather than preserving source IDs.

## Expression operators

Operator names are case-insensitive. The supported operators are:

| Operator         | Behavior                                                         |
| ---------------- | ---------------------------------------------------------------- |
| `T`              | Trim whitespace                                                  |
| `U`              | Convert to uppercase                                             |
| `S(start,end)`   | Take the substring from `start` (inclusive) to `end` (exclusive) |
| `D`              | Parse a normalized `yyyy-MM-dd` date                             |
| `M(regex)`       | Concatenate the regex matches found in the value                 |
| `R("old","new")` | Replace occurrences of one quoted string with another            |

For examples and the API-level expression behavior, see
[Token Rules: Expression Syntax](../concepts/token-rules.md#expression-syntax).

## Attribute types

`type` values are exact, case-sensitive registered names. The Python CLI
currently accepts these canonical names and aliases:

| Canonical type         | Aliases                               |
| ---------------------- | ------------------------------------- |
| `Age`                  | —                                     |
| `BirthDate`            | `DateOfBirth`                         |
| `BirthYear`            | `YearOfBirth`                         |
| `Date`                 | —                                     |
| `Decimal`              | —                                     |
| `FirstName`            | `GivenName`                           |
| `Integer`              | —                                     |
| `LastName`             | `Surname`                             |
| `PostalCode`           | `ZipCode`, `ZIP3`, `ZIP4`, `ZIP5`     |
| `RecordId`             | `Id`                                  |
| `Sex`                  | `Gender`                              |
| `SocialSecurityNumber` | `NationalIdentificationNumber`, `SSN` |
| `String`               | `Text`                                |
| `Year`                 | —                                     |

Each type applies its own normalization and validation rules; see
[Normalization and Validation](../concepts/normalization-and-validation.md).

When `--config` is omitted, the CLI uses its built-in input-column aliases and
token definitions.
