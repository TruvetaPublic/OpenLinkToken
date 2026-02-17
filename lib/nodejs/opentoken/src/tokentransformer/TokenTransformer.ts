/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Interface for token transformers.
 */
export interface TokenTransformer {
  /**
   * Transforms a token.
   *
   * @param token - The token to transform.
   * @returns The transformed token.
   */
  transform(token: string): string;
}
