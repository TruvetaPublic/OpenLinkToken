/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../attributes/AttributeExpression';

/**
 * A generic interface for tokens.
 *
 * A token is a set of attribute expressions concatenated together using
 * a vertical bar separator (|) to form a token signature.
 *
 * The token signature is then hashed and encrypted to form the final token.
 */
export interface Token {
  /**
   * Gets the unique identifier of the token.
   */
  getIdentifier(): string;

  /**
   * Gets the list of attribute expressions that define the token.
   */
  getDefinition(): AttributeExpression[];
}

/**
 * Token namespace for constants.
 */
export namespace Token {
  /**
   * The blank token constant representing an empty/null token value.
   */
  export const BLANK = '0000000000000000000000000000000000000000000000000000000000000000';
}
