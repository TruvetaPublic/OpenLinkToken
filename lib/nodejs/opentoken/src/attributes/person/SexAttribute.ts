/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { RegexValidator } from '../validation/RegexValidator';

/**
 * Represents an assigned sex of a person.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * these type of fields. It recognizes "Sex" or "Gender" as valid aliases for
 * this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format (Male or Female).
 */
export class SexAttribute extends BaseAttribute {
  private static readonly NAME = 'Sex';
  private static readonly ALIASES = ['Sex', 'Gender'];

  /**
   * Regular expression pattern for validating sex/gender values.
   *
   * This pattern matches the following formats (case-insensitive):
   * - "M" or "F"
   * - "Male" or "Female"
   * - "MALE" or "FEMALE"
   */
  private static readonly VALIDATE_REGEX = /^([Mm](ale|ALE)?|[Ff](emale|EMALE)?)$/;

  constructor() {
    super(SexAttribute.NAME, SexAttribute.ALIASES, [
      new RegexValidator(SexAttribute.VALIDATE_REGEX),
    ]);
  }

  normalize(value: string): string {
    if (!value || value.length === 0) {
      return value;
    }

    const firstChar = value.charAt(0).toUpperCase();
    switch (firstChar) {
      case 'M':
        return 'MALE';
      case 'F':
        return 'FEMALE';
      default:
        return value;
    }
  }
}
