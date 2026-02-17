/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Interface for tokenizing values into tokens.
 *
 * A tokenizer takes a string value (typically a token signature) and
 * transforms it into a token using various cryptographic or encoding
 * techniques.
 */
export interface Tokenizer {
  /**
   * Generates a token from the given value.
   *
   * @param value - The value to tokenize (e.g., a token signature).
   * @returns the generated token. Returns a default empty token value
   *          if the input value is null or blank.
   * @throws Error if an error occurs during tokenization, such as
   *              unsupported encoding or cryptographic algorithm issues.
   */
  tokenize(value: string | null): Promise<string>;
}
