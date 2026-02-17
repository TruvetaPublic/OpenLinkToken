/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { SocialSecurityNumberAttribute } from '../../../src/attributes/person/SocialSecurityNumberAttribute';

describe('SocialSecurityNumberAttribute', () => {
  let ssnAttribute: SocialSecurityNumberAttribute;

  beforeEach(() => {
    ssnAttribute = new SocialSecurityNumberAttribute();
  });

  test('getName should return SocialSecurityNumber', () => {
    expect(ssnAttribute.getName()).toBe('SocialSecurityNumber');
  });

  test('getAliases should return SocialSecurityNumber and SSN', () => {
    const expectedAliases = ['SocialSecurityNumber', 'SSN'];
    const actualAliases = ssnAttribute.getAliases();
    expect(actualAliases).toEqual(expectedAliases);
  });

  test('normalize should remove dashes and keep 9 digits', () => {
    expect(ssnAttribute.normalize('123-45-6789')).toBe('123456789');
    expect(ssnAttribute.normalize('987-65-4321')).toBe('987654321');
  });

  test('normalize should handle SSN without dashes', () => {
    expect(ssnAttribute.normalize('123456789')).toBe('123456789');
  });

  test('validate should return true for valid SSN format', () => {
    expect(ssnAttribute.validate('123-45-6789')).toBe(true);
    expect(ssnAttribute.validate('987-65-4321')).toBe(true);
  });

  test('validate should return true for valid SSN without dashes', () => {
    expect(ssnAttribute.validate('123456789')).toBe(true);
  });

  test('validate should return false for invalid SSN patterns', () => {
    // All zeros
    expect(ssnAttribute.validate('000-00-0000')).toBe(false);
    // Sequential like 123-45-6789 (common test pattern)
    expect(ssnAttribute.validate('123-45-6789')).toBe(true); // This is actually valid format
    // 8 digits is valid (will be padded to 9)
    expect(ssnAttribute.validate('123-45-678')).toBe(true);
    // 7 digits is valid (will be padded to 9)
    expect(ssnAttribute.validate('123-45-67')).toBe(true);
    // Too short (less than 7 digits - only 6)
    expect(ssnAttribute.validate('123-45-6')).toBe(false);
    // Too long
    expect(ssnAttribute.validate('123-45-67890')).toBe(false);
  });

  test('validate should return false for non-numeric characters', () => {
    expect(ssnAttribute.validate('ABC-DE-FGHI')).toBe(false);
    expect(ssnAttribute.validate('123-45-ABCD')).toBe(false);
  });

  test('validate should return false for empty string', () => {
    expect(ssnAttribute.validate('')).toBe(false);
  });
});
