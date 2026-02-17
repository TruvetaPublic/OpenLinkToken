/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { DateRangeValidator } from '../../../src/attributes/validation/DateRangeValidator';

describe('DateRangeValidator', () => {
  test('should validate dates within range', () => {
    const validator = new DateRangeValidator(new Date('1910-01-01'), new Date('2030-12-31'));
    expect(validator.validate('1950-06-15')).toBe(true);
    expect(validator.validate('2000-01-01')).toBe(true);
    expect(validator.validate('2020-12-31')).toBe(true);
  });

  test('should reject dates before minimum date', () => {
    const validator = new DateRangeValidator(new Date('1910-01-01'), new Date('2030-12-31'));
    expect(validator.validate('1909-12-31')).toBe(false);
    expect(validator.validate('1800-01-01')).toBe(false);
  });

  test('should reject dates after maximum date', () => {
    const validator = new DateRangeValidator(new Date('1910-01-01'), new Date('2030-12-31'));
    expect(validator.validate('2031-01-01')).toBe(false);
    expect(validator.validate('2100-01-01')).toBe(false);
  });

  test('should accept dates on boundary dates', () => {
    const validator = new DateRangeValidator(new Date('1910-01-01'), new Date('2030-12-31'));
    expect(validator.validate('1910-01-01')).toBe(true);
    expect(validator.validate('2030-12-31')).toBe(true);
  });

  test('should handle various date formats', () => {
    const validator = new DateRangeValidator(new Date('1910-01-01'), new Date('2030-12-31'));
    // Should work with YYYY-MM-DD format
    expect(validator.validate('2000-06-15')).toBe(true);
  });

  test('should return false for invalid date format', () => {
    const validator = new DateRangeValidator(new Date('1910-01-01'), new Date('2030-12-31'));
    expect(validator.validate('not-a-date')).toBe(false);
    expect(validator.validate('13/45/2000')).toBe(false);
    expect(validator.validate('')).toBe(false);
  });
});
