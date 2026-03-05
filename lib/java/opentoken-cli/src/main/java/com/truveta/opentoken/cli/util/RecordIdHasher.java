/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Utility for hashing record IDs using SHA-256.
 */
public final class RecordIdHasher {

    private static final String ALGORITHM = "SHA-256";

    private RecordIdHasher() {
    }

    /**
     * Hashes the given record ID using SHA-256 and returns a lowercase hex string.
     *
     * @param recordId the record ID to hash
     * @return the SHA-256 hex digest of the record ID
     */
    public static String hash(String recordId) {
        try {
            MessageDigest digest = MessageDigest.getInstance(ALGORITHM);
            byte[] hashBytes = digest.digest(recordId.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder(2 * hashBytes.length);
            for (byte b : hashBytes) {
                hexString.append(String.format("%02x", b));
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 algorithm not available", e);
        }
    }
}
