/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.junit.jupiter.api.Test;
import org.openlinktoken.crypto.CryptoSuite;

class ExchangeJweTest {

    private static final byte[] HASHING_SECRET = "shared-hashing-secret".getBytes(StandardCharsets.UTF_8);
    private static final byte[] ROTATION_IV = "test-rotation-iv-24".getBytes(StandardCharsets.UTF_8);

    /**
     * Verifies a version-one envelope matches the Python-compatible shape and decrypts for both recipients.
     *
     * <p>Takes no arguments and returns no value.</p>
     */
    @Test
    void buildsPythonCompatibleEnvelopeAndDecryptsForEitherRecipient() {
        KeyMaterial keys = generateKeyMaterial();

        Map<String, Object> envelope = buildEnvelope(keys);

        assertEquals(Set.of("version", "protected", "recipients", "iv", "ciphertext", "tag"), envelope.keySet());
        assertEquals(ExchangeJwe.VERSION, envelope.get("version"));

        Map<String, Object> protectedHeader = readProtectedHeader(envelope);
        assertEquals(ExchangeJwe.TYPE, protectedHeader.get("typ"));
        assertEquals(ExchangeJwe.CONTENT_TYPE, protectedHeader.get("cty"));
        assertEquals(ExchangeJwe.ENCRYPTION, protectedHeader.get("enc"));
        assertFalse(protectedHeader.containsKey("alg"));
        assertFalse(protectedHeader.containsKey("cryptoSuite"));
        assertFalse(protectedHeader.containsKey("crit"));

        List<?> recipients = (List<?>) envelope.get("recipients");
        assertEquals(2, recipients.size());
        assertEquals(
                Set.of(
                        EcKeyUtils.fingerprintToKid(EcKeyUtils.publicKeyFingerprint(keys.senderPublicPem)),
                        EcKeyUtils.fingerprintToKid(EcKeyUtils.publicKeyFingerprint(keys.recipientPublicPem))),
                recipients.stream()
                        .map(entry -> ((Map<?, ?>) entry).get("header"))
                        .map(header -> ((Map<?, ?>) header).get("kid"))
                        .collect(Collectors.toSet()));
        for (Object recipient : recipients) {
            Map<?, ?> header = (Map<?, ?>) ((Map<?, ?>) recipient).get("header");
            assertEquals(ExchangeJwe.RECIPIENT_ALGORITHM, header.get("alg"));
            assertTrue(header.containsKey("epk"));
        }

        byte[] senderPayload = ExchangeJwe.decryptExchangeEnvelope(envelope, keys.senderPrivatePem);
        byte[] recipientPayload = ExchangeJwe.decryptExchangeEnvelope(envelope, keys.recipientPrivatePem);

        assertArrayEquals(senderPayload, recipientPayload);
        ExchangeJwe.ExchangePayload payload = ExchangeJwe.decryptExchangePayload(
                ExchangeJsonTestSupport.writeObject(envelope),
                keys.senderPrivatePem);
        assertEquals("demo-exchange", payload.exchangeName());
        assertArrayEquals(HASHING_SECRET, payload.hashingSecret());
        assertArrayEquals(ROTATION_IV, payload.rotationIv());
        assertEquals(50, payload.rotationCount());
        assertEquals(List.of(0.1, -0.2), payload.dimensionBias());
    }

    /**
     * Verifies secret, IV, and protected-header fields use unpadded base64url encoding.
     */
    @Test
    void emitsUnpaddedBase64UrlPayloadFields() {
        KeyMaterial keys = generateKeyMaterial();

        Map<String, Object> envelope = buildEnvelope(keys);
        Map<String, Object> payload = ExchangeJsonTestSupport.readObject(
                ExchangeJwe.decryptExchangeEnvelope(envelope, keys.senderPrivatePem));

        assertFalse(((String) payload.get("hashingSecret")).contains("="));
        assertFalse(((String) payload.get("rotationIv")).contains("="));
        assertFalse(((String) envelope.get("protected")).contains("="));
        assertArrayEquals(
                HASHING_SECRET,
                Base64.getUrlDecoder().decode((String) payload.get("hashingSecret")));
    }

