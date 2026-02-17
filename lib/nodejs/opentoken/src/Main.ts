#!/usr/bin/env node
/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { CommandLineArguments } from './CommandLineArguments';
import { PersonAttributesCSVReader } from './io/csv/PersonAttributesCSVReader';
import { PersonAttributesCSVWriter } from './io/csv/PersonAttributesCSVWriter';
import { PersonAttributesProcessor } from './processor/PersonAttributesProcessor';
import { HashTokenTransformer } from './tokentransformer/HashTokenTransformer';
import { EncryptTokenTransformer } from './tokentransformer/EncryptTokenTransformer';
import { TokenTransformer } from './tokentransformer/TokenTransformer';
import { Metadata } from './Metadata';
import { MetadataJsonWriter } from './io/json/MetadataJsonWriter';

/**
 * Main entry point for the OpenToken CLI.
 */
async function main() {
  const args = new CommandLineArguments(process.argv.slice(2));

  if (args.help) {
    console.log(args.getUsage());
    process.exit(0);
  }

  const errors = args.validate();
  if (errors.length > 0) {
    console.error('Errors:');
    errors.forEach((err) => console.error(`  - ${err}`));
    console.log(args.getUsage());
    process.exit(1);
  }

  try {
    console.log('OpenToken - Starting token generation...');
    console.log(`Input: ${args.inputFile}`);
    console.log(`Output: ${args.outputFile}`);

    // Create reader and writer
    const reader = new PersonAttributesCSVReader(args.inputFile!);
    const writer = new PersonAttributesCSVWriter(args.outputFile!);

    // Create transformers
    const transformers: TokenTransformer[] = [];
    if (args.hashKey) {
      transformers.push(new HashTokenTransformer(args.hashKey));
    }
    if (args.encryptionKey) {
      transformers.push(new EncryptTokenTransformer(args.encryptionKey));
    }

    // Create metadata
    const metadata = new Metadata();

    // Process
    await PersonAttributesProcessor.process(reader, writer, transformers, metadata);

    // Close resources
    await reader.close();
    await writer.close();

    // Write metadata if requested
    if (args.metadataFile) {
      const metadataWriter = new MetadataJsonWriter(args.metadataFile);
      await metadataWriter.write(metadata.toJSON());
      console.log(`Metadata written to: ${args.metadataFile}`);
    }

    console.log('Token generation completed successfully!');
  } catch (error) {
    console.error('Error during token generation:', error);
    process.exit(1);
  }
}

// Run main if this is the entry point
if (require.main === module) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { main };
