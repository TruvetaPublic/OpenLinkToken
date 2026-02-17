/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { ParquetReader } from 'parquetjs';
import { ParquetCursor } from 'parquetjs/lib/reader';
import { Attribute } from '../../attributes/Attribute';
import { AttributeLoader } from '../../attributes/AttributeLoader';
import { PersonAttributesReader } from '../PersonAttributesReader';

/**
 * Reads person attributes from a Parquet file.
 * Implements the PersonAttributesReader interface.
 */
export class PersonAttributesParquetReader implements PersonAttributesReader {
  private reader: ParquetReader | null = null;
  private cursor: ParquetCursor | null = null;
  private currentRecord: any = null;
  private closed = false;
  private hasNextCalled = false;
  private hasNextResult = false;
  private attributeMap: Map<string, Attribute> = new Map();

  /**
   * Initialize the class with the input file in Parquet format.
   *
   * @param filePath the input file path
   */
  constructor(private filePath: string) {}

  /**
   * Initialize the reader (async operation)
   */
  async initialize(): Promise<void> {
    // Load attributes and build the mapping
    const attributes = AttributeLoader.load();
    for (const attribute of attributes) {
      for (const alias of attribute.getAliases()) {
        this.attributeMap.set(alias.toLowerCase(), attribute);
      }
    }

    // Open the Parquet file
    this.reader = await ParquetReader.openFile(this.filePath);
    this.cursor = this.reader.getCursor();
  }

  /**
   * Check if there are more records to read.
   *
   * @returns true if there are more records, false otherwise
   * @throws Error if the reader is closed
   */
  async hasNext(): Promise<boolean> {
    if (this.closed) {
      throw new Error('Reader is closed');
    }

    if (!this.hasNextCalled) {
      if (!this.cursor) {
        throw new Error('Reader not initialized. Call initialize() first.');
      }
      this.currentRecord = await this.cursor.next();
      this.hasNextResult = this.currentRecord !== null;
      this.hasNextCalled = true;
    }

    return this.hasNextResult;
  }

  /**
   * Get the next record from the Parquet file.
   *
   * @returns a person attributes map
   * @throws Error when there are no more records or reader is closed
   */
  async next(): Promise<Map<string, string>> {
    if (this.closed || !this.hasNextCalled) {
      throw new Error('Reader is closed or hasNext() not called');
    }

    if (!this.hasNextResult) {
      throw new Error('No more records');
    }

    this.hasNextCalled = false;

    // Map to attribute classes
    const attributes = new Map<string, string>();

    for (const [fieldName, fieldValue] of Object.entries(this.currentRecord)) {
      const attribute = this.attributeMap.get(fieldName.toLowerCase());
      if (attribute) {
        const attributeName = attribute.getName();
        const fieldValueStr =
          fieldValue !== null && fieldValue !== undefined ? String(fieldValue) : '';
        attributes.set(attributeName, fieldValueStr);
      }
    }

    return attributes;
  }

  /**
   * Close the Parquet reader and release resources.
   */
  async close(): Promise<void> {
    if (this.reader) {
      await this.reader.close();
    }
    this.closed = true;
  }
}