    /**
     * Verifies suite identity cannot be supplied inside a legacy exchange payload.
     *
     * <p>Takes no arguments and returns no value.</p>
     */
    @Test
    void rejectsCryptoSuiteInLegacyPayload() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> payload = ExchangeJsonTestSupport.readObject(
                ExchangeJwe.decryptExchangeEnvelope(buildEnvelope(keys), keys.senderPrivatePem));
        payload.put("cryptoSuite", CryptoSuite.defaultSuite().getSuiteId());

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.parseExchangePayload(ExchangeJsonTestSupport.writeObject(payload)));
    }

    /**
     * Verifies a non-default v1 suite is authenticated in a critical protected-header parameter.
     *
     * <p>Takes no arguments and returns no value.</p>
     */
    @Test
    void buildsAndDecryptsSha3LegacySuiteWithCriticalHeader() {
        KeyMaterial keys = generateKeyMaterial();

        Map<String, Object> envelope = ExchangeJwe.buildExchangeEnvelope(
                "legacy-suite",
                HASHING_SECRET,
                keys.senderPublicPem,
                keys.recipientPublicPem,
                "P-256",
                "2026-03-11T00:00:00Z",
                "exchange-legacy-suite",
                ROTATION_IV,
                0,
                0.05,
                List.of(),
                CryptoSuite.SUITE_SHA3_V1);

        Map<String, Object> protectedHeader = readProtectedHeader(envelope);
        assertEquals("suite-sha3-v1", protectedHeader.get("cryptoSuite"));
        assertEquals(List.of("cryptoSuite"), protectedHeader.get("crit"));

        Map<String, Object> payload = ExchangeJsonTestSupport.readObject(
                ExchangeJwe.decryptExchangeEnvelope(envelope, keys.senderPrivatePem));
        assertFalse(payload.containsKey("cryptoSuite"));
    }

    /**
     * Verifies suite metadata is rejected unless it is critical and protected.
     *
     * <p>Takes no arguments and returns no value.</p>
     */
    @Test
    void rejectsMalformedOrUnprotectedSuiteHeaders() {
        KeyMaterial keys = generateKeyMaterial();

        Map<String, Object> unmarkedSuite = buildEnvelope(keys);
        Map<String, Object> unmarkedSuiteHeader = readProtectedHeader(unmarkedSuite);
        unmarkedSuiteHeader.put("cryptoSuite", "suite-sha3-v1");
        updateProtectedHeader(unmarkedSuite, unmarkedSuiteHeader);
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(unmarkedSuite, keys.senderPrivatePem));

        Map<String, Object> missingSuite = buildEnvelope(keys);
        Map<String, Object> missingSuiteHeader = readProtectedHeader(missingSuite);
        missingSuiteHeader.put("crit", List.of("cryptoSuite"));
        updateProtectedHeader(missingSuite, missingSuiteHeader);
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(missingSuite, keys.senderPrivatePem));

        Map<String, Object> unprotectedSuite = buildEnvelope(keys);
        unprotectedSuite.put("unprotected", Map.of("cryptoSuite", "suite-sha3-v1"));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(unprotectedSuite, keys.senderPrivatePem));
    }

    /**
     * Verifies malformed JSON and envelopes missing required structural fields are rejected.
     */
    @Test
    void rejectsMalformedEnvelopeJsonAndStructure() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> envelope = buildEnvelope(keys);

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope("not-json".getBytes(), keys.senderPrivatePem));

        Map<String, Object> missingVersion = new LinkedHashMap<>(envelope);
        missingVersion.remove("version");
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(missingVersion, keys.senderPrivatePem));

        Map<String, Object> missingRecipients = new LinkedHashMap<>(envelope);
        missingRecipients.remove("recipients");
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(missingRecipients, keys.senderPrivatePem));
    }

    /**
     * Verifies omitted rotation options resolve to their documented defaults.
     */
    @Test
    void buildsDefaultPayloadOptions() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> envelope = ExchangeJwe.buildExchangeEnvelope(
                "demo-exchange",
                HASHING_SECRET,
                keys.senderPublicPem,
                keys.recipientPublicPem,
                "P-256",
                "2026-03-11T00:00:00Z",
                "exchange-defaults");

        ExchangeJwe.ExchangePayload payload =
                ExchangeJwe.decryptExchangePayload(envelope, keys.senderPrivatePem);

        assertEquals(0, payload.rotationCount());
        assertEquals(0.05, payload.binWidth());
        assertArrayEquals(new byte[0], payload.rotationIv());
        assertEquals(List.of(), payload.dimensionBias());
    }

    /**
     * Verifies invalid UTF-8 and malformed version-one payload fields are rejected.
     */
    @Test
    void rejectsMalformedUtf8AndInvalidPayloadFields() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> payload = ExchangeJsonTestSupport.readObject(
                ExchangeJwe.decryptExchangeEnvelope(buildEnvelope(keys), keys.senderPrivatePem));

        Map<String, Object> invalid = new LinkedHashMap<>(payload);
        invalid.put("hashingSecretEncoding", "base64");
        assertInvalidPayload(invalid);

        invalid = new LinkedHashMap<>(payload);
        invalid.put("hashingSecret", payload.get("hashingSecret") + "=");
        assertInvalidPayload(invalid);

        invalid = new LinkedHashMap<>(payload);
        invalid.put("senderKeyFingerprint", "00");
        assertInvalidPayload(invalid);

        invalid = new LinkedHashMap<>(payload);
        invalid.put("rotationCount", 1.5);
        assertInvalidPayload(invalid);

        invalid = new LinkedHashMap<>(payload);
        invalid.put("binWidth", 0.0);
        assertInvalidPayload(invalid);

        invalid = new LinkedHashMap<>(payload);
        invalid.put("dimensionBias", List.of("not-a-number"));
        assertInvalidPayload(invalid);

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.parseExchangePayload(new byte[] {(byte) 0xc3, 0x28}));
    }

    /**
     * Verifies ciphertext tampering and unrelated private keys cannot decrypt an envelope.
     */
    @Test
    void rejectsTamperedCiphertextAndUnrelatedPrivateKey() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> tampered = new LinkedHashMap<>(buildEnvelope(keys));
        tampered.put("ciphertext", mutateBase64Url((String) tampered.get("ciphertext")));

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(tampered, keys.senderPrivatePem));

        KeyMaterial unrelated = generateKeyMaterial();
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(buildEnvelope(keys), unrelated.senderPrivatePem));
    }

    /**
     * Verifies an unsupported protected content-encryption value is rejected before decryption.
     */
    @Test
    void rejectsTamperedProtectedHeaderBeforeDecryption() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> tampered = new LinkedHashMap<>(buildEnvelope(keys));
        Map<String, Object> protectedHeader = readProtectedHeader(tampered);
        protectedHeader.put("enc", "A128GCM");
        tampered.put(
                "protected",
                Base64.getUrlEncoder().withoutPadding().encodeToString(
                        ExchangeJsonTestSupport.writeObject(protectedHeader)));

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.decryptExchangeEnvelope(tampered, keys.senderPrivatePem));
    }

    private static Map<String, Object> buildEnvelope(KeyMaterial keys) {
        return ExchangeJwe.buildExchangeEnvelope(
                "demo-exchange",
                HASHING_SECRET,
                keys.senderPublicPem,
                keys.recipientPublicPem,
                "P-256",
                "2026-03-11T00:00:00Z",
                "exchange-123",
                ROTATION_IV,
                50,
                0.05,
                List.of(0.1, -0.2),
                CryptoSuite.defaultSuite());
    }

    /**
     * Verifies a mapping with invalid payload fields fails JSON payload validation.
     *
     * @param payload invalid exchange payload fields
     */
    private static void assertInvalidPayload(Map<String, Object> payload) {
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.parseExchangePayload(ExchangeJsonTestSupport.writeObject(payload)));
    }

    private static Map<String, Object> readProtectedHeader(Map<String, Object> envelope) {
        return ExchangeJsonTestSupport.readObject(
                Base64.getUrlDecoder().decode((String) envelope.get("protected")));
    }

    /**
     * Replaces the encoded protected header in a JWE envelope; returns no value.
     *
     * @param envelope mutable general JSON JWE envelope
     * @param protectedHeader replacement protected-header fields
     */
    private static void updateProtectedHeader(Map<String, Object> envelope, Map<String, Object> protectedHeader) {
        envelope.put(
                "protected",
                Base64.getUrlEncoder().withoutPadding().encodeToString(
                        ExchangeJsonTestSupport.writeObject(protectedHeader)));
    }

    private static KeyMaterial generateKeyMaterial() {
        KeyPair sender = EcKeyUtils.generateKeyPair("P-256");
        KeyPair recipient = EcKeyUtils.generateKeyPair("P-256");
        return new KeyMaterial(
                EcKeyUtils.privateKeyToPem(sender.getPrivate()),
                EcKeyUtils.publicKeyToPem(sender.getPublic()),
                EcKeyUtils.privateKeyToPem(recipient.getPrivate()),
                EcKeyUtils.publicKeyToPem(recipient.getPublic()));
    }

    private static String mutateBase64Url(String value) {
        byte[] decoded = Base64.getUrlDecoder().decode(value);
        decoded[0] ^= 0x01;
        return Base64.getUrlEncoder().withoutPadding().encodeToString(decoded);
    }

    private record KeyMaterial(
            byte[] senderPrivatePem,
            byte[] senderPublicPem,
            byte[] recipientPrivatePem,
            byte[] recipientPublicPem) {
    }
}
