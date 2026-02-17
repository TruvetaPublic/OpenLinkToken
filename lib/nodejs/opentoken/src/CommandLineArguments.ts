/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Parses and holds command line arguments for the OpenToken CLI.
 */
export class CommandLineArguments {
  inputFile?: string;
  outputFile?: string;
  metadataFile?: string;
  encryptionKey?: string;
  hashKey?: string;
  inputFormat: 'csv' | 'parquet' = 'csv';
  outputFormat: 'csv' | 'parquet' = 'csv';
  help: boolean = false;

  constructor(args: string[]) {
    this.parse(args);
  }

  private parse(args: string[]): void {
    for (let i = 0; i < args.length; i++) {
      const arg = args[i];

      switch (arg) {
        case '-i':
        case '--input':
          this.inputFile = args[++i];
          break;
        case '-o':
        case '--output':
          this.outputFile = args[++i];
          break;
        case '-m':
        case '--metadata':
          this.metadataFile = args[++i];
          break;
        case '-e':
        case '--encryption-key':
          this.encryptionKey = args[++i];
          break;
        case '-k':
        case '--hash-key':
          this.hashKey = args[++i];
          break;
        case '--input-format':
          this.inputFormat = args[++i] as 'csv' | 'parquet';
          break;
        case '--output-format':
          this.outputFormat = args[++i] as 'csv' | 'parquet';
          break;
        case '-h':
        case '--help':
          this.help = true;
          break;
      }
    }
  }

  validate(): string[] {
    const errors: string[] = [];

    if (!this.inputFile && !this.help) {
      errors.push('Input file is required');
    }

    if (!this.outputFile && !this.help) {
      errors.push('Output file is required');
    }

    if (this.encryptionKey && this.encryptionKey.length !== 32) {
      errors.push('Encryption key must be exactly 32 characters');
    }

    return errors;
  }

  getUsage(): string {
    return `
OpenToken CLI - Generate privacy-preserving tokens

Usage: opentoken [options]

Options:
  -i, --input <file>           Input file path (required)
  -o, --output <file>          Output file path (required)
  -m, --metadata <file>        Metadata output file path (optional)
  -k, --hash-key <key>         HMAC-SHA256 hash key (optional)
  -e, --encryption-key <key>   AES-256 encryption key, must be 32 chars (optional)
  --input-format <format>      Input format: csv or parquet (default: csv)
  --output-format <format>     Output format: csv or parquet (default: csv)
  -h, --help                   Show this help message

Examples:
  opentoken -i input.csv -o output.csv
  opentoken -i input.csv -o output.csv -k myHashKey -e 12345678901234567890123456789012
`;
  }
}
