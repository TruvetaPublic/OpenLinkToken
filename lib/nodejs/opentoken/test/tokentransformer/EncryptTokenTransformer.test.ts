/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { EncryptTokenTransformer } from '../../src/tokentransformer/EncryptTokenTransformer';

describe('EncryptTokenTransformer', () => {
  const testKey = 'Secret-Encryption-Key-Goes-Here.'; // 32 characters

  it('should encrypt a token using AES-256-GCM', () => {
    const transformer = new EncryptTokenTransformer(testKey);
    const token = 'test-token-value';
    const encrypted = transformer.transform(token);

    // Should return a base64-encoded string
    expect(encrypted).toBeDefined();
    expect(encrypted.length).toBeGreaterThan(0);
    expect(encrypted).toMatch(/^[A-Za-z0-9+/=]+$/);
  });

  it('should produce different encrypted values each time (due to random IV)', () => {
    const transformer = new EncryptTokenTransformer(testKey);
    const token = 'same-token';

    const encrypted1 = transformer.transform(token);
    const encrypted2 = transformer.transform(token);

    // Different because of random IV each time
    expect(encrypted1).not.toBe(encrypted2);
  });

  it('should encrypt different tokens to different values', () => {
    const transformer = new EncryptTokenTransformer(testKey);

    const encrypted1 = transformer.transform('token1');
    const encrypted2 = transformer.transform('token2');

    expect(encrypted1).not.toBe(encrypted2);
  });

  it('should throw error for null or empty token', () => {
    const transformer = new EncryptTokenTransformer(testKey);

    expect(() => transformer.transform('')).toThrow('Token cannot be null or empty');
    expect(() => transformer.transform('  ')).toThrow('Token cannot be null or empty');
  });

  it('should throw error for invalid key length', () => {
    expect(() => new EncryptTokenTransformer('short')).toThrow('Key must be 32 characters long');
    expect(() => new EncryptTokenTransformer('way-too-long-key-that-exceeds-32-chars')).toThrow(
      'Key must be 32 characters long'
    );
  });

  it('should accept 32-character key', () => {
    expect(() => new EncryptTokenTransformer(testKey)).not.toThrow();
  });
});
