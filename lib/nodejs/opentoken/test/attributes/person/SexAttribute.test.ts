/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { SexAttribute } from '../../../src/attributes/person/SexAttribute';

describe('SexAttribute', () => {
  let sexAttribute: SexAttribute;

  beforeEach(() => {
    sexAttribute = new SexAttribute();
  });

  test('getName should return Sex', () => {
    expect(sexAttribute.getName()).toBe('Sex');
  });

  test('getAliases should return Sex and Gender', () => {
    const expectedAliases = ['Sex', 'Gender'];
    const actualAliases = sexAttribute.getAliases();
    expect(actualAliases).toEqual(expectedAliases);
  });

  test('normalize should convert male variations to MALE', () => {
    expect(sexAttribute.normalize('M')).toBe('MALE');
    expect(sexAttribute.normalize('m')).toBe('MALE');
    expect(sexAttribute.normalize('Male')).toBe('MALE');
    expect(sexAttribute.normalize('MALE')).toBe('MALE');
    expect(sexAttribute.normalize('male')).toBe('MALE');
  });

  test('normalize should convert female variations to FEMALE', () => {
    expect(sexAttribute.normalize('F')).toBe('FEMALE');
    expect(sexAttribute.normalize('f')).toBe('FEMALE');
    expect(sexAttribute.normalize('Female')).toBe('FEMALE');
    expect(sexAttribute.normalize('FEMALE')).toBe('FEMALE');
    expect(sexAttribute.normalize('female')).toBe('FEMALE');
  });

  test('validate should return true for male variations', () => {
    expect(sexAttribute.validate('M')).toBe(true);
    expect(sexAttribute.validate('Male')).toBe(true);
    expect(sexAttribute.validate('MALE')).toBe(true);
  });

  test('validate should return true for female variations', () => {
    expect(sexAttribute.validate('F')).toBe(true);
    expect(sexAttribute.validate('Female')).toBe(true);
    expect(sexAttribute.validate('FEMALE')).toBe(true);
  });

  test('validate should return false for invalid values', () => {
    expect(sexAttribute.validate('X')).toBe(false);
    expect(sexAttribute.validate('Unknown')).toBe(false);
    expect(sexAttribute.validate('Other')).toBe(false);
    expect(sexAttribute.validate('')).toBe(false);
  });
});
