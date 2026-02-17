/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { NotInValidator } from '../validation/NotInValidator';
import { RegexValidator } from '../validation/RegexValidator';
import { AttributeUtilities } from '../utilities/AttributeUtilities';

/**
 * Represents the social security number attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * social security number fields. It recognizes "SocialSecurityNumber" and
 * "NationalIdentificationNumber" as valid aliases for this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format (xxx-xx-xxxx).
 *
 * The attribute also performs validation on input values, ensuring they match
 * the following format:
 * - xxx-xx-xxxx
 * - xxxxxxxxx
 */
export class SocialSecurityNumberAttribute extends BaseAttribute {
  private static readonly NAME = 'SocialSecurityNumber';
  // Aliases must match Java implementation for cross-language parity
  private static readonly ALIASES = ['SocialSecurityNumber', 'NationalIdentificationNumber'];
  private static readonly MIN_SSN_LENGTH = 7;
  private static readonly SSN_LENGTH = 9;

  /**
   * Regular expression to validate Social Security Numbers (SSNs).
   *
   * Allows:
   * - 7 to 9 digits, optionally followed by a decimal separator and zero(s).
   * - Properly formatted SSNs with or without dashes, ensuring:
   *   - The first three digits are not "000", "666", or in the range "900-999".
   *   - The middle two digits are not "00".
   *   - The last four digits are not "0000".
   */
  // Mirrors Java regex semantics (dynamic decimal separator simplified to '.'):
  // ^(?:\d{7,9}(\.0*)?)|(?:^(?!000|666|9\d\d)(\d{3})-?(?!00)(\d{2})-?(?!0000)(\d{4})$)
  private static readonly SSN_REGEX = /^(?:\d{7,9}(\.0*)?)|(?:^(?!000|666|9\d\d)(\d{3})-?(?!00)(\d{2})-?(?!0000)(\d{4})$)/;

  private static readonly DIGITS_ONLY_PATTERN = /^\d+$/;

  // Use the exact invalid SSN list (dash formatted) from Java implementation for parity
  private static readonly INVALID_SSNS = new Set([
    '111-11-1111',
    '222-22-2222',
    '333-33-3333',
    '444-44-4444',
    '555-55-5555',
    '777-77-7777',
    '888-88-8888',
    '001-23-4567',
    '009-99-9999',
    '010-10-1010',
    '012-34-5678',
    '087-65-4321',
    '098-76-5432',
    '099-99-9999',
    '111-22-3333',
    '121-21-2121',
    '123-45-6789',
    '123-45-9999'
  ]);

  constructor() {
    super(SocialSecurityNumberAttribute.NAME, SocialSecurityNumberAttribute.ALIASES, [
      new NotInValidator(SocialSecurityNumberAttribute.INVALID_SSNS),
      new RegexValidator(SocialSecurityNumberAttribute.SSN_REGEX),
    ]);
  }

  /**
   * Validates the social security number value.
   * This method overrides the validate method from BaseAttribute
   * to ensure that the value is normalized before validation.
   */
  validate(value: string): boolean {
    return super.validate(this.normalize(value)); // Validate normalized SSN
  }

  /**
   * Normalize the social security number value. Remove whitespace & dashes,
   * strip any decimal extension, pad with zeros (if 7-8 digits) then format
   * as xxx-xx-xxxx. If not possible return the original trimmed value.
   */
  normalize(originalValue: string): string {
    if (!originalValue || originalValue.length === 0) {
      return originalValue;
    }

    // Remove any whitespace characters
    let trimmedValue = originalValue.trim().replace(AttributeUtilities.WHITESPACE, '');

    // Remove dashes
    let normalizedValue = trimmedValue.replace(/-/g, '');

    // Remove decimal portion if present
    const decimalIndex = normalizedValue.indexOf('.');
    if (decimalIndex !== -1) {
      normalizedValue = normalizedValue.substring(0, decimalIndex);
    }

    // Digits only check
    if (!SocialSecurityNumberAttribute.DIGITS_ONLY_PATTERN.test(normalizedValue)) {
      return originalValue.trim();
    }

    // Length check
    if (
      normalizedValue.length < SocialSecurityNumberAttribute.MIN_SSN_LENGTH ||
      normalizedValue.length > SocialSecurityNumberAttribute.SSN_LENGTH
    ) {
      return originalValue.trim();
    }

    normalizedValue = this.padWithZeros(normalizedValue);

    // Format with dashes (xxx-xx-xxxx)
    return `${normalizedValue.substring(0, 3)}-${normalizedValue.substring(3, 5)}-${normalizedValue.substring(5)}`;
  }

  /**
   * If SSN is between 7-8 digits, pad with leading zeros to reach 9 digits.
   *
   * Examples:
   * - "1234567" -> "001234567"
   * - "12345678" -> "012345678"
   */
  private padWithZeros(ssn: string): string {
    if (
      ssn.length >= SocialSecurityNumberAttribute.MIN_SSN_LENGTH &&
      ssn.length < SocialSecurityNumberAttribute.SSN_LENGTH
    ) {
      ssn = ssn.padStart(SocialSecurityNumberAttribute.SSN_LENGTH, '0');
    }
    return ssn;
  }
}
