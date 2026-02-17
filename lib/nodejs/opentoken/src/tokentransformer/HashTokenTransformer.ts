/**
 * Copyright (c) Truveta. All rights reserved.
 */

import * as crypto from 'crypto';
import { TokenTransformer } from './TokenTransformer';

/**
 * Transforms the token using a cryptographic hash function with a secret key.
 *
 * Uses HMAC-SHA256 algorithm.
 */
export class HashTokenTransformer implements TokenTransformer {
  private hashingSecret: string;

  /**
   * Initializes the transformer with the secret key.
   *
   * @param hashingSecret - The cryptographic secret key.
   */
  constructor(hashingSecret: string) {
    if (!hashingSecret || hashingSecret.trim().length === 0) {
      throw new Error('Hashing secret cannot be null or empty');
    }
    this.hashingSecret = hashingSecret;
  }

  /**
   * Hash token transformer.
   *
   * The token is transformed using HMAC SHA256 algorithm.
   *
   * @param token - The token to hash.
   * @returns Hashed token in base64 format.
   */
  transform(token: string): string {
    if (!token || token.trim().length === 0) {
      throw new Error('Token cannot be null or empty');
    }

    const hmac = crypto.createHmac('sha256', this.hashingSecret);
    hmac.update(token);
    const hash = hmac.digest();
    return Buffer.from(hash).toString('base64');
  }
}
