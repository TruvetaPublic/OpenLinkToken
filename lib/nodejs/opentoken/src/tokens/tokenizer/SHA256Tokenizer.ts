/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { createHash } from 'node:crypto';
import { Token } from '../Token';
import { Tokenizer } from './Tokenizer';
import { TokenTransformer } from '../../tokentransformer/TokenTransformer';

/**
 * Generates token using SHA256 digest.
 *
 * The token is generated using SHA256 digest and is hex encoded.
 * If token transformations are specified, the token is then transformed
 * by those transformers.
 */
export class SHA256Tokenizer implements Tokenizer {
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
   * Generates the token for the given token signature.
   *
   * `Token = Hex(Sha256(token-signature))`
   *
   * The token is optionally transformed with one or more transformers.
   *
   * @param value - The token signature value.
   * @returns the token. If the token signature value is `null` or blank,
   *          {@link EMPTY} is returned.
   * @throws Error if an error occurs during tokenization.
   */
  async tokenize(value: string | null): Promise<string> {
    if (!value || value.trim() === '') {
      return SHA256Tokenizer.EMPTY;
    }

    const hash = createHash('sha256');
    hash.update(value, 'utf8');
    let transformedToken = hash.digest('hex');

    for (const tokenTransformer of this.tokenTransformerList) {
      transformedToken = tokenTransformer.transform(transformedToken);
    }
    
    return transformedToken;
  }
}
