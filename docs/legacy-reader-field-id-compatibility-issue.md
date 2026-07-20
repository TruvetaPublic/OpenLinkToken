# Legacy `PersonAttributesReader` Compatibility Issue

## Summary

`PersonAttributesProcessor` now processes rows with
`TokenGenerator.get_all_tokens_via_field_id()`, which expects dictionaries
keyed by logical field IDs such as `"FirstName"`.

Custom readers written against the older `PersonAttributesReader` contract
may still return dictionaries keyed by attribute classes:

```python
{
    FirstNameAttribute: "Ana",
    LastNameAttribute: "Lopez",
}
```

Those readers continue to run, but their values are not found by the
field-ID-based token generator. The processor can therefore emit blank tokens
without reporting a processing failure.

This issue predates pull request #395. PR #395 does not modify
`PersonAttributesProcessor`; it updates the built-in readers and documents the
field-ID row format.

## Reproduction

Create a custom reader that yields a class-keyed row:

```python
row = {
    RecordIdAttribute: "A-1001",
    FirstNameAttribute: "Ana",
    LastNameAttribute: "Lopez",
    BirthDateAttribute: "1988-03-12",
    SexAttribute: "F",
    PostalCodeAttribute: "98052",
    SocialSecurityNumberAttribute: "123-45-6789",
}
```

Pass that reader to `PersonAttributesProcessor.process(...)`.

The processor calls the field-ID API, which looks for keys such as
`"FirstName"` and `"LastName"`. The class keys are not found, so required
attributes appear to be missing and generated tokens become:

```text
0000000000000000000000000000000000000000000000000000000000000000
```

The run may still complete successfully and report the row as processed.

## Expected behavior

Existing custom readers should continue to generate the same tokens after the
field-ID migration, or receive a clear compatibility error instead of silently
producing blank tokens.

## Impact

- Existing integrations with custom class-keyed readers can produce unusable
  blank tokens.
- The failure is silent unless callers inspect token values or blank-token
  metadata.
- Records may be marked as processed even though no usable matching tokens
  were generated.

## Suggested resolution

Preserve both input shapes at the processor boundary:

1. Use the field-ID token-generation path for string-keyed rows.
2. Use the existing legacy class-keyed path for class-keyed rows.
3. Emit a deprecation warning when the legacy shape is detected.
4. Add regression tests covering both row formats and the resulting tokens.

This keeps existing integrations working while giving consumers time to
migrate to the field-ID contract.

## Resolution

The processor now supports both row shapes without changing the built-in
reader contract:

- Built-in CSV and Parquet readers continue to emit rows keyed by field-ID
  strings.
- `PersonAttributesProcessor` detects field-ID string-keyed rows versus legacy
  `Attribute`-class-keyed rows and dispatches each shape to the matching token
  generator API.
- Legacy rows emit one deprecation warning per processing run. Custom readers
  should migrate to field-ID string keys.
- String `RecordId` values are preserved. For legacy rows, exact or subclass
  `RecordIdAttribute` values are also preserved; when no record ID is present,
  the processor falls back to a generated UUID.
- Empty rows are shape-neutral: they follow an already established non-empty
  row shape, and use field-ID behavior when no non-empty shape has been
  established.
- Mixed key types and unsupported keys fail explicitly. A reader that changes
  between non-empty row shapes raises a clear error.
- Token generation, token writing, and metadata processing otherwise remain
  unchanged.
