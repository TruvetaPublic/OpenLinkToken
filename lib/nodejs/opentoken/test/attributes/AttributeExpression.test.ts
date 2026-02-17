/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../../src/attributes/AttributeExpression';
import { FirstNameAttribute } from '../../src/attributes/person/FirstNameAttribute';
import { LastNameAttribute } from '../../src/attributes/person/LastNameAttribute';
import { BirthDateAttribute } from '../../src/attributes/person/BirthDateAttribute';

describe('AttributeExpression', () => {
  test('should apply trim operation (T)', () => {
    const expression = new AttributeExpression(FirstNameAttribute, 'T');
    const result = expression.getEffectiveValue('  JONATHAN  ');
    expect(result).toBe('JONATHAN');
  });

  test('should apply uppercase operation (U)', () => {
    const expression = new AttributeExpression(FirstNameAttribute, 'U');
    const result = expression.getEffectiveValue('john');
    expect(result).toBe('JOHN');
  });

  test('should handle date expressions', () => {
    const expression = new AttributeExpression(BirthDateAttribute, 'D');
    const result = expression.getEffectiveValue('1990-01-15');
    expect(result).toBe('1990-01-15');
  });

  test('should apply substring operation (S)', () => {
    const expression = new AttributeExpression(LastNameAttribute, 'S(0,3)');
    const result = expression.getEffectiveValue('SMITH');
    expect(result).toBe('SMI');
  });

  test('should apply combined operations with pipe', () => {
    // U|S(0,3) - uppercase then substring (truncate to 3 chars)
    const expression = new AttributeExpression(FirstNameAttribute, 'U|S(0,3)');
    const result = expression.getEffectiveValue('jonathan');
    expect(result).toBe('JON');
  });

  test('should return empty string for null or undefined input', () => {
    const expression = new AttributeExpression(FirstNameAttribute, 'U');
    expect(expression.getEffectiveValue(null as any)).toBe('');
    expect(expression.getEffectiveValue(undefined as any)).toBe('');
    expect(expression.getEffectiveValue('')).toBe('');
  });

  test('should handle substring beyond string length', () => {
    const expression = new AttributeExpression(FirstNameAttribute, 'S(0,10)');
    const result = expression.getEffectiveValue('JON');
    expect(result).toBe('JON');
  });

  test('should handle expressions with no operations', () => {
    const expression = new AttributeExpression(FirstNameAttribute, '');
    const result = expression.getEffectiveValue('JOHN');
    expect(result).toBe('JOHN');
  });
});
