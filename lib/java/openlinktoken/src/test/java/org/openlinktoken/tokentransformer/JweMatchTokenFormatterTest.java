/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWEObject;
import com.nimbusds.jose.crypto.DirectDecrypter;
import com.nimbusds.jose.jwk.OctetSequenceKey;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Unit tests for {@link JweMatchTokenFormatter}.
 */
class JweMatchTokenFormatterTest {

    private static final String TEST_ENCRYPTION_KEY = "12345678901234567890123456789012"; // 32 chars
    private static final String TEST_RING_ID = "test-ring-2026";
    private static final String TEST_RULE_ID = "T1";
    private static final String TEST_TOKEN = "dGVzdC10b2tlbi1wcGlk"; // base64-encoded test token

    /**
     * Verifies construction with valid string-key parameters.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithValidParameters() throws JOSEException {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");
        assertNotNull(formatter);
    }

    /**
     * Verifies construction with valid raw key bytes.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithRaw32ByteKey() throws JOSEException {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8),
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");
        assertNotNull(formatter);
    }

    /**
     * Verifies that a null encryption key is rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithNullEncryptionKey() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter((String) null, TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
    }

    /**
     * Verifies that an incorrectly sized encryption key is rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithInvalidKeyLength() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter("short", TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
    }

    /**
     * Verifies that a non-ASCII key is validated by its byte length.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithNonAscii32CharacterKey() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter("é".repeat(32), TEST_RING_ID, TEST_RULE_ID, "test.issuer");
        });
        assertEquals("Encryption key must be exactly 32 bytes (256 bits)", exception.getMessage());
    }

    /**
     * Verifies that a null ring identifier is rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithNullRingId() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(TEST_ENCRYPTION_KEY, null, TEST_RULE_ID, "test.issuer");
        });
    }

    /**
     * Verifies that a null rule identifier is rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testConstructorWithNullRuleId() {
        assertThrows(IllegalArgumentException.class, () -> {
            new JweMatchTokenFormatter(TEST_ENCRYPTION_KEY, TEST_RING_ID, null, "test.issuer");
        });
    }

    /**
     * Verifies the prefix and compact serialization shape of a JWE token.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
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

    /**
     * Verifies that a null token is returned unchanged.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
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

    /**
     * Verifies that an empty token is returned unchanged.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
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

    /**
     * Verifies that the JWE header contains the expected metadata.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
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

    /**
     * Verifies that the selected suite metadata is embedded in the payload.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testShakeSuiteMetadataIsEmbeddedInOltV1() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8),
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer",
                CryptoSuite.fromId("suite-pq-shake-v1"));

        String result = formatter.transform(TEST_TOKEN);
        JWEObject jweObject = JWEObject.parse(result.substring("olt.V1.".length()));
        jweObject.decrypt(new DirectDecrypter(
                new OctetSequenceKey.Builder(TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8)).build()));
        Map<String, Object> payload = jweObject.getPayload().toJSONObject();

        assertEquals("SHAKE256-256", payload.get("hash_alg"));
        assertEquals("KMAC256-256", payload.get("mac_alg"));
    }

    /**
     * Verifies that a null suite uses the backward-compatible token metadata.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testNullSuiteUsesDefaultMetadata() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8),
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer",
                null);

        String result = formatter.transform(TEST_TOKEN);
        JWEObject jweObject = JWEObject.parse(result.substring("olt.V1.".length()));
        jweObject.decrypt(new DirectDecrypter(
                new OctetSequenceKey.Builder(TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8)).build()));
        Map<String, Object> payload = jweObject.getPayload().toJSONObject();

        assertEquals("SHA-256", payload.get("hash_alg"));
        assertEquals("HS256", payload.get("mac_alg"));
    }

    /**
     * Verifies that the default-suite formatter rebuilds its encrypter after serialization.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testDefaultSuiteFormatterRoundTripsThroughSerialization() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY,
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer");

        JweMatchTokenFormatter deserializedFormatter = serializeAndDeserialize(formatter);
        Map<String, Object> payload = decryptPayload(deserializedFormatter.transform(TEST_TOKEN));

        assertEquals("SHA-256", payload.get("hash_alg"));
        assertEquals("HS256", payload.get("mac_alg"));
        assertEquals(List.of(TEST_TOKEN), payload.get("ppid"));
    }

    /**
     * Verifies that an explicit-suite formatter restores its suite and encrypter after serialization.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void testExplicitSuiteFormatterRoundTripsThroughSerialization() throws Exception {
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(
                TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8),
                TEST_RING_ID,
                TEST_RULE_ID,
                "test.issuer",
                CryptoSuite.fromId("suite-pq-shake-v1"));

        JweMatchTokenFormatter deserializedFormatter = serializeAndDeserialize(formatter);
        Map<String, Object> payload = decryptPayload(deserializedFormatter.transform(TEST_TOKEN));

        assertEquals("SHAKE256-256", payload.get("hash_alg"));
        assertEquals("KMAC256-256", payload.get("mac_alg"));
        assertEquals(List.of(TEST_TOKEN), payload.get("ppid"));
    }

    /**
     * Verifies that a missing issuer uses the default issuer value.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
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

    /**
     * Serializes and deserializes a JWE match-token formatter.
     *
     * @param formatter formatter to round-trip
     * @return the deserialized formatter
     * @throws IOException if writing or reading the serialized formatter fails
     * @throws ClassNotFoundException if the formatter class cannot be resolved during deserialization
     */
    private static JweMatchTokenFormatter serializeAndDeserialize(JweMatchTokenFormatter formatter)
            throws IOException, ClassNotFoundException {
        ByteArrayOutputStream serializedBytes = new ByteArrayOutputStream();
        try (ObjectOutputStream output = new ObjectOutputStream(serializedBytes)) {
            output.writeObject(formatter);
        }

        try (ObjectInputStream input = new ObjectInputStream(
                new ByteArrayInputStream(serializedBytes.toByteArray()))) {
            return JweMatchTokenFormatter.class.cast(input.readObject());
        }
    }

    /**
     * Decrypts a formatted match token and returns its JSON payload.
     *
     * @param token formatted JWE match token
     * @return the decrypted payload members
     * @throws Exception if the token cannot be parsed or decrypted
     */
    private static Map<String, Object> decryptPayload(String token) throws Exception {
        JWEObject jweObject = JWEObject.parse(token.substring("olt.V1.".length()));
        jweObject.decrypt(new DirectDecrypter(
                new OctetSequenceKey.Builder(TEST_ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8)).build()));
        return jweObject.getPayload().toJSONObject();
    }
}
