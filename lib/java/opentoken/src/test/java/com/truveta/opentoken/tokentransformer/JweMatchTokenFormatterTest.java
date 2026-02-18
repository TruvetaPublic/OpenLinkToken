/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokentransformer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWEObject;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link JweMatchTokenFormatter}.
 */
class JweMatchTokenFormatterTest {

    private static final String TEST_ENCRYPTION_KEY = "12345678901234567890123456789012"; // 32 chars
    private static final String TEST_RING_ID = "test-ring-2026";
    private static final String TEST_RULE_ID = "T1";
    private static final String TEST_TOKEN = "dGVzdC10b2tlbi1wcGlk"; // base64-encoded test token

    @Test
    void testConstructorWithValidParameters() throws JOSEException {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");
        assertNotNull(formatter);
    }

    @Test
    void testConstructorWithNullEncryptionKey() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(null, TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
    }

    @Test
    void testConstructorWithInvalidKeyLength() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter("short", TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
    }

    @Test
    void testConstructorWithNullRingId() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(TEST_ENCRYPTION_KEY, null, TEST_RULE_ID, "test.issuer");
        });
    }

    @Test
    void testConstructorWithNullRuleId() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(TEST_ENCRYPTION_KEY, TEST_RING_ID, null, "test.issuer");
        });
    }

    @Test
    void testTransformCreatesValidJweToken() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");

        String result = formatter.transform(TEST_TOKEN);

        // Verify the token has the correct prefix
        assertTrue(result.startsWith("ot.V1."));

        // Verify it's a valid JWE token (5 parts separated by dots after the prefix)
        String jweCompact = result.substring("ot.V1.".length());
        String[] parts = jweCompact.split("\\.");
        assertEquals(5, parts.length, "JWE compact serialization should have 5 parts");
    }

    @Test
    void testTransformWithNullToken() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                null);

        String result = formatter.transform(null);
        assertNull(result);
    }

    @Test
    void testTransformWithEmptyToken() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                null);

        String result = formatter.transform("");
        assertEquals("", result);
    }

    @Test
    void testJweHeaderContainsCorrectMetadata() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");

        String result = formatter.transform(TEST_TOKEN);
        String jweCompact = result.substring("ot.V1.".length());

        // Parse the JWE object to inspect the header
        JWEObject jweObject = JWEObject.parse(jweCompact);

        // Verify header fields
        assertEquals("dir", jweObject.getHeader().getAlgorithm().getName());
        assertEquals("A256GCM", jweObject.getHeader().getEncryptionMethod().getName());
        assertEquals("match-token", jweObject.getHeader().getType().getType());
        assertEquals(TEST_RING_ID, jweObject.getHeader().getKeyID());
    }

    @Test
    void testDefaultIssuer() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                null // null issuer should default to "truveta.opentoken"
        );

        assertNotNull(formatter);
        // The default issuer is set internally and will be verified in the decrypted payload
    }
}
