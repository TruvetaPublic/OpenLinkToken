/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { RegexValidator } from '../validation/RegexValidator';
import { AttributeValidator } from '../validation/AttributeValidator';

/**
 * Represents a generic year attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * year fields. It recognizes "Year" as a valid alias for this attribute type.
 *
 * The attribute performs normalization on input values by trimming whitespace
 * and validates that the year is a 4-digit year format.
 */
export class YearAttribute extends BaseAttribute {
  private static readonly NAME = 'Year';
  private static readonly ALIASES = ['Year'];
  private static readonly YEAR_REGEX = /^\s*\d{4}\s*$/;
  private static readonly YEAR_PATTERN = /\d{4}/;

  constructor(additionalValidators: AttributeValidator[] = []) {
    super(
      YearAttribute.NAME,
      YearAttribute.ALIASES,
      [new RegexValidator(YearAttribute.YEAR_REGEX), ...additionalValidators]
    );
  }

  normalize(value: string): string {
    if (!value) {
      throw new Error('Year value cannot be null');
    }

    const trimmed = value.trim();

    // Check if it matches the 4-digit year format
    if (!YearAttribute.YEAR_PATTERN.test(trimmed)) {
      throw new Error(`Invalid year format: ${value}`);
    }

    try {
      const year = parseInt(trimmed, 10);
      if (isNaN(year)) {
        throw new Error(`Invalid year format: ${value}`);
      }
      return String(year);
    } catch (e) {
      throw new Error(`Invalid year format: ${value}`);
    }
  }
}
