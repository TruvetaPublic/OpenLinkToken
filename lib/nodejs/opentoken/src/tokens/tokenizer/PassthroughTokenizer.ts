/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { Token } from '../Token';
import { Tokenizer } from './Tokenizer';
import { TokenTransformer } from '../../tokentransformer/TokenTransformer';

/**
 * A tokenizer that returns the input value unchanged (passthrough).
 *
 * This tokenizer does not apply any hashing or cryptographic transformation
 * to the input value. It simply returns the input as-is, optionally applying
 * token transformers if provided.
 *
 * This is useful for scenarios where you want to preserve the original token
 * signature without any cryptographic processing, while still allowing for
 * optional transformations (e.g., encryption).
 */
export class PassthroughTokenizer implements Tokenizer {
  /**
   * The empty token value.
   *
   * This is the value returned when the token signature is `null` or blank.
   */
  static readonly EMPTY = Token.BLANK;
  
  private readonly tokenTransformerList: TokenTransformer[];

  /**
   * Initializes the tokenizer.
   *
   * @param tokenTransformerList - A list of token transformers.
   */
  constructor(tokenTransformerList: TokenTransformer[]) {
    this.tokenTransformerList = tokenTransformerList;
  }

  /**
   * Returns the input value unchanged (passthrough).
   *
   * `Token = value`
   *
   * The token is optionally transformed with one or more transformers.
   *
   * @param value - The token signature value.
   * @returns the token. If the token signature value is `null` or blank,
   *          {@link EMPTY} is returned.
   * @throws Error if an error is thrown by the transformer.
   */
  async tokenize(value: string | null): Promise<string> {
    if (!value || value.trim() === '') {
      return PassthroughTokenizer.EMPTY;
    }

    let transformedToken = value;

    for (const tokenTransformer of this.tokenTransformerList) {
      transformedToken = tokenTransformer.transform(transformedToken);
    }
    
    return transformedToken;
  }
}
