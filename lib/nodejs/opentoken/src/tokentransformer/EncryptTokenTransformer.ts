/**
 * Copyright (c) Truveta. All rights reserved.
 */

import * as crypto from 'crypto';
import { TokenTransformer } from './TokenTransformer';

/**
 * Transforms the token using AES-256 symmetric encryption.
 *
 * Uses AES-256-GCM encryption algorithm.
 */
export class EncryptTokenTransformer implements TokenTransformer {
  private static readonly ENCRYPTION_ALGORITHM = 'aes-256-gcm';
  private static readonly KEY_BYTE_LENGTH = 32;
  private static readonly IV_SIZE = 12;
  // TAG_LENGTH is implicit in GCM mode (16 bytes)

  private secretKey: Buffer;

  /**
   * Initializes the underlying cipher (AES) with the encryption secret.
   *
   * @param encryptionKey - The encryption key. The key must be 32 characters long.
   */
  constructor(encryptionKey: string) {
    if (encryptionKey.length !== EncryptTokenTransformer.KEY_BYTE_LENGTH) {
      throw new Error(`Key must be ${EncryptTokenTransformer.KEY_BYTE_LENGTH} characters long`);
    }

    this.secretKey = Buffer.from(encryptionKey, 'utf8');
  }

  /**
   * Encryption token transformer.
   *
   * Encrypts the token using AES-256-GCM symmetric encryption algorithm.
   *
   * @param token - The token to encrypt.
   * @returns Encrypted token in base64 format.
   */
  transform(token: string): string {
    if (!token || token.trim().length === 0) {
      throw new Error('Token cannot be null or empty');
    }

    // Generate random IV (Initialization Vector)
    const iv = crypto.randomBytes(EncryptTokenTransformer.IV_SIZE);

    // Create cipher
    const cipher = crypto.createCipheriv(
      EncryptTokenTransformer.ENCRYPTION_ALGORITHM,
      this.secretKey,
      iv
    );

    // Encrypt the token
    let encrypted = cipher.update(token, 'utf8');
    encrypted = Buffer.concat([encrypted, cipher.final()]);

    // Get the authentication tag
    const authTag = cipher.getAuthTag();

    // Combine IV + encrypted data + auth tag
    const result = Buffer.concat([iv, encrypted, authTag]);

    // Return as base64
    return result.toString('base64');
  }
}
