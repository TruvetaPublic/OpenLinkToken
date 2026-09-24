/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWEObject;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

/** Tests JWE formatter validation, token framing, headers, and nullable inputs. */
class JweMatchTokenFormatterTest {

    private static final String TEST_ENCRYPTION_KEY = "12345678901234567890123456789012"; // 32 chars
    private static final String TEST_RING_ID = "test-ring-2026";
    private static final String TEST_RULE_ID = "T1";
    private static final String TEST_TOKEN = "dGVzdC10b2tlbi1wcGlk"; // base64-encoded test token

    /** Verifies construction succeeds with a valid string key and required metadata. */
    @Test
    void testConstructorWithValidParameters() throws JOSEException {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");
        assertNotNull(formatter);
    }

    /** Verifies construction accepts a valid raw 32-byte encryption key. */
    @Test
    void testConstructorWithRaw32ByteKey() throws JOSEException {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8),
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");
        assertNotNull(formatter);
    }

    /** Verifies construction rejects a null encryption key. */
    @Test
    void testConstructorWithNullEncryptionKey() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter((String) null, TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
    }

    /** Verifies construction rejects a key with the wrong byte length. */
    @Test
    void testConstructorWithInvalidKeyLength() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter("short", TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
    }

    /** Verifies construction rejects a 32-character non-ASCII key whose UTF-8 length is not 32 bytes. */
    @Test
    void testConstructorWithNonAscii32CharacterKey() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter("é".repeat(32), TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
        assertEquals("Encryption key must be exactly 32 bytes (256 bits)", exception.getMessage());
    }

    /** Verifies construction rejects a null key-ring identifier. */
    @Test
    void testConstructorWithNullRingId() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(TEST_ENCRYPTION_KEY, null, TEST_RULE_ID, "test.issuer");
        });
    }

    /** Verifies construction rejects a null rule identifier. */
    @Test
    void testConstructorWithNullRuleId() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(TEST_ENCRYPTION_KEY, TEST_RING_ID, null, "test.issuer");
        });
    }

    /** Verifies transformation emits the versioned prefix and compact five-part JWE. */
    @Test
    void testTransformCreatesValidJweToken() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");

        String result = formatter.transform(TEST_TOKEN);

        // Verify the token has the correct prefix
        assertTrue(result.startsWith("olt.V1."));

        // Verify it's a valid JWE token (5 parts separated by dots after the prefix)
        String jweCompact = result.substring("olt.V1.".length());
        String[] parts = jweCompact.split("\\.");
        assertEquals(5, parts.length, "JWE compact serialization should have 5 parts");
    }

    /** Verifies transforming a null token returns null. */
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

    /** Verifies transforming an empty token preserves the empty value. */
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

    /** Verifies the compact JWE header contains the expected algorithm and key metadata. */
    @Test
    void testJweHeaderContainsCorrectMetadata() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");

        String result = formatter.transform(TEST_TOKEN);
        String jweCompact = result.substring("olt.V1.".length());

        // Parse the JWE object to inspect the header
        JWEObject jweObject = JWEObject.parse(jweCompact);

        // Verify header fields
        assertEquals("dir", jweObject.getHeader().getAlgorithm().getName());
        assertEquals("A256GCM", jweObject.getHeader().getEncryptionMethod().getName());
        assertEquals("match-token", jweObject.getHeader().getType().getType());
        assertEquals(TEST_RING_ID, jweObject.getHeader().getKeyID());
    }

    /** Verifies formatter construction succeeds when the issuer is omitted. */
    @Test
    void testDefaultIssuer() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                null // null issuer should default to "org.openlinktoken"
        );

        assertNotNull(formatter);
        // The default issuer is set internally and will be verified in the decrypted payload
    }
}
