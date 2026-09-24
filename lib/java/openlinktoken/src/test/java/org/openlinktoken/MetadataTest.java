/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.security.MessageDigest;
import java.util.Map;

import org.junit.jupiter.api.Test;

/** Tests metadata initialization and secret-hash behavior. */
class MetadataTest {

    private static final String PRIMARY_SECRET_DIGEST = "PrimarySecretDigest";
    private static final String SECONDARY_SECRET_DIGEST = "SecondarySecretDigest";

    /** Verifies initialization adds only the standard platform and version metadata. */
    @Test
    void testInitializeOnly() {
        Metadata metadata = new Metadata();
        Map<String, Object> result = metadata.initialize();

        assertTrue(result.containsKey(Metadata.JAVA_VERSION));
        assertTrue(result.containsKey(Metadata.PLATFORM));
        assertTrue(result.containsKey(Metadata.VERSION));
        assertEquals(3, result.size());

        assertEquals(Metadata.PLATFORM_JAVA, result.get(Metadata.PLATFORM));
        assertEquals(Metadata.DEFAULT_VERSION, result.get(Metadata.VERSION));
    }

    /** Verifies a custom secret is stored under its requested digest key. */
    @Test
    void testAddHashedSecretWithCustomKey() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        String customSecret = "test-hashing-secret";
        Map<String, Object> result = metadata.addHashedSecret(PRIMARY_SECRET_DIGEST, customSecret);

        assertTrue(result.containsKey(PRIMARY_SECRET_DIGEST));
        assertNotNull(result.get(PRIMARY_SECRET_DIGEST));
    }

    /** Verifies adding a second custom secret does not create the primary digest entry. */
    @Test
    void testAddHashedSecretWithSecondCustomKey() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        String customSecret = "test-encryption-key";
        Map<String, Object> result = metadata.addHashedSecret(SECONDARY_SECRET_DIGEST, customSecret);

        assertFalse(result.containsKey(PRIMARY_SECRET_DIGEST));
        assertTrue(result.containsKey(SECONDARY_SECRET_DIGEST));
        assertNotNull(result.get(SECONDARY_SECRET_DIGEST));
    }

    /** Verifies two custom secrets are stored as distinct digest entries. */
    @Test
    void testAddHashedSecretWithBothCustomKeys() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        metadata.addHashedSecret(PRIMARY_SECRET_DIGEST, "test-hashing-secret");
        Map<String, Object> result = metadata.addHashedSecret(SECONDARY_SECRET_DIGEST, "test-encryption-key");

        assertTrue(result.containsKey(PRIMARY_SECRET_DIGEST));
        assertTrue(result.containsKey(SECONDARY_SECRET_DIGEST));
        assertNotNull(result.get(PRIMARY_SECRET_DIGEST));
        assertNotNull(result.get(SECONDARY_SECRET_DIGEST));
        assertNotEquals(result.get(PRIMARY_SECRET_DIGEST), result.get(SECONDARY_SECRET_DIGEST));
    }

    /** Verifies null secrets are omitted from metadata. */
    @Test
    void testAddHashedSecretWithNullSecrets() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        metadata.addHashedSecret(PRIMARY_SECRET_DIGEST, (String) null);
        Map<String, Object> result = metadata.addHashedSecret(SECONDARY_SECRET_DIGEST, (String) null);

        assertFalse(result.containsKey(PRIMARY_SECRET_DIGEST));
        assertFalse(result.containsKey(SECONDARY_SECRET_DIGEST));
    }

    /** Verifies empty secrets are omitted from metadata. */
    @Test
    void testAddHashedSecretWithEmptySecrets() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        metadata.addHashedSecret(PRIMARY_SECRET_DIGEST, "");
        Map<String, Object> result = metadata.addHashedSecret(SECONDARY_SECRET_DIGEST, "");

        assertFalse(result.containsKey(PRIMARY_SECRET_DIGEST));
        assertFalse(result.containsKey(SECONDARY_SECRET_DIGEST));
    }

    /** Verifies secure hashing returns a repeatable 64-character digest for nonempty input. */
    @Test
    void testCalculateSecureHashWithValidInput() {
        String input = "test-input";
        String hash = Metadata.calculateSecureHash(input);

        assertNotNull(hash);
        assertFalse(hash.isEmpty());
        assertEquals(64, hash.length());

        String hash2 = Metadata.calculateSecureHash(input);
        assertEquals(hash, hash2);
    }

    /** Verifies secure hashing matches the known SHA-256 digest for {@code hello}. */
    @Test
    void testCalculateSecureHashWithKnownValue() {
        String input = "hello";
        String expectedHash = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824";

        String actualHash = Metadata.calculateSecureHash(input);
        assertEquals(expectedHash, actualHash);
    }

    /** Verifies different input strings produce different secure hashes. */
    @Test
    void testCalculateSecureHashWithDifferentInputs() {
        String input1 = "input1";
        String input2 = "input2";

        String hash1 = Metadata.calculateSecureHash(input1);
        String hash2 = Metadata.calculateSecureHash(input2);

        assertNotEquals(hash1, hash2);
    }

    /** Verifies null input has no secure hash. */
    @Test
    void testCalculateSecureHashWithNullInput() {
        String hash = Metadata.calculateSecureHash((String) null);
        assertNull(hash);
    }

    /** Verifies empty input has no secure hash. */
    @Test
    void testCalculateSecureHashWithEmptyInput() {
        String hash = Metadata.calculateSecureHash("");
        assertNull(hash);
    }

    /** Verifies Unicode input produces a repeatable secure hash. */
    @Test
    void testCalculateSecureHashWithUnicodeInput() {
        String input = "こんにちは";
        String hash = Metadata.calculateSecureHash(input);

        assertNotNull(hash);
        assertEquals(64, hash.length());

        String hash2 = Metadata.calculateSecureHash(input);
        assertEquals(hash, hash2);
    }

    /** Verifies a raw secret byte array is stored using its byte-based digest. */
    @Test
    void testAddHashedSecretWithByteArray() {
        Metadata metadata = new Metadata();
        metadata.initialize();

        byte[] rawSecret = new byte[] { (byte) 0xff, 0x00, 0x01, 0x02 };
        Map<String, Object> result = metadata.addHashedSecret(PRIMARY_SECRET_DIGEST, rawSecret);

        assertTrue(result.containsKey(PRIMARY_SECRET_DIGEST));
        assertEquals(Metadata.calculateSecureHash(rawSecret), result.get(PRIMARY_SECRET_DIGEST));
    }

    /** Verifies raw-byte hashing matches an independently calculated SHA-256 digest. */
    @Test
    void testCalculateSecureHashWithRawBytes() throws Exception {
        byte[] input = new byte[] { (byte) 0xff, 0x00, 'h', 'i' };

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

    /** Verifies legacy secret-hash constants are absent from {@link Metadata}. */
    @Test
    void testMetadataNoLongerDefinesSecretHashConstants() {
        assertThrows(NoSuchFieldException.class, () -> Metadata.class.getDeclaredField("HASHING_SECRET_HASH"));
        assertThrows(NoSuchFieldException.class, () -> Metadata.class.getDeclaredField("ENCRYPTION_SECRET_HASH"));
    }

    /** Verifies the hash-calculation exception retains its message and cause. */
    @Test
    void testHashCalculationExceptionCreation() {
        String message = "Test message";
        Exception cause = new RuntimeException("Test cause");

        Metadata.HashCalculationException exception = new Metadata.HashCalculationException(message, cause);

        assertEquals(message, exception.getMessage());
        assertEquals(cause, exception.getCause());
    }
}
