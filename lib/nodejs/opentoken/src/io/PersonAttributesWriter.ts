/**
 * Copyright (c) Truveta. All rights reserved.
 */

export interface PersonAttributesWriter {
  writeAttributes(data: Map<string, string>): Promise<void>;
  close(): Promise<void>;
}
