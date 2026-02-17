/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { LastNameAttribute } from '../../../src/attributes/person/LastNameAttribute';

describe('LastNameAttribute', () => {
  let lastNameAttribute: LastNameAttribute;

  beforeEach(() => {
    lastNameAttribute = new LastNameAttribute();
  });

  test('getName should return LastName', () => {
    expect(lastNameAttribute.getName()).toBe('LastName');
  });

  test('getAliases should return LastName and FamilyName', () => {
    const expectedAliases = ['LastName', 'FamilyName'];
    const actualAliases = lastNameAttribute.getAliases();
    expect(actualAliases).toEqual(expectedAliases);
  });

  test('normalize should return unchanged value for basic names', () => {
    const input = 'Smith';
    expect(lastNameAttribute.normalize(input)).toBe(input);
  });

  test('normalize should remove accents', () => {
    expect(lastNameAttribute.normalize('García')).toBe('Garcia');
    expect(lastNameAttribute.normalize('Müller')).toBe('Muller');
    expect(lastNameAttribute.normalize('Nguyễn')).toBe('Nguyen');
  });

  test('normalize should remove suffixes', () => {
    expect(lastNameAttribute.normalize('Smith Jr')).toBe('Smith');
    expect(lastNameAttribute.normalize('Johnson III')).toBe('Johnson');
    expect(lastNameAttribute.normalize('Brown Sr.')).toBe('Brown');
  });

  test('normalize should preserve case', () => {
    expect(lastNameAttribute.normalize('smith')).toBe('smith');
    expect(lastNameAttribute.normalize('Johnson')).toBe('Johnson');
  });

  test('validate should return true for names with 2+ characters', () => {
    expect(lastNameAttribute.validate('Smith')).toBe(true);
    expect(lastNameAttribute.validate('Li')).toBe(true);
    expect(lastNameAttribute.validate('Van Der Berg')).toBe(true);
  });

  test('validate should return false for single character names', () => {
    expect(lastNameAttribute.validate('X')).toBe(false);
  });

  test('validate should return false for empty string', () => {
    expect(lastNameAttribute.validate('')).toBe(false);
  });

  test('validate should return false for null or undefined', () => {
    expect(lastNameAttribute.validate(null as any)).toBe(false);
    expect(lastNameAttribute.validate(undefined as any)).toBe(false);
  });
});
