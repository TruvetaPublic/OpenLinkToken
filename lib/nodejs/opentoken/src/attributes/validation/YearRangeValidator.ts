/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeValidator } from './AttributeValidator';

/**
 * A Validator that asserts that a year value is within
 * an acceptable range (between 1910 and current year).
 *
 * This validator checks that years are:
 * - Not before 1910
 * - Not after the current year
 *
 * If the year is outside this range, the validation fails.
 */
export class YearRangeValidator implements AttributeValidator {
  private static readonly MIN_YEAR = 1910;

  /**
   * Validates that the year value is within acceptable range.
   *
   * @param value - The year string to validate
   * @returns true if the year is within acceptable range (1910 to current year), false otherwise
   */
  validate(value: string): boolean {
    if (!value || value.trim().length === 0) {
      return false;
    }

    try {
      const year = parseInt(value.trim(), 10);
      if (isNaN(year)) {
        return false;
      }
      const currentYear = new Date().getFullYear();
      return year >= YearRangeValidator.MIN_YEAR && year <= currentYear;
    } catch (e) {
      return false;
    }
  }
}
