/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * A generic interface for attributes.
 *
 * An attribute is a piece of information that can be used to generate a token.
 * An attribute has a name and a list of aliases. The name is the canonical name
 * of the attribute, while the aliases are alternative names that can be used to
 * refer to the attribute.
 *
 * An attribute also has a normalization function that converts the attribute
 * value to a canonical form. This is useful for attributes that have multiple
 * valid representations.
 *
 * An attribute also has a validation function that checks if the attribute value
 * is valid.
 */
export interface Attribute {
  /**
   * Gets the name of the attribute.
   */
  getName(): string;

  /**
   * Gets the aliases of the attribute.
   */
  getAliases(): string[];

  /**
   * Normalizes the attribute value.
   *
   * @param value - The attribute value.
   * @returns The normalized attribute value.
   */
  normalize(value: string): string;

  /**
   * Validates the attribute value.
   *
   * @param value - The attribute value.
   * @returns true if the attribute value is valid; false otherwise.
   */
  validate(value: string): boolean;
}
