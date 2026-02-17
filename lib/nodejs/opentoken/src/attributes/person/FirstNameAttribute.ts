/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BaseAttribute } from '../BaseAttribute';
import { NotInValidator } from '../validation/NotInValidator';
import { AttributeUtilities } from '../utilities/AttributeUtilities';

/**
 * Represents the first name of a person.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * first name fields. It recognizes "FirstName" and "GivenName" as valid aliases
 * for this attribute type.
 */
export class FirstNameAttribute extends BaseAttribute {
  private static readonly NAME = 'FirstName';
  private static readonly ALIASES = ['FirstName', 'GivenName'];

  /** Pattern to match and remove common titles and title abbreviations from first names */
  private static readonly TITLE_PATTERN =
    /^(mr|mrs|ms|miss|dr|prof|capt|sir|col|gen|cmdr|lt|rabbi|father|brother|sister|hon|honorable|reverend|rev|doctor)\.?\s+/i;

  /** Pattern to match trailing periods and middle initials in names */
  private static readonly TRAILING_PERIOD_AND_INITIAL_PATTERN = /\s[^\s]\.?$/;

  constructor() {
    super(FirstNameAttribute.NAME, FirstNameAttribute.ALIASES, [
      new NotInValidator(AttributeUtilities.COMMON_PLACEHOLDER_NAMES),
    ]);
  }

  normalize(value: string): string {
    // Replicate Java normalization ordering and conditional retention
    let normalizedValue = AttributeUtilities.normalizeDiacritics(value);

    const valueWithoutTitle = normalizedValue.replace(FirstNameAttribute.TITLE_PATTERN, '');
    if (valueWithoutTitle.length > 0) {
      normalizedValue = valueWithoutTitle;
    }

    const valueWithoutSuffix = normalizedValue.replace(AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN, '');
    if (valueWithoutSuffix.length > 0) {
      normalizedValue = valueWithoutSuffix;
    }

    normalizedValue = normalizedValue.replace(FirstNameAttribute.TRAILING_PERIOD_AND_INITIAL_PATTERN, '');
    normalizedValue = normalizedValue.replace(AttributeUtilities.NON_ALPHABETIC_PATTERN, '');
    return normalizedValue;
  }
}
