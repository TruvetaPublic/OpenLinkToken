/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokentransformer;

/**
 * Shared constants for AES-256 GCM encryption and decryption.
 */
public final class EncryptionConstants {

    private EncryptionConstants() {
        // Utility class, prevent instantiation
    }

    /** AES algorithm name. */
    public static final String AES = "AES";

    /** AES-256 GCM encryption algorithm specification. */
    public static final String ENCRYPTION_ALGORITHM = "AES/GCM/NoPadding";

    /** AES-256 key length in bytes. */
    public static final int KEY_BYTE_LENGTH = 32;

    /** GCM initialization vector size in bytes. */
    public static final int IV_SIZE = 12;

    /** GCM authentication tag length in bits. */
    public static final int TAG_LENGTH_BITS = 128;
}
