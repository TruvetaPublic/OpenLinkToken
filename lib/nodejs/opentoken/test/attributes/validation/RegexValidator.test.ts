/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { RegexValidator } from '../../../src/attributes/validation/RegexValidator';

describe('RegexValidator', () => {
  test('should validate strings matching regex pattern', () => {
    const validator = new RegexValidator(/^\d{3}-\d{2}-\d{4}$/);
    expect(validator.validate('123-45-6789')).toBe(true);
    expect(validator.validate('987-65-4321')).toBe(true);
  });

  test('should reject strings not matching regex pattern', () => {
    const validator = new RegexValidator(/^\d{3}-\d{2}-\d{4}$/);
    expect(validator.validate('12-345-6789')).toBe(false);
    expect(validator.validate('abc-de-fghi')).toBe(false);
    expect(validator.validate('123456789')).toBe(false);
  });

  test('should work with email pattern', () => {
    const validator = new RegexValidator(/^[^\s@]+@[^\s@]+\.[^\s@]+$/);
    expect(validator.validate('test@example.com')).toBe(true);
    expect(validator.validate('invalid.email')).toBe(false);
    expect(validator.validate('@example.com')).toBe(false);
  });

  test('should validate alphanumeric pattern', () => {
    const validator = new RegexValidator(/^[A-Za-z0-9]+$/);
    expect(validator.validate('ABC123')).toBe(true);
    expect(validator.validate('Test123')).toBe(true);
    expect(validator.validate('Test 123')).toBe(false);
    expect(validator.validate('Test-123')).toBe(false);
  });

  test('should return false for empty string when pattern requires content', () => {
    const validator = new RegexValidator(/^\d+$/);
    expect(validator.validate('')).toBe(false);
  });
});
