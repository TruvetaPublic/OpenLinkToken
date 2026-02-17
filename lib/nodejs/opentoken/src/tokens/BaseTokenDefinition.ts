/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../attributes/AttributeExpression';

/**
 * A generic interface for the token definition.
 */
export interface BaseTokenDefinition {
  /**
   * Get the version of the token definition.
   *
   * @returns the token definition version.
   */
  getVersion(): string;

  /**
   * Get all token identifiers. For example, a set of `{ T1, T2, T3, T4, T5 }`.
   *
   * The token identifiers are also called rule identifiers because every token is
   * generated from rule definition.
   *
   * @returns a set of token identifiers.
   */
  getTokenIdentifiers(): Set<string>;

  /**
   * Get the token definition for a given token identifier.
   *
   * @param tokenId - The token/rule identifier.
   * @returns a list of token/rule definition.
   */
  getTokenDefinition(tokenId: string): AttributeExpression[];
}
