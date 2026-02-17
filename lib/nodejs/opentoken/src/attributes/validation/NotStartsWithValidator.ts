/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeValidator } from './AttributeValidator';

/**
 * A Validator that ensures a string does not start with any of the specified prefixes.
 *
 * This validator checks that the given value (after trimming) does not begin
 * with any of the prefixes in the provided set.
 */
export class NotStartsWithValidator implements AttributeValidator {
  private prefixes: Set<string>;

  /**
   * Constructs a NotStartsWithValidator with the given set of prefixes.
   *
   * @param prefixes - The set of prefixes that the value should not start with
   */
  constructor(prefixes: Set<string>) {
    this.prefixes = prefixes;
  }

  /**
   * Validates that the value does not start with any of the forbidden prefixes.
   *
   * @param value - The string to validate
   * @returns true if the value does not start with any prefix, false otherwise
   */
  validate(value: string): boolean {
    if (!value) {
      return false;
    }

    const trimmed = value.trim();

    for (const prefix of this.prefixes) {
      if (trimmed.startsWith(prefix)) {
        return false;
      }
    }

    return true;
  }
}
