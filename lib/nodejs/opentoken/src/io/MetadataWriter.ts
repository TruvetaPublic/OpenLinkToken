/**
 * Copyright (c) Truveta. All rights reserved.
 */

export interface MetadataWriter {
  write(metadata: any): Promise<void>;
}
