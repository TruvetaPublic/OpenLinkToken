# OpenToken Node.js Implementation

This is the Node.js/TypeScript implementation of OpenToken, providing privacy-preserving person matching using cryptographically secure token generation.

## Status: In Development

This implementation is currently under active development. The core infrastructure and attribute system are in place, with token transformers (HMAC-SHA256 and AES-256-GCM) implemented.

### Completed Components

- ✅ Project structure with TypeScript, ESLint, Prettier, and Jest
- ✅ Base attribute classes (`Attribute`, `BaseAttribute`, `SerializableAttribute`)
- ✅ Validation framework (`Validator`, `RegexValidator`, `NotInValidator`, `DateRangeValidator`)
- ✅ Attribute utilities (normalization, diacritic removal)
- ✅ General attributes (`StringAttribute`, `DateAttribute`)
- ✅ Person attributes (FirstName, LastName, BirthDate, Sex, SocialSecurityNumber)
- ✅ Token transformers (`HashTokenTransformer`, `EncryptTokenTransformer`)

### In Progress

- 🚧 Remaining person attributes (PostalCode, RecordId)
- 🚧 Attribute expression and combined attribute support
- 🚧 Token definitions (T1-T5)
- 🚧 I/O readers and writers (CSV, Parquet)
- 🚧 Person attributes processor
- 🚧 Command-line interface
- 🚧 Metadata generation

### Not Yet Started

- ⏳ Unit tests
- ⏳ Integration tests
- ⏳ Interoperability tests with Java/Python
- ⏳ GitHub Actions workflows
- ⏳ Docker support
- ⏳ Documentation

## Prerequisites

- Node.js 18.0.0 or higher
- npm 8.0.0 or higher

## Installation

```bash
cd lib/nodejs/opentoken
npm install
```

## Build

```bash
npm run build
```

This compiles the TypeScript code to JavaScript in the `dist` directory.

## Testing

```bash
npm test              # Run tests
npm run test:coverage # Run tests with coverage report
```

## Linting and Formatting

```bash
npm run lint          # Check for linting errors
npm run lint:fix      # Fix linting errors automatically
npm run format        # Format code with Prettier
```

## Usage (Planned)

### As a Library

```typescript
import {
  HashTokenTransformer,
  EncryptTokenTransformer,
} from '@truveta/opentoken';

// Create transformers
const hashTransformer = new HashTokenTransformer('your-hashing-secret');
const encryptTransformer = new EncryptTokenTransformer('your-encryption-key-32-chars-!');

// Process data (implementation in progress)
// ...
```

### Command Line Interface (Planned)

```bash
opentoken \
  -i input.csv \
  -t csv \
  -o output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

## Architecture

The Node.js implementation follows the same architecture as the Java and Python implementations:

```
src/
├── attributes/          # Person data attributes with validation
│   ├── person/         # FirstName, LastName, BirthDate, Sex, SSN, etc.
│   ├── general/        # StringAttribute, DateAttribute
│   ├── validation/     # Validators (regex, date ranges, etc.)
│   └── utilities/      # Normalization utilities
├── tokens/             # Token definitions (T1-T5)
│   └── definitions/    # Token rule implementations
├── tokentransformer/   # HMAC-SHA256 hashing + AES-256 encryption
├── io/                 # CSV and Parquet file I/O
│   ├── csv/           # CSV readers and writers
│   ├── parquet/       # Parquet readers and writers
│   └── json/          # Metadata JSON writer
├── processor/          # Token generation pipeline
└── utils/             # Utility functions
```

## Token Generation Process

OpenToken generates 5 distinct tokens (T1-T5) for each person record using:

1. **Attribute Validation**: Ensures data quality (e.g., valid dates, SSN formats)
2. **Normalization**: Standardizes formats (e.g., removes diacritics, formats dates)
3. **Token Signature Generation**: Combines specific attributes per token rule
4. **SHA-256 Hashing**: Creates base hash of token signature
5. **HMAC-SHA256**: Adds cryptographic security with secret key
6. **AES-256-GCM Encryption**: Final encryption layer

## Token Rules

| Rule | Definition |
|------|------------|
| T1 | `U(last-name)\|U(first-name-1)\|U(sex)\|birth-date` |
| T2 | `U(last-name)\|U(first-name)\|birth-date\|postal-code-3` |
| T3 | `U(last-name)\|U(first-name)\|U(sex)\|birth-date` |
| T4 | `social-security-number\|U(sex)\|birth-date` |
| T5 | `U(last-name)\|U(first-name-3)\|U(sex)` |

*Note: U(X) = uppercase(X), attribute-N = first N characters*

## Cross-Language Compatibility

This Node.js implementation must generate **identical tokens** to the Java and Python implementations for the same input data. This ensures interoperability across all three language implementations.

## Development Guidelines

1. **Follow existing patterns**: Match the structure and logic of Java/Python implementations
2. **Type safety**: Use TypeScript types consistently
3. **Testing**: Add tests for all new functionality
4. **Documentation**: Document public APIs and complex logic
5. **Code style**: Follow ESLint and Prettier configurations
6. **Normalization parity**: Ensure normalization logic matches Java/Python exactly

## Contributing

When contributing to the Node.js implementation:

1. Implement features to match Java/Python behavior exactly
2. Add corresponding unit tests
3. Update interoperability tests to include Node.js
4. Run `npm run lint` and fix any issues
5. Run `npm test` to ensure all tests pass
6. Update this README with any new features

## License

Copyright (c) Truveta. All rights reserved.

Licensed under the Apache License, Version 2.0.
