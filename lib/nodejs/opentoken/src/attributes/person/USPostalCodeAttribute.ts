/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { RegexValidator } from '../validation/RegexValidator';
import { NotStartsWithValidator } from '../validation/NotStartsWithValidator';

/**
 * Represents US postal codes (ZIP codes).
 *
 * This class handles validation and normalization of US ZIP codes, supporting
 * both 5-digit format (12345) and 5+4 format (12345-6789).
 */
export class USPostalCodeAttribute extends BaseAttribute {
  private static readonly NAME = 'USPostalCode';
  private static readonly ALIASES = ['USPostalCode', 'USZipCode'];

  /**
   * Regular expression pattern for validating US postal (ZIP) codes.
   */
  private static readonly US_ZIP_REGEX = /^\s*(\d{3}|\d{4}|\d{5}(-\d{4})?|\d{9})\s*$/;

  private static readonly INVALID_ZIP_CODES = new Set([
    '11111',
    '22222',
    '33333',
    '66666',
    '77777',
    '99999',
    '01234',
    '12345',
    '54321',
    '98765',
    '000',
    '555',
    '888',
  ]);

  private minLength: number;

  constructor(minLength: number = 5) {
    super(USPostalCodeAttribute.NAME, USPostalCodeAttribute.ALIASES, [
      new RegexValidator(USPostalCodeAttribute.US_ZIP_REGEX),
      new NotStartsWithValidator(USPostalCodeAttribute.INVALID_ZIP_CODES),
    ]);
    this.minLength = minLength;
  }

  /**
   * Normalizes a US ZIP code to standard 5-digit format.
   */
  normalize(value: string): string {
    if (!value) {
      return value;
    }

    const trimmed = value.trim().replace(/\s+/g, '');

    // Check if it's a 3-digit ZIP code (ZIP-3) - pad with "00" if minLength allows
    if (/^\d{3}$/.test(trimmed)) {
      if (this.minLength <= 3) {
        return trimmed + '00';
      }
      return value.trim();
    }

    // Check if it's a 4-digit ZIP code (ZIP-4) - pad with "0" if minLength allows
    if (/^\d{4}$/.test(trimmed)) {
      if (this.minLength <= 4) {
        return trimmed + '0';
      }
      return value.trim();
    }

    // Check if it's a US ZIP code (5 digits, 5+4 with dash, or 9 digits without dash)
    if (/^\d{5}(-?\d{4})?$/.test(trimmed) || /^\d{9}$/.test(trimmed)) {
      return trimmed.substring(0, 5);
    }

    return value.trim();
  }
}
