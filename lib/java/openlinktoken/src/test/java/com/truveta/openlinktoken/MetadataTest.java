/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.security.MessageDigest;
import java.util.Map;

import org.junit.jupiter.api.Test;

class MetadataTest {

    @Test
    void testInitializeOnly() {
        Metadata metadata = new Metadata();
        Map<String, Object> result = metadata.initialize();

        assertTrue(result.containsKey(Metadata.JAVA_VERSION));
        assertTrue(result.containsKey(Metadata.PLATFORM));
        assertTrue(result.containsKey(Metadata.OPENTOKEN_VERSION));

        assertFalse(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertFalse(result.containsKey(Metadata.ENCRYPTION_SECRET_HASH));

        assertEquals(Metadata.PLATFORM_JAVA, result.get(Metadata.PLATFORM));
        assertEquals(Metadata.DEFAULT_VERSION, result.get(Metadata.OPENTOKEN_VERSION));
    }

    @Test
    void testAddHashedSecretWithHashingSecret() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        String hashingSecret = "test-hashing-secret";
        Map<String, Object> result = metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, hashingSecret);

        assertTrue(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertFalse(result.containsKey(Metadata.ENCRYPTION_SECRET_HASH));
        assertNotNull(result.get(Metadata.HASHING_SECRET_HASH));
    }

    @Test
    void testAddHashedSecretWithEncryptionKey() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        String encryptionKey = "test-encryption-key";
        Map<String, Object> result = metadata.addHashedSecret(Metadata.ENCRYPTION_SECRET_HASH, encryptionKey);

        assertFalse(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertTrue(result.containsKey(Metadata.ENCRYPTION_SECRET_HASH));
        assertNotNull(result.get(Metadata.ENCRYPTION_SECRET_HASH));
    }

    @Test
    void testAddHashedSecretWithBothSecrets() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        String hashingSecret = "test-hashing-secret";
        String encryptionKey = "test-encryption-key";

        metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, hashingSecret);
        Map<String, Object> result = metadata.addHashedSecret(Metadata.ENCRYPTION_SECRET_HASH, encryptionKey);

        assertTrue(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertTrue(result.containsKey(Metadata.ENCRYPTION_SECRET_HASH));
        assertNotNull(result.get(Metadata.HASHING_SECRET_HASH));
        assertNotNull(result.get(Metadata.ENCRYPTION_SECRET_HASH));

        // Verify hashes are different for different inputs
        assertNotEquals(result.get(Metadata.HASHING_SECRET_HASH),
                result.get(Metadata.ENCRYPTION_SECRET_HASH));
    }

    @Test
    void testAddHashedSecretWithNullSecrets() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, (String) null);
        Map<String, Object> result = metadata.addHashedSecret(Metadata.ENCRYPTION_SECRET_HASH, (String) null);

        assertFalse(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertFalse(result.containsKey(Metadata.ENCRYPTION_SECRET_HASH));
    }

    @Test
    void testAddHashedSecretWithEmptySecrets() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, "");
        Map<String, Object> result = metadata.addHashedSecret(Metadata.ENCRYPTION_SECRET_HASH, "");

        assertFalse(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertFalse(result.containsKey(Metadata.ENCRYPTION_SECRET_HASH));
    }

    @Test
    void testAddHashedSecretWithCustomKey() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        String customKey = "CustomSecretHash";
        String customSecret = "my-custom-secret";
        Map<String, Object> result = metadata.addHashedSecret(customKey, customSecret);

        assertTrue(result.containsKey(customKey));
        assertNotNull(result.get(customKey));
        assertEquals(Metadata.calculateSecureHash(customSecret), result.get(customKey));
    }

    @Test
    void testCalculateSecureHashWithValidInput() {
        String input = "test-input";
        String hash = Metadata.calculateSecureHash(input);

        assertNotNull(hash);
        assertFalse(hash.isEmpty());
        assertEquals(64, hash.length()); // SHA-256 produces 64 character hex string

        // Verify the hash is consistent
        String hash2 = Metadata.calculateSecureHash(input);
        assertEquals(hash, hash2);
    }

    @Test
    void testCalculateSecureHashWithKnownValue() {
        // Test with a known SHA-256 value to ensure compatibility
        String input = "hello";
        String expectedHash = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824";

        String actualHash = Metadata.calculateSecureHash(input);
        assertEquals(expectedHash, actualHash);
    }

    @Test
    void testCalculateSecureHashWithDifferentInputs() {
        String input1 = "input1";
        String input2 = "input2";

        String hash1 = Metadata.calculateSecureHash(input1);
        String hash2 = Metadata.calculateSecureHash(input2);

        assertNotEquals(hash1, hash2);
    }

    @Test
    void testCalculateSecureHashWithNullInput() {
        String hash = Metadata.calculateSecureHash((String) null);
        assertNull(hash);
    }

    @Test
    void testCalculateSecureHashWithEmptyInput() {
        String hash = Metadata.calculateSecureHash("");
        assertNull(hash);
    }

    @Test
    void testCalculateSecureHashWithUnicodeInput() {
        String input = "こんにちは"; // Japanese "hello"
        String hash = Metadata.calculateSecureHash(input);

        assertNotNull(hash);
        assertEquals(64, hash.length());

        // Verify UTF-8 encoding produces consistent results
        String hash2 = Metadata.calculateSecureHash(input);
        assertEquals(hash, hash2);
    }

    @Test
    void testAddHashedSecretWithByteArray() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        byte[] rawSecret = new byte[] {(byte) 0xff, 0x00, 0x01, 0x02};
        Map<String, Object> result = metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, rawSecret);

        assertTrue(result.containsKey(Metadata.HASHING_SECRET_HASH));
        assertEquals(Metadata.calculateSecureHash(rawSecret), result.get(Metadata.HASHING_SECRET_HASH));
    }

    @Test
    void testCalculateSecureHashWithRawBytes() throws Exception {
        byte[] input = new byte[] {(byte) 0xff, 0x00, 'h', 'i'};

        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] expectedHashBytes = digest.digest(input);
        StringBuilder expectedHash = new StringBuilder();
        for (byte b : expectedHashBytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                expectedHash.append('0');
            }
            expectedHash.append(hex);
        }

        assertEquals(expectedHash.toString(), Metadata.calculateSecureHash(input));
    }

    @Test
    void testMetadataConstants() {
        // Verify that the new constants are properly defined
        assertNotNull(Metadata.ENCRYPTION_SECRET_HASH);
        assertNotNull(Metadata.HASHING_SECRET_HASH);

        assertEquals("EncryptionSecretHash", Metadata.ENCRYPTION_SECRET_HASH);
        assertEquals("HashingSecretHash", Metadata.HASHING_SECRET_HASH);
    }

    @Test
    void testHashCalculationExceptionCreation() {
        String message = "Test message";
        Exception cause = new RuntimeException("Test cause");

        Metadata.HashCalculationException exception = new Metadata.HashCalculationException(message, cause);

        assertEquals(message, exception.getMessage());
        assertEquals(cause, exception.getCause());
    }
}
