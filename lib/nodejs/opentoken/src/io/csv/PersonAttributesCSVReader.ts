/**
 * Copyright (c) Truveta. All rights reserved.
 */

import * as fs from 'fs';
import { parse, Parser } from 'csv-parse';
import { PersonAttributesReader } from '../PersonAttributesReader';
import { Attribute } from '../../attributes/Attribute';
import { AttributeLoader } from '../../attributes/AttributeLoader';

/**
 * Reads person attributes from a CSV file.
 */
export class PersonAttributesCSVReader implements PersonAttributesReader {
  private parser: Parser;
  private done: boolean = false;
  private readonly queue: Record<string, unknown>[] = [];
  private readonly waiters: Array<{ resolve: (value: boolean) => void; reject: (error: Error) => void }> = [];
  private error?: Error;
  private readonly attributeMap: Map<string, Attribute> = new Map();
  private headers: string[] = [];

  constructor(filePath: string) {
    const stream = fs.createReadStream(filePath);
    this.parser = stream.pipe(
      parse({
        columns: true,
        skip_empty_lines: true,
        trim: true,
      })
    );
    
    // Load all available attributes
    const attributes = AttributeLoader.load();
    
    this.parser.on('readable', () => {
      let record: Record<string, unknown> | null;
      while ((record = this.parser.read()) !== null) {
        // Build attribute map from headers on first record
        if (this.headers.length === 0 && record) {
          this.headers = Object.keys(record);
          for (const headerName of this.headers) {
            for (const attribute of attributes) {
              for (const alias of attribute.getAliases()) {
                if (headerName.toLowerCase() === alias.toLowerCase()) {
                  this.attributeMap.set(headerName, attribute);
                  break;
                }
              }
              if (this.attributeMap.has(headerName)) break;
            }
          }
        }
        this.queue.push(record);
      }
      this.drainWaiters();
    });

    this.parser.once('end', () => {
      this.done = true;
      this.drainWaiters();
    });

    this.parser.once('error', (err: Error) => {
      this.error = err;
      this.drainWaiters();
    });
  }

  async hasNext(): Promise<boolean> {
    if (this.error) {
      throw this.error;
    }

    if (this.queue.length > 0) {
      return true;
    }

    if (this.done) {
      return false;
    }

    return new Promise<boolean>((resolve, reject) => {
      this.waiters.push({ resolve, reject });
    });
  }

  async next(): Promise<Map<string, string>> {
    if (this.error) {
      throw this.error;
    }

    const record = this.queue.shift();
    if (!record) {
      throw new Error('No more records');
    }

    const result = new Map<string, string>();
    for (const [key, value] of Object.entries(record)) {
      const attribute = this.attributeMap.get(key);
      if (attribute && typeof value === 'string') {
        result.set(key, value);
      }
    }

    return result;
  }

  async close(): Promise<void> {
    this.done = true;
    this.parser.destroy();
    this.drainWaiters();
  }

  private drainWaiters(): void {
    if (this.error) {
      while (this.waiters.length > 0) {
        const waiter = this.waiters.shift();
        waiter?.reject(this.error);
      }
      return;
    }

    while (this.queue.length > 0 && this.waiters.length > 0) {
      const waiter = this.waiters.shift();
      waiter?.resolve(true);
    }

    if (this.done && this.queue.length === 0) {
      while (this.waiters.length > 0) {
        const waiter = this.waiters.shift();
        waiter?.resolve(false);
      }
    }
  }
}
