/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { RegexValidator } from '../validation/RegexValidator';
import { NotStartsWithValidator } from '../validation/NotStartsWithValidator';

/**
 * Represents Canadian postal codes.
 *
 * This class handles validation and normalization of Canadian postal codes,
 * supporting the A1A 1A1 format (letter-digit-letter space digit-letter-digit).
 */
export class CanadianPostalCodeAttribute extends BaseAttribute {
  private static readonly NAME = 'CanadianPostalCode';
  private static readonly ALIASES = ['CanadianPostalCode', 'CanadianZipCode'];

  /**
   * Regular expression pattern for validating Canadian postal codes.
   */
  private static readonly CANADIAN_POSTAL_REGEX =
    /^\s*[A-Za-z]\d[A-Za-z](\s?\d([A-Za-z]\d?)?)?\s*$/;

  private static readonly INVALID_ZIP_CODES = new Set([
    'A1A 1A1',
    'X0X 0X0',
    'Y0Y 0Y0',
    'Z0Z 0Z0',
    'A0A 0A0',
    'B1B 1B1',
    'C2C 2C2',
    'K1A',
    'M7A',
    'H0H',
  ]);

  private minLength: number;

  constructor(minLength: number = 6) {
    super(CanadianPostalCodeAttribute.NAME, CanadianPostalCodeAttribute.ALIASES, [
      new RegexValidator(CanadianPostalCodeAttribute.CANADIAN_POSTAL_REGEX),
      new NotStartsWithValidator(CanadianPostalCodeAttribute.INVALID_ZIP_CODES),
    ]);
    this.minLength = minLength;
  }

  /**
   * Normalizes a Canadian postal code to standard A1A 1A1 format.
   */
  normalize(value: string): string {
    if (!value) {
      return value;
    }

    const trimmed = value.trim().replace(/\s+/g, '');

    // Check if it's a 3-character Canadian postal code (ZIP-3)
    if (/^[A-Za-z]\d[A-Za-z]$/.test(trimmed)) {
      if (this.minLength <= 3) {
        return trimmed.toUpperCase() + ' 000';
      }
      return value.trim();
    }

    // Check if it's a 4-character partial postal code (e.g., "A1A1")
    if (/^[A-Za-z]\d[A-Za-z]\d$/.test(trimmed)) {
      if (this.minLength <= 4) {
        const upper = trimmed.toUpperCase();
        return upper.substring(0, 3) + ' ' + upper.substring(3) + 'A0';
      }
      return value.trim();
    }

    // Check if it's a 5-character partial postal code (e.g., "A1A1A")
    if (/^[A-Za-z]\d[A-Za-z]\d[A-Za-z]$/.test(trimmed)) {
      if (this.minLength <= 5) {
        const upper = trimmed.toUpperCase();
        return upper.substring(0, 3) + ' ' + upper.substring(3) + '0';
      }
      return value.trim();
    }

    // Check if it's a Canadian postal code (6 alphanumeric characters)
    if (/^[A-Za-z]\d[A-Za-z]\d[A-Za-z]\d$/.test(trimmed)) {
      const upper = trimmed.toUpperCase();
      return upper.substring(0, 3) + ' ' + upper.substring(3, 6);
    }

    return value.trim();
  }
}
