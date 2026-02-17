/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { NotInValidator } from '../validation/NotInValidator';
import { RegexValidator } from '../validation/RegexValidator';
import { AttributeUtilities } from '../utilities/AttributeUtilities';

/**
 * Represents the last name (surname) of a person.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * last name fields. It recognizes "LastName" and "Surname" as valid aliases.
 *
 * The attribute validates that the last name:
 * - Must be at least 2 characters long
 * - For 2-character names, must contain at least one vowel or be "Ng"
 * - Cannot be a common placeholder value
 */
export class LastNameAttribute extends BaseAttribute {
  private static readonly NAME = 'LastName';
  // Align aliases with Java implementation (LastName, Surname)
  private static readonly ALIASES = ['LastName', 'Surname'];

  // Java LAST_NAME_REGEX replicated for parity
  private static readonly LAST_NAME_REGEX = /^(?:\s*(?:(?:.{3,})|(?:[^aeiouAEIOU\s][aeiouAEIOU])|(?:[aeiouAEIOU][^aeiouAEIOU\s])|(?:[aeiouAEIOU]{2})|(?:[Nn][Gg]))\s*)$/;

  constructor() {
    super(LastNameAttribute.NAME, LastNameAttribute.ALIASES, [
      new RegexValidator(LastNameAttribute.LAST_NAME_REGEX),
      new NotInValidator(AttributeUtilities.COMMON_PLACEHOLDER_NAMES),
    ]);
  }

  validate(value: string): boolean {
    // Reject null early
    if (value == null) {
      return false;
    }

    // Reject single letters explicitly (Java logic)
    const trimmed = value.trim();
    if (trimmed.length === 1) {
      return false;
    }

    return super.validate(value);
  }

  normalize(value: string): string {
    let normalizedValue = AttributeUtilities.normalizeDiacritics(value);

    const valueWithoutSuffix = normalizedValue.replace(AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN, '');
    if (valueWithoutSuffix.length > 0) {
      normalizedValue = valueWithoutSuffix;
    }

    // Remove generational suffix again (parity with Java's double application)
    normalizedValue = normalizedValue.replace(AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN, '');

    // Remove non-alphabetic characters
    normalizedValue = normalizedValue.replace(AttributeUtilities.NON_ALPHABETIC_PATTERN, '');

    return normalizedValue;
  }
}
