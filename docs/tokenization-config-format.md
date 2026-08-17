# Tokenization configuration

`olt tokenize --config` maps source columns to Open Link Token attribute types
and defines token rules. Use it when the input columns do not use the built-in
aliases or when the token rules must be explicit.

```bash
olt tokenize \
  -i unusual-input.csv \
  -o output.csv \
  --exchange-config ./partner.exchange.json \
  --config ./tokenization-config.yaml
```

## File format

The YAML file must contain non-empty `column_mappings` and `token_rules`
sections:

```yaml
column_mappings:
  RecordId:
    column_name: "member_id"
    type: RecordId
  GivenName:
    column_name: "given nm"
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

### `column_mappings`

Each mapping is keyed by a logical field ID:

| Key           | Required | Description                             |
| ------------- | -------- | --------------------------------------- |
| `<field_id>`  | yes      | ID referenced by `token_rules`          |
| `column_name` | yes      | Column name in the CSV or Parquet input |
| `type`        | yes      | Built-in attribute name or alias        |

### `token_rules`

Each rule is an ordered list of entries:

| Key          | Required | Description                                   |
| ------------ | -------- | --------------------------------------------- |
| `<rule_id>`  | yes      | Rule identifier, such as `T1` or a custom ID  |
| `field`      | yes      | Must match a `column_mappings` field ID       |
| `expression` | yes      | Pipe-separated attribute-expression operators |

The loader preserves entry order. It validates the operator names during
configuration loading. Supported operators are `T`, `U`, `S`, `D`, `M`, and
`R`; see [expression syntax](../pages/concepts/token-rules.md#expression-syntax)
for their meanings.

If no mapping uses type `RecordId`, the CLI logs a warning and generates a UUID
for each output row instead of preserving a source record ID.

## Attribute types

These built-in names and aliases are accepted by the resolver:

| Type                   | Meaning                        |
| ---------------------- | ------------------------------ |
| `Age`                  | Numeric age                    |
| `BirthDate`            | Date of birth                  |
| `BirthYear`            | Year of birth                  |
| `Date`                 | Generic date                   |
| `Decimal`              | Decimal number                 |
| `FirstName`            | Given name                     |
| `Integer`              | Integer number                 |
| `LastName`             | Family name                    |
| `PostalCode`           | Postal or ZIP code             |
| `Sex`                  | Sex                            |
| `SocialSecurityNumber` | National identification number |
| `String`               | Generic string                 |
| `Year`                 | Generic year                   |

Each type applies its normalization and validation rules. See
[Normalization and validation](../pages/concepts/normalization-and-validation.md).

The configuration is supported for both CSV and Parquet input. Without
`--config`, the CLI uses its built-in column aliases and token definitions.
