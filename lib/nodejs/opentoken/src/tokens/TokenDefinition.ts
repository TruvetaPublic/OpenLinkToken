/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../attributes/AttributeExpression';
import { BaseTokenDefinition } from './BaseTokenDefinition';
import { TokenRegistry } from './TokenRegistry';

/**
 * Encapsulates the token definitions.
 *
 * The tokens are generated using some token generation rules. This class
 * encapsulates the definition of those rules. Together, they are commonly
 * referred to as **token definitions** or **rule definitions**.
 *
 * Each token/rule definition is a collection of `AttributeExpression` that are
 * concatenated together to get the token signature.
 *
 * @see AttributeExpression
 */
export class TokenDefinition implements BaseTokenDefinition {
  private readonly definitions: Map<string, AttributeExpression[]>;

  /**
   * Initializes the token definitions.
   */
  constructor() {
    // load all implementations of Token interface and store in definitions
    this.definitions = TokenRegistry.loadAllTokens();
  }

  getVersion(): string {
    return '2.0';
  }

  getTokenIdentifiers(): Set<string> {
    return new Set(this.definitions.keys());
  }

  getTokenDefinition(tokenId: string): AttributeExpression[] {
    return this.definitions.get(tokenId) || [];
  }
}
