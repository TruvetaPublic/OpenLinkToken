/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * A generic interface for a streaming person attributes reader.
 * Returns Map of attribute names to their string values.
 */
export interface PersonAttributesReader {
  hasNext(): Promise<boolean>;
  next(): Promise<Map<string, string>>;
  close(): Promise<void>;
}
