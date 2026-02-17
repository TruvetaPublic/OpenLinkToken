/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { TokenTransformer } from './TokenTransformer';

/**
 * A **No Operation** token transformer. No transformation is applied whatsoever.
 */
export class NoOperationTokenTransformer implements TokenTransformer {
  /**
   * No operation token transformer.
   *
   * Does not transform the token in any ways.
   *
   * @param token - The token to transform.
   * @returns the same token, unchanged.
   */
  transform(token: string): string {
    return token;
  }
}
