/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Metadata about the token generation process.
 */
export class Metadata {
  version: string;
  timestamp: string;
  totalRows: number;
  totalRowsWithInvalidAttributes: number;
  invalidAttributesByType: Record<string, number>;
  blankTokensByRule: Record<string, number>;

  constructor() {
    this.version = '1.10.0';
    this.timestamp = new Date().toISOString();
    this.totalRows = 0;
    this.totalRowsWithInvalidAttributes = 0;
    this.invalidAttributesByType = {};
    this.blankTokensByRule = {};
  }

  toJSON(): any {
    return {
      version: this.version,
      timestamp: this.timestamp,
      totalRows: this.totalRows,
      totalRowsWithInvalidAttributes: this.totalRowsWithInvalidAttributes,
      invalidAttributesByType: this.invalidAttributesByType,
      blankTokensByRule: this.blankTokensByRule,
    };
  }
}
