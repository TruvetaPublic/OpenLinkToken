/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.apache.commons.lang3.SerializationUtils;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Tests keyed SHA-256 hashing, raw secrets, and serialized transformer behavior. */
class HashTokenTransformerTest {
    private static final String VALID_SECRET = "sampleSecret";
    private static final String VALID_TOKEN = "sampleToken";

    private HashTokenTransformer transformer;

    /** Creates a hash transformer with the valid test secret. */
    @BeforeEach
    void setup() throws NoSuchAlgorithmException, InvalidKeyException {
        transformer = new HashTokenTransformer(VALID_SECRET);
    }

    /** Verifies a serialized transformer produces the expected Base64 HMAC-SHA-256 digest. */
    @Test
    void testSerializable() throws Exception {
        TokenTransformer encryptTokenTransformer = new HashTokenTransformer(VALID_SECRET);
        byte[] serialized = SerializationUtils.serialize(encryptTokenTransformer);
        TokenTransformer deserialized = SerializationUtils.deserialize(serialized);
        String hashedToken = deserialized.transform(VALID_TOKEN);

        assertNotNull(hashedToken);

        // Manually calculate the expected hash for validation
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new javax.crypto.spec.SecretKeySpec(VALID_SECRET.getBytes(), "HmacSHA256"));
        byte[] expectedHash = mac.doFinal(VALID_TOKEN.getBytes());
        String expectedHashedToken = Base64.getEncoder().encodeToString(expectedHash);

        assertEquals(expectedHashedToken, hashedToken);
    }

    /** Verifies hashing a valid token matches an independently calculated HMAC-SHA-256 digest. */
    @Test
    void testTransform_ValidToken_ReturnsHashedToken() throws Exception {
        String hashedToken = transformer.transform(VALID_TOKEN);
        assertNotNull(hashedToken);

        // Manually calculate the expected hash for validation
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new javax.crypto.spec.SecretKeySpec(VALID_SECRET.getBytes(), "HmacSHA256"));
        byte[] expectedHash = mac.doFinal(VALID_TOKEN.getBytes());
        String expectedHashedToken = Base64.getEncoder().encodeToString(expectedHash);

        assertEquals(expectedHashedToken, hashedToken);
    }

    /** Verifies null token input is rejected with an argument error. */
    @Test
    void testTransform_NullToken_ThrowsIllegalArgumentException() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            transformer.transform(null);
        });
        assertEquals("Invalid Argument. Token can't be Null.", exception.getMessage());
    }

    /** Verifies a transformer created without a secret cannot hash a token. */
    @Test
    void testConstructor_NullSecret_InitializesWithNullMac() throws Exception {
        HashTokenTransformer nullSecretTransformer = new HashTokenTransformer((String) null);
        assertThrows(NullPointerException.class, () -> {
            nullSecretTransformer.transform(VALID_TOKEN);
        });
    }

    /** Verifies a transformer created with a blank secret cannot hash a token. */
    @Test
    void testConstructor_BlankSecret_InitializesWithNullMac() throws Exception {
        HashTokenTransformer blankSecretTransformer = new HashTokenTransformer("");
        assertThrows(NullPointerException.class, () -> {
            blankSecretTransformer.transform(VALID_TOKEN);
        });
    }

    /** Verifies repeated hashing of the same token produces a consistent digest. */
    @Test
    void testTransform_ValidTokenMultipleTimes_ReturnsConsistentHash() throws Exception {
        String hash1 = transformer.transform(VALID_TOKEN);
        String hash2 = transformer.transform(VALID_TOKEN);
        assertEquals(hash1, hash2); // The hashed value should be consistent
    }

    /** Verifies a raw-byte secret produces the expected HMAC-SHA-256 digest. */
    @Test
    void testTransform_RawByteSecret_ReturnsExpectedHash() throws Exception {
        byte[] rawSecret = new byte[] {(byte) 0xff, 0x00, 's', 'e', 'c', 'r', 'e', 't'};
        HashTokenTransformer rawSecretTransformer = new HashTokenTransformer(rawSecret);

        String hashedToken = rawSecretTransformer.transform(VALID_TOKEN);

        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(rawSecret, "HmacSHA256"));
        byte[] expectedHash = mac.doFinal(VALID_TOKEN.getBytes());
        String expectedHashedToken = Base64.getEncoder().encodeToString(expectedHash);

        assertEquals(expectedHashedToken, hashedToken);
    }
}
