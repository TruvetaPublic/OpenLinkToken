/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeValidator } from './AttributeValidator';

/**
 * A Validator that asserts that the age value is within
 * an acceptable range (between 0 and 120).
 *
 * This validator checks that ages are:
 * - Not negative
 * - Not greater than 120 years
 *
 * If the age is outside this range, the validation fails.
 */
export class AgeRangeValidator implements AttributeValidator {
  private static readonly MIN_AGE = 0;
  private static readonly MAX_AGE = 120;

  /**
   * Validates that the age value is within acceptable range.
   *
   * @param value - The age string to validate
   * @returns true if the age is within acceptable range (0 to 120), false otherwise
   */
  validate(value: string): boolean {
    if (!value || value.trim().length === 0) {
      return false;
    }

    try {
      const age = parseInt(value.trim(), 10);
      if (isNaN(age)) {
        return false;
      }
      return age >= AgeRangeValidator.MIN_AGE && age <= AgeRangeValidator.MAX_AGE;
    } catch (e) {
      return false;
    }
  }
}
