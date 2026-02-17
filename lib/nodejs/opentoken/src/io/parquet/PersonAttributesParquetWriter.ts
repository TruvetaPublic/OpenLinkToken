/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { ParquetWriter, ParquetSchema } from 'parquetjs';
import * as fs from 'fs';
import * as path from 'path';
import { PersonAttributesWriter } from '../PersonAttributesWriter';

/**
 * The PersonAttributeParquetWriter class is responsible for writing person
 * attributes to a Parquet file.
 * It implements the PersonAttributesWriter interface.
 */
export class PersonAttributesParquetWriter implements PersonAttributesWriter {
  private writer: ParquetWriter | null = null;
  private schema: ParquetSchema | null = null;
  private initialized = false;
  private firstRecordKeys: string[] = [];

  /**
   * Initialize the class with the output file in Parquet format.
   *
   * @param filePath the output file path
   */
  constructor(private filePath: string) {
    // Create directory if it doesn't exist
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  /**
   * Write attributes to the Parquet file.
   *
   * @param attributes a map of person attributes
   */
  async writeAttributes(attributes: Map<string, string>): Promise<void> {
    const attributesObj: { [key: string]: string } = {};
    attributes.forEach((value, key) => {
      attributesObj[key] = value;
    });

    if (!this.initialized) {
      await this.initializeWriter(attributesObj);
    }

    // Create a row with all fields from the schema
    const row: { [key: string]: string } = {};
    for (const key of this.firstRecordKeys) {
      row[key] = attributesObj[key] || '';
    }

    await this.writer!.appendRow(row);
  }

  /**
   * Close the Parquet writer.
   */
  async close(): Promise<void> {
    if (this.writer) {
      await this.writer.close();
    }
  }

  /**
   * Initialize the Parquet writer with schema based on the first record.
   *
   * @param firstRecord the first record to determine schema
   */
  private async initializeWriter(firstRecord: { [key: string]: string }): Promise<void> {
    // Create schema based on the first record
    const schemaFields: { [key: string]: any } = {};

    for (const [key, value] of Object.entries(firstRecord)) {
      if (value !== null && value !== undefined) {
        this.firstRecordKeys.push(key);
        schemaFields[key] = { type: 'UTF8', optional: true };
      }
    }

    this.schema = new ParquetSchema(schemaFields);

    // Initialize the Parquet writer
    this.writer = await ParquetWriter.openFile(this.schema, this.filePath);
    this.initialized = true;
  }
}
