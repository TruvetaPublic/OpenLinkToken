/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { HashTokenTransformer } from '../../src/tokentransformer/HashTokenTransformer';

describe('HashTokenTransformer', () => {
  const testSecret = 'TestHashingKey123';

  it('should hash a token using HMAC-SHA256', () => {
    const transformer = new HashTokenTransformer(testSecret);
    const token = 'test-token-value';
    const hashed = transformer.transform(token);

    // Should return a base64-encoded string
    expect(hashed).toBeDefined();
    expect(hashed.length).toBeGreaterThan(0);
    expect(hashed).toMatch(/^[A-Za-z0-9+/=]+$/);
  });

  it('should produce consistent hashes for the same input', () => {
    const transformer = new HashTokenTransformer(testSecret);
    const token = 'consistent-token';

    const hash1 = transformer.transform(token);
    const hash2 = transformer.transform(token);

    expect(hash1).toBe(hash2);
  });

  it('should produce different hashes for different inputs', () => {
    const transformer = new HashTokenTransformer(testSecret);

    const hash1 = transformer.transform('token1');
    const hash2 = transformer.transform('token2');

    expect(hash1).not.toBe(hash2);
  });

  it('should throw error for null or empty token', () => {
    const transformer = new HashTokenTransformer(testSecret);

    expect(() => transformer.transform('')).toThrow('Token cannot be null or empty');
    expect(() => transformer.transform('  ')).toThrow('Token cannot be null or empty');
  });

  it('should throw error for null or empty secret', () => {
    expect(() => new HashTokenTransformer('')).toThrow('Hashing secret cannot be null or empty');
    expect(() => new HashTokenTransformer('  ')).toThrow('Hashing secret cannot be null or empty');
  });
});
