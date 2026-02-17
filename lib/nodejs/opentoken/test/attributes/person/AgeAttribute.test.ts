/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AgeAttribute } from '../../../src/attributes/person/AgeAttribute';

describe('AgeAttribute', () => {
  let ageAttribute: AgeAttribute;

  beforeEach(() => {
    ageAttribute = new AgeAttribute();
  });

  test('getName should return Age', () => {
    expect(ageAttribute.getName()).toBe('Age');
  });

  test('normalize should return age as string', () => {
    expect(ageAttribute.normalize('25')).toBe('25');
    expect(ageAttribute.normalize('100')).toBe('100');
  });

  test('validate should return true for ages 0-120', () => {
    expect(ageAttribute.validate('0')).toBe(true);
    expect(ageAttribute.validate('25')).toBe(true);
    expect(ageAttribute.validate('100')).toBe(true);
    expect(ageAttribute.validate('120')).toBe(true);
  });

  test('validate should return false for negative ages', () => {
    expect(ageAttribute.validate('-1')).toBe(false);
    expect(ageAttribute.validate('-10')).toBe(false);
  });

  test('validate should return false for ages over 120', () => {
    expect(ageAttribute.validate('121')).toBe(false);
    expect(ageAttribute.validate('150')).toBe(false);
  });

  test('validate should return false for non-numeric values', () => {
    expect(ageAttribute.validate('abc')).toBe(false);
    expect(ageAttribute.validate('')).toBe(false);
  });
});
