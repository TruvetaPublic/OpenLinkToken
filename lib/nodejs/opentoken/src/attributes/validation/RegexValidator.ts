/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeValidator } from './AttributeValidator';

/**
 * A validator that validates a value against a regular expression.
 */
export class RegexValidator implements AttributeValidator {
  private pattern: RegExp;

  /**
   * Constructs a new RegexValidator.
   *
   * @param pattern - The regular expression pattern to validate against.
   */
  constructor(pattern: string | RegExp) {
    this.pattern = typeof pattern === 'string' ? new RegExp(pattern) : pattern;
  }

  /**
   * Validates the given value against the regular expression.
   *
   * @param value - The value to validate.
   * @returns true if the value matches the pattern; false otherwise.
   */
  validate(value: string): boolean {
    if (!value) {
      return false;
    }
    return this.pattern.test(value);
  }
}
