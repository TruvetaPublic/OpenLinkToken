/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokentransformer;

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

class HashTokenTransformerTest {
    private static final String VALID_SECRET = "sampleSecret";
    private static final String VALID_TOKEN = "sampleToken";

    private HashTokenTransformer transformer;

    @BeforeEach
    void setup() throws NoSuchAlgorithmException, InvalidKeyException {
        transformer = new HashTokenTransformer(VALID_SECRET);
    }

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

    @Test
    void testTransform_NullToken_ThrowsIllegalArgumentException() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            transformer.transform(null);
        });
        assertEquals("Invalid Argument. Token can't be Null.", exception.getMessage());
    }

    @Test
    void testConstructor_NullSecret_InitializesWithNullMac() throws Exception {
        HashTokenTransformer nullSecretTransformer = new HashTokenTransformer((String) null);
        assertThrows(NullPointerException.class, () -> {
            nullSecretTransformer.transform(VALID_TOKEN);
        });
    }

    @Test
    void testConstructor_BlankSecret_InitializesWithNullMac() throws Exception {
        HashTokenTransformer blankSecretTransformer = new HashTokenTransformer("");
        assertThrows(NullPointerException.class, () -> {
            blankSecretTransformer.transform(VALID_TOKEN);
        });
    }

    @Test
    void testTransform_ValidTokenMultipleTimes_ReturnsConsistentHash() throws Exception {
        String hash1 = transformer.transform(VALID_TOKEN);
        String hash2 = transformer.transform(VALID_TOKEN);
        assertEquals(hash1, hash2); // The hashed value should be consistent
    }

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
