/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Utility functions for attribute processing including normalizing accents,
 * standardizing formats, and other attribute-related transformations.
 */
export class AttributeUtilities {
  /** Pattern that matches any character that is not an alphabetic character (a-z or A-Z) */
  static readonly NON_ALPHABETIC_PATTERN = /[^a-zA-Z]/g;

  /** Pattern that matches one or more whitespace characters */
  static readonly WHITESPACE = /\s+/g;

  /** Pattern that matches generational suffixes at the end of a string */
  static readonly GENERATIONAL_SUFFIX_PATTERN =
    /\s+(jr\.?|junior|sr\.?|senior|I{1,3}|IV|V|VI{0,3}|IX|X|\d+(st|nd|rd|th))$/i;

  /**
   * A set of common placeholder names used to identify non-identifying or
   * placeholder text in data fields.
   */
  static readonly COMMON_PLACEHOLDER_NAMES = new Set([
    'Unknown',
    'N/A',
    'None',
    'Test',
    'Sample',
    'Donor',
    'Patient',
    'Automation Test',
    'Automationtest',
    'patient not found',
    'patientnotfound',
    '<masked>',
    'Anonymous',
    'zzztrash',
    'Missing',
    'Unavailable',
    'Not Available',
    'NotAvailable',
  ]);

  /**
   * Removes diacritic marks from the given string.
   *
   * This method performs the following steps:
   * 1. Trims the input string
   * 2. Normalizes the string using NFD form, which separates characters from their diacritical marks
   * 3. Removes all diacritical marks
   *
   * @param value - The string from which to remove diacritical marks
   * @returns A new string with all diacritical marks removed
   */
  static normalizeDiacritics(value: string): string {
    return value
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }
}
