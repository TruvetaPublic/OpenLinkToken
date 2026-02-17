/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { FirstNameAttribute } from '../../../src/attributes/person/FirstNameAttribute';

describe('FirstNameAttribute', () => {
  let firstNameAttribute: FirstNameAttribute;

  beforeEach(() => {
    firstNameAttribute = new FirstNameAttribute();
  });

  test('getName should return FirstName', () => {
    expect(firstNameAttribute.getName()).toBe('FirstName');
  });

  test('getAliases should return FirstName and GivenName', () => {
    const expectedAliases = ['FirstName', 'GivenName'];
    const actualAliases = firstNameAttribute.getAliases();
    expect(actualAliases).toEqual(expectedAliases);
  });

  test('normalize should return unchanged value for basic names', () => {
    const input = 'John';
    expect(firstNameAttribute.normalize(input)).toBe(input);
  });

  test('normalize should remove accents', () => {
    expect(firstNameAttribute.normalize('José')).toBe('Jose');
    expect(firstNameAttribute.normalize('Vũ')).toBe('Vu');
    expect(firstNameAttribute.normalize('François')).toBe('Francois');
    expect(firstNameAttribute.normalize('Renée')).toBe('Renee');
  });

  test('normalize should remove titles', () => {
    expect(firstNameAttribute.normalize('Dr. John')).toBe('John');
    expect(firstNameAttribute.normalize('Mr. Smith')).toBe('Smith');
    expect(firstNameAttribute.normalize('Mrs. Jane')).toBe('Jane');
  });

  test('normalize should handle middle initials', () => {
    expect(firstNameAttribute.normalize('John M')).toBe('John');
    expect(firstNameAttribute.normalize('Mary A.')).toBe('Mary');
  });

  test('normalize should remove suffixes', () => {
    expect(firstNameAttribute.normalize('John Jr')).toBe('John');
    expect(firstNameAttribute.normalize('William III')).toBe('William');
  });

  test('normalize should preserve case', () => {
    expect(firstNameAttribute.normalize('john')).toBe('john');
    expect(firstNameAttribute.normalize('Mary')).toBe('Mary');
  });

  test('validate should return true for any non-empty string', () => {
    expect(firstNameAttribute.validate('John')).toBe(true);
    expect(firstNameAttribute.validate('Jane Doe')).toBe(true);
    expect(firstNameAttribute.validate('X')).toBe(true);
  });

  test('validate should return false for empty string', () => {
    expect(firstNameAttribute.validate('')).toBe(false);
  });

  test('validate should return false for null or undefined', () => {
    expect(firstNameAttribute.validate(null as any)).toBe(false);
    expect(firstNameAttribute.validate(undefined as any)).toBe(false);
  });
});
