/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { DateAttribute } from '../general/DateAttribute';
import { DateRangeValidator } from '../validation/DateRangeValidator';

/**
 * Represents the birth date attribute.
 *
 * This class extends DateAttribute and provides functionality for working with
 * birth date fields. It recognizes "BirthDate" and "DateOfBirth" as valid aliases
 * for this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format (yyyy-MM-dd) (inherited from DateAttribute).
 *
 * The attribute also performs validation on input values, ensuring they:
 * - Match one of the supported date formats (inherited from DateAttribute)
 * - Fall within an acceptable range for birth dates (1910-01-01 to today)
 */
export class BirthDateAttribute extends DateAttribute {
  private static readonly NAME = 'BirthDate';
  private static readonly ALIASES = ['BirthDate', 'DateOfBirth'];

  constructor() {
    const minDate = new Date('1910-01-01');
    super(BirthDateAttribute.NAME, BirthDateAttribute.ALIASES, [
      new DateRangeValidator(minDate, null, true),
    ]);
  }
}
