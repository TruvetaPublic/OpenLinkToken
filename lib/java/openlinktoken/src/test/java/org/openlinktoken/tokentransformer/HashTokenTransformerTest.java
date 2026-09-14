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

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Tests keyed token transformation, suite selection, and serialization.
 */
class HashTokenTransformerTest {
    private static final String VALID_SECRET = "sampleSecret";
    private static final String VALID_TOKEN = "sampleToken";

    private HashTokenTransformer transformer;

    /**
     * Creates the default-suite transformer used by the baseline tests.
     */
    @BeforeEach
    void setup() throws NoSuchAlgorithmException, InvalidKeyException {
        transformer = new HashTokenTransformer(VALID_SECRET);
    }

    /**
     * Verifies that a serialized transformer rebuilds its transient MAC state.
     */
    @Test
    void testSerializable() throws Exception {
        TokenTransformer encryptTokenTransformer = new HashTokenTransformer(VALID_SECRET);
        byte[] serialized = SerializationUtils.serialize(encryptTokenTransformer);
        TokenTransformer deserialized = SerializationUtils.deserialize(serialized);
        String hashedToken = deserialized.transform(VALID_TOKEN);

        assertNotNull(hashedToken);

        // Manually calculate the expected hash for validation
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(VALID_SECRET.getBytes(), "HmacSHA256"));
        byte[] expectedHash = mac.doFinal(VALID_TOKEN.getBytes());
        String expectedHashedToken = Base64.getEncoder().encodeToString(expectedHash);

        assertEquals(expectedHashedToken, hashedToken);
    }

    /**
     * Verifies hashing with the default HMAC-SHA-256 suite.
     */
    @Test
    void testTransform_ValidToken_ReturnsHashedToken() throws Exception {
        String hashedToken = transformer.transform(VALID_TOKEN);
        assertNotNull(hashedToken);

        // Manually calculate the expected hash for validation
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(VALID_SECRET.getBytes(), "HmacSHA256"));
        byte[] expectedHash = mac.doFinal(VALID_TOKEN.getBytes());
        String expectedHashedToken = Base64.getEncoder().encodeToString(expectedHash);

        assertEquals(expectedHashedToken, hashedToken);
    }

    /**
     * Verifies that null tokens are rejected.
     */
    @Test
    void testTransform_NullToken_ThrowsIllegalArgumentException() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            transformer.transform(null);
        });
        assertEquals("Invalid Argument. Token can't be Null.", exception.getMessage());
    }

    /**
     * Verifies the behavior of a transformer initialized with a null secret.
     */
    @Test
    void testConstructor_NullSecret_InitializesWithNullMac() throws Exception {
        HashTokenTransformer nullSecretTransformer = new HashTokenTransformer((String) null);
        assertThrows(NullPointerException.class, () -> {
            nullSecretTransformer.transform(VALID_TOKEN);
        });
    }

    /**
     * Verifies the behavior of a transformer initialized with a blank secret.
     */
    @Test
    void testConstructor_BlankSecret_InitializesWithNullMac() throws Exception {
        HashTokenTransformer blankSecretTransformer = new HashTokenTransformer("");
        assertThrows(NullPointerException.class, () -> {
            blankSecretTransformer.transform(VALID_TOKEN);
        });
    }

    /**
     * Verifies that hashing the same token repeatedly is deterministic.
     */
    @Test
    void testTransform_ValidTokenMultipleTimes_ReturnsConsistentHash() throws Exception {
        String hash1 = transformer.transform(VALID_TOKEN);
        String hash2 = transformer.transform(VALID_TOKEN);
        assertEquals(hash1, hash2); // The hashed value should be consistent
    }

    /**
     * Verifies hashing with raw secret bytes.
     */
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

    /**
     * Verifies the fixed vector for the SHA-3 suite.
     */
    @Test
    void testTransform_Sha3Suite_ReturnsFixedVector() throws Exception {
        HashTokenTransformer sha3Transformer =
                new HashTokenTransformer("sampleSecret".getBytes(), CryptoSuite.fromId("suite-sha3-v1"));

        assertEquals(
                "0Y3qAZTI1zwnHdNznv7lec1sz5Uu8rpa/dYMZFWqLSg=",
                sha3Transformer.transform("ab96273f069fc38264bf16cc2287218779c5eed6c0fee89490b990ffc35a2af5"));
    }

    /**
     * Verifies the fixed vector for the SHAKE and KMAC suite.
     */
    @Test
    void testTransform_ShakeSuite_ReturnsFixedVector() throws Exception {
        HashTokenTransformer shakeTransformer = new HashTokenTransformer(
                "0123456789abcdef0123456789abcdef".getBytes(),
                CryptoSuite.fromId("suite-pq-shake-v1"));

        assertEquals(
                "ylKfGg587NihC8+Sc2GSeR4g+INl76rLvAB1RYLRfA8=",
                shakeTransformer.transform("083e2185f52946fb45e459794409b2ea56e64241ba22a29072ad25b5947c023a"));
    }
}
