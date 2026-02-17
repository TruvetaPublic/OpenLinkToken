/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { YearAttribute } from '../general/YearAttribute';
import { YearRangeValidator } from '../validation/YearRangeValidator';

/**
 * Represents the birth year attribute.
 *
 * This class extends YearAttribute and provides functionality for working with
 * birth year fields. It recognizes "BirthYear" as a valid alias for this
 * attribute type.
 *
 * The attribute performs normalization on input values by trimming whitespace
 * and validates that the birth year is a 4-digit year between 1910 and the current year.
 */
export class BirthYearAttribute extends YearAttribute {
  constructor() {
    super([new YearRangeValidator()]);
    this.name = 'BirthYear';
    this.aliases = ['BirthYear', 'YearOfBirth'];
  }
}
