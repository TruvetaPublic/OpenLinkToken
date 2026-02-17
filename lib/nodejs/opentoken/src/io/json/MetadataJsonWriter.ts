/**
 * Copyright (c) Truveta. All rights reserved.
 */

import * as fs from 'fs';
import { MetadataWriter } from '../MetadataWriter';

/**
 * Writes metadata to a JSON file.
 */
export class MetadataJsonWriter implements MetadataWriter {
  private filePath: string;

  constructor(filePath: string) {
    this.filePath = filePath;
  }

  async write(metadata: any): Promise<void> {
    const jsonString = JSON.stringify(metadata, null, 2);
    await fs.promises.writeFile(this.filePath, jsonString, 'utf8');
  }
}
