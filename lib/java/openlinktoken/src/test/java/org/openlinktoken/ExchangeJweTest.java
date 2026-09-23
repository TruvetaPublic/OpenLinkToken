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
                JsonSupport.writeObject(envelope),
                keys.senderPrivatePem);
        assertEquals("demo-exchange", payload.exchangeName());
        assertArrayEquals(HASHING_SECRET, payload.hashingSecret());
        assertArrayEquals(ROTATION_IV, payload.rotationIv());
        assertEquals(50, payload.rotationCount());
        assertEquals(List.of(0.1, -0.2), payload.dimensionBias());
    }

    @Test
    void emitsUnpaddedBase64UrlPayloadFields() {
        KeyMaterial keys = generateKeyMaterial();

        Map<String, Object> envelope = buildEnvelope(keys);
        Map<String, Object> payload = JsonSupport.readObject(
                ExchangeJwe.decryptExchangeEnvelope(envelope, keys.senderPrivatePem));

        assertFalse(((String) payload.get("hashingSecret")).contains("="));
        assertFalse(((String) payload.get("rotationIv")).contains("="));
        assertFalse(((String) envelope.get("protected")).contains("="));
        assertArrayEquals(
                HASHING_SECRET,
                Base64.getUrlDecoder().decode((String) payload.get("hashingSecret")));
    }

    @Test
    void rejectsNonDefaultLegacySuite() {
        KeyMaterial keys = generateKeyMaterial();

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeJwe.buildExchangeEnvelope(
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
                        CryptoSuite.SUITE_SHA3_V1));
    }

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

    @Test
    void rejectsTamperedProtectedHeaderBeforeDecryption() {
        KeyMaterial keys = generateKeyMaterial();
        Map<String, Object> tampered = new LinkedHashMap<>(buildEnvelope(keys));
        Map<String, Object> protectedHeader = readProtectedHeader(tampered);
        protectedHeader.put("enc", "A128GCM");
        tampered.put("protected", CryptoEncoding.encodeBase64Url(JsonSupport.writeObject(protectedHeader)));

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

    private static Map<String, Object> readProtectedHeader(Map<String, Object> envelope) {
        return JsonSupport.readObject(
                CryptoEncoding.decodeBase64Url((String) envelope.get("protected"), "protected"));
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
