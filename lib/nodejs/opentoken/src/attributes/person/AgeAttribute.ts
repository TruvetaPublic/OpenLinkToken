/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { RegexValidator } from '../validation/RegexValidator';
import { AgeRangeValidator } from '../validation/AgeRangeValidator';

/**
 * Represents the age attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * age fields. It recognizes "Age" as the primary alias for this attribute type.
 *
 * The attribute performs normalization on input values, trimming whitespace and
 * ensuring the value is a valid integer.
 *
 * The attribute also performs validation on input values, ensuring they:
 * - Are numeric (integers only)
 * - Fall within an acceptable range (0-120)
 */
export class AgeAttribute extends BaseAttribute {
  private static readonly NAME = 'Age';
  private static readonly ALIASES = ['Age'];
  private static readonly AGE_REGEX = /^\s*\d+\s*$/;

  constructor() {
    super(AgeAttribute.NAME, AgeAttribute.ALIASES, [
      new RegexValidator(AgeAttribute.AGE_REGEX),
      new AgeRangeValidator(),
    ]);
  }

  normalize(value: string): string {
    if (!value) {
      throw new Error('Age value cannot be null');
    }

    const trimmed = value.trim();

    try {
      const age = parseInt(trimmed, 10);
      if (isNaN(age)) {
        throw new Error(`Invalid age format: ${value}`);
      }
      return String(age);
    } catch (e) {
      throw new Error(`Invalid age format: ${value}`);
    }
  }
}
