/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.LinkedHashMap;
import java.util.Map;

public class Metadata {

    // Metadata keys
    public static final String PLATFORM = "Platform";
    public static final String JAVA_VERSION = "JavaVersion";
    public static final String OPENTOKEN_VERSION = "OpenTokenVersion";
    public static final String OUTPUT_FORMAT = "OutputFormat";
    public static final String ENCRYPTION_SECRET_HASH = "EncryptionSecretHash";
    public static final String HASHING_SECRET_HASH = "HashingSecretHash";
    public static final String BLANK_TOKENS_BY_RULE = "BlankTokensByRule";

    // Metadata values
    public static final String PLATFORM_JAVA = "Java";
    public static final String METADATA_FILE_EXTENSION = ".metadata.json";
    public static final String SYSTEM_JAVA_VERSION = System.getProperty("java.version");

    public static final String DEFAULT_VERSION = "2.0.0-alpha";

    // Output format values
    public static final String OUTPUT_FORMAT_JSON = "JSON";
    public static final String OUTPUT_FORMAT_CSV = "CSV";
    public static final String OUTPUT_FORMAT_PARQUET = "Parquet";

    private Map<String, Object> metadataMap;

    public Metadata() {
        metadataMap = new LinkedHashMap<>();
    }

    /**
     * Initializes metadata with system information only.
     * Secret hashes must be set separately using setHashingSecret() and setEncryptionKey().
     *
     * @return the initialized metadata map
     */
    public Map<String, Object> initialize() {
        metadataMap.clear();
        metadataMap.put(JAVA_VERSION, SYSTEM_JAVA_VERSION);
        metadataMap.put(PLATFORM, PLATFORM_JAVA);
        metadataMap.put(OPENTOKEN_VERSION, DEFAULT_VERSION);

        return metadataMap;
    }

    /**
     * Sets the hashing secret and adds its hash to the metadata.
     * 
     * @param secretToHash the secret to hash
     * @return the metadata map for method chaining
     */
    public Map<String, Object> addHashedSecret(String secretKey, String secretToHash) {
        if (secretToHash != null && !secretToHash.isEmpty()) {
            metadataMap.put(secretKey, calculateSecureHash(secretToHash));
        }
        return metadataMap;
    }

    /**
     * Calculates a secure SHA-256 hash of the given input.
     * The hash is returned as a hexadecimal string.
     *
     * @param input the input string to hash
     * @return the SHA-256 hash as a hexadecimal string
     * @throws HashCalculationException if SHA-256 algorithm is not available
     */
    public static String calculateSecureHash(String input) {
        if (input == null || input.isEmpty()) {
            return null;
        }

        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(input.getBytes(StandardCharsets.UTF_8));

            // Convert bytes to hexadecimal string
            StringBuilder hexString = new StringBuilder();
            for (byte b : hashBytes) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();

        } catch (NoSuchAlgorithmException e) {
            throw new HashCalculationException("SHA-256 algorithm not available", e);
        }
    }

    /**
     * Custom exception for hash calculation errors.
     */
    public static class HashCalculationException extends RuntimeException {
        public HashCalculationException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
