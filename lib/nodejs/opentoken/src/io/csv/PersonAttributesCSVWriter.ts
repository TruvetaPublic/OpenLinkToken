/**
 * Copyright (c) Truveta. All rights reserved.
 */

import * as fs from 'fs';
import { stringify } from 'csv-stringify';
import { PersonAttributesWriter } from '../PersonAttributesWriter';

/**
 * Writes person attributes to a CSV file.
 */
export class PersonAttributesCSVWriter implements PersonAttributesWriter {
  private stringifier: any;
  private stream: fs.WriteStream;

  constructor(filePath: string) {
    this.stream = fs.createWriteStream(filePath);
    this.stringifier = stringify({
      header: true,
    });
    this.stringifier.pipe(this.stream);
  }

  async writeAttributes(data: Map<string, string>): Promise<void> {
    const record: Record<string, string> = {};
    for (const [key, value] of data.entries()) {
      record[key] = value;
    }

    return new Promise((resolve, reject) => {
      this.stringifier.write(record, (err: Error | null) => {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }

  async close(): Promise<void> {
    return new Promise((resolve) => {
      this.stringifier.end(() => {
        this.stream.end(resolve);
      });
    });
  }
}
