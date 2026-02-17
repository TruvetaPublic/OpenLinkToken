/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { BirthDateAttribute } from '../../../src/attributes/person/BirthDateAttribute';

describe('BirthDateAttribute', () => {
  let birthDateAttribute: BirthDateAttribute;

  beforeEach(() => {
    birthDateAttribute = new BirthDateAttribute();
  });

  test('getName should return BirthDate', () => {
    expect(birthDateAttribute.getName()).toBe('BirthDate');
  });

  test('getAliases should return BirthDate and DateOfBirth', () => {
    const expectedAliases = ['BirthDate', 'DateOfBirth'];
    const actualAliases = birthDateAttribute.getAliases();
    expect(actualAliases).toEqual(expectedAliases);
  });

  test('normalize should convert various date formats to YYYY-MM-DD', () => {
    expect(birthDateAttribute.normalize('01/15/1990')).toBe('1990-01-15');
    expect(birthDateAttribute.normalize('1990-01-15')).toBe('1990-01-15');
    // DateAttribute treats XX-XX-XXXX as MM-DD-YYYY format (matches Java/Python)
    expect(birthDateAttribute.normalize('01-15-1990')).toBe('1990-01-15');
  });

  test('validate should return true for dates within valid range (1910-present)', () => {
    expect(birthDateAttribute.validate('1990-01-15')).toBe(true);
    expect(birthDateAttribute.validate('1950-06-30')).toBe(true);
    expect(birthDateAttribute.validate('2000-12-31')).toBe(true);
  });

  test('validate should return false for dates before 1910', () => {
    expect(birthDateAttribute.validate('1909-12-31')).toBe(false);
    expect(birthDateAttribute.validate('1800-01-01')).toBe(false);
  });

  test('validate should return false for future dates', () => {
    const futureYear = new Date().getFullYear() + 1;
    expect(birthDateAttribute.validate(`${futureYear}-01-01`)).toBe(false);
  });

  test('validate should return false for invalid date format', () => {
    expect(birthDateAttribute.validate('not-a-date')).toBe(false);
    expect(birthDateAttribute.validate('13/45/1990')).toBe(false);
  });

  test('validate should return false for empty string', () => {
    expect(birthDateAttribute.validate('')).toBe(false);
  });
});
