/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.Test;

class ExchangeKemTest {

    private static final List<String> V2_SUITES = List.of(
            "suite-pq-v1",
            "suite-pq-shake-v1",
            "suite-pq-hybrid-v1");

    @Test
    void buildsAndDecryptsEveryV2SuiteForBothRecipients() {
        for (String suiteId : V2_SUITES) {
            ExchangeKeyBundle sender = ExchangeKeyBundle.generate(suiteId);
            ExchangeKeyBundle recipient = ExchangeKeyBundle.generate(suiteId);
            Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                    "pqc-exchange",
                    "0123456789abcdef0123456789abcdef".getBytes(StandardCharsets.UTF_8),
                    sender,
                    recipient,
                    "2026-03-12T00:00:00Z",
                    "exchange-pqc-" + suiteId,
                    "rotation-iv".getBytes(StandardCharsets.UTF_8),
                    3,
                    0.05,
                    List.of(0.1, -0.2));

            assertEquals(
                    SetOf.members("protected", "recipients", "iv", "ciphertext", "tag"),
                    envelope.keySet());
            Map<String, Object> protectedHeader = ExchangeJsonTestSupport.readObject(
                    Base64.getUrlDecoder().decode((String) envelope.get("protected")));
            assertEquals("openlinktoken-exchange+jwe", protectedHeader.get("typ"));
            assertEquals("application/openlinktoken-exchange+json", protectedHeader.get("cty"));
            assertEquals("A256GCM", protectedHeader.get("enc"));
            assertEquals(2, protectedHeader.get("version"));
            assertEquals(suiteId, protectedHeader.get("cryptoSuite"));
            assertEquals("exchange-pqc-" + suiteId, protectedHeader.get("exchangeId"));
            Map<String, Object> expectedProtected = new LinkedHashMap<>();
            expectedProtected.put("typ", "openlinktoken-exchange+jwe");
            expectedProtected.put("cty", "application/openlinktoken-exchange+json");
            expectedProtected.put("enc", "A256GCM");
            expectedProtected.put("version", 2);
            expectedProtected.put("cryptoSuite", suiteId);
            expectedProtected.put("exchangeId", "exchange-pqc-" + suiteId);
            assertEquals(encode(ExchangeJsonTestSupport.writeObject(expectedProtected)), envelope.get("protected"));

            List<?> recipients = (List<?>) envelope.get("recipients");
            assertEquals(2, recipients.size());
            String expectedAlgorithm = suiteId.equals("suite-pq-hybrid-v1")
                    ? "ECDH-ES+ML-KEM-768"
                    : "ML-KEM-768";
            for (Object value : recipients) {
                Map<?, ?> entry = (Map<?, ?>) value;
                Map<?, ?> header = (Map<?, ?>) entry.get("header");
                assertEquals(expectedAlgorithm, header.get("alg"));
                assertTrue(header.get("kid") instanceof String);
                byte[] encryptedKey = decode((String) entry.get("encrypted_key"));
                assertEquals(1128, encryptedKey.length);
                assertEquals(suiteId.equals("suite-pq-hybrid-v1"), header.containsKey("epk"));
            }

            ExchangeKem.DecryptionResult senderResult = ExchangeKem.decryptExchangeEnvelopeV2(envelope, sender);
            ExchangeKem.DecryptionResult recipientResult =
                    ExchangeKem.decryptExchangeEnvelopeV2(envelope, recipient);
            assertArrayEquals(senderResult.getPlaintext(), recipientResult.getPlaintext());
            assertArrayEquals(senderResult.getTransportKey(), recipientResult.getTransportKey());
            assertEquals(32, senderResult.getTransportKey().length);
            JweMlkem.Decryption internal = JweMlkem.decrypt(envelope, sender);
            assertFalse(Arrays.equals(internal.cek(), internal.transportKey()));
            assertArrayEquals(senderResult.getPlaintext(), ExchangeKem.decryptExchangeEnvelope(envelope, sender));
            assertArrayEquals(
                    senderResult.getPlaintext(),
                    ExchangeKem.decryptExchangeEnvelope(ExchangeJsonTestSupport.writeObject(envelope), sender));
        }
    }

    @Test
    void derivesTransportKeySeparatelyFromTheJweCek() {
        byte[] cek = new byte[32];
        for (int index = 0; index < cek.length; index++) {
            cek[index] = (byte) index;
        }
        byte[] transportKey = JweMlkem.deriveTokenTransportKey(cek, "exchange-id-a1");

        assertEquals(
                "28cf4377e92ac7219f4454c73192e4bd6ca29076a648be934abb74f7350a7d6a",
                Hex.encode(transportKey));
        assertFalse(Arrays.equals(cek, transportKey));
        assertFalse(Arrays.equals(
                transportKey,
                JweMlkem.deriveTokenTransportKey(cek, "exchange-id-a2")));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.deriveTokenTransportKey(null, "exchange-id"));
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.deriveTokenTransportKey(new byte[31], "exchange-id"));
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.deriveTokenTransportKey(cek, ""));
    }

    @Test
    void rejectsInvalidDirectJweBuildInputs() {
        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> header = protectedHeader("suite-pq-v1");

        assertThrows(IllegalArgumentException.class, () -> JweMlkem.build(null, header, List.of(sender, recipient)));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.build(new byte[0], null, List.of(sender, recipient)));

        Map<String, Object> missingExchangeId = new LinkedHashMap<>(header);
        missingExchangeId.remove("exchangeId");
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.build(new byte[0], missingExchangeId, List.of(sender, recipient)));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.build(new byte[0], header, List.of(sender)));
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.build(new byte[0], header, Arrays.asList(sender, null)));
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.build(new byte[0], header, List.of(sender, sender)));

        Map<String, Object> unknownSuite = new LinkedHashMap<>(header);
        unknownSuite.put("cryptoSuite", "unknown-suite");
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.build(new byte[0], unknownSuite, List.of(sender, recipient)));
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.build(
                        new byte[0],
                        header,
                        List.of(sender, ExchangeKeyBundle.generate("suite-pq-shake-v1"))));
    }

    @Test
    void rejectsMalformedJweMembersAndContentParameters() {
        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                "malformed-test",
                "hash-secret".getBytes(StandardCharsets.UTF_8),
                sender,
                recipient,
                "2026-03-12T00:00:00Z",
                "exchange-malformed");

        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(null, sender));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(envelope, null));

        Map<String, Object> missingTag = copyEnvelope(envelope);
        missingTag.remove("tag");
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(missingTag, sender));

        Map<String, Object> invalidProtected = copyEnvelope(envelope);
        invalidProtected.put("protected", "*");
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidProtected, sender));

        Map<String, Object> invalidRecipientAlgorithm = copyEnvelope(envelope);
        Map<String, Object> invalidAlgorithmHeader = copyFirstRecipientHeader(invalidRecipientAlgorithm);
        invalidAlgorithmHeader.put("alg", "dir");
        setFirstRecipientHeader(invalidRecipientAlgorithm, invalidAlgorithmHeader);
        assertThrows(
                IllegalArgumentException.class,
                () -> JweMlkem.decrypt(invalidRecipientAlgorithm, sender));

        Map<String, Object> invalidEncryptedKey = copyEnvelope(envelope);
        recipients(invalidEncryptedKey).get(0).put("encrypted_key", "!");
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidEncryptedKey, sender));

        Map<String, Object> invalidIv = copyEnvelope(envelope);
        invalidIv.put("iv", encode(new byte[11]));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidIv, sender));

        Map<String, Object> invalidTag = copyEnvelope(envelope);
        invalidTag.put("tag", encode(new byte[15]));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidTag, sender));

        Map<String, Object> duplicateRecipient = copyEnvelope(envelope);
        recipients(duplicateRecipient).set(1, new LinkedHashMap<>(recipients(duplicateRecipient).get(0)));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(duplicateRecipient, sender));
    }

    @Test
    void rejectsMalformedHybridEphemeralKeysAndWrappedContentKeys() {
        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-hybrid-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-hybrid-v1");
        Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                "hybrid-malformed-test",
                "hash-secret".getBytes(StandardCharsets.UTF_8),
                sender,
                recipient,
                "2026-03-12T00:00:00Z",
                "exchange-hybrid-malformed");

        Map<String, Object> invalidCurve = copyEnvelope(envelope);
        Map<String, Object> curveHeader = copyFirstRecipientHeader(invalidCurve);
        Map<String, Object> invalidCurveEpk = copyStringMap((Map<?, ?>) curveHeader.get("epk"));
        invalidCurveEpk.put("crv", "P-384");
        curveHeader.put("epk", invalidCurveEpk);
        setFirstRecipientHeader(invalidCurve, curveHeader);
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidCurve, sender));

        Map<String, Object> invalidCoordinates = copyEnvelope(envelope);
        Map<String, Object> coordinatesHeader = copyFirstRecipientHeader(invalidCoordinates);
        Map<String, Object> invalidEpk = copyStringMap((Map<?, ?>) coordinatesHeader.get("epk"));
        invalidEpk.put("x", encode(new byte[32]));
        invalidEpk.put("y", encode(new byte[32]));
        coordinatesHeader.put("epk", invalidEpk);
        setFirstRecipientHeader(invalidCoordinates, coordinatesHeader);
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidCoordinates, sender));

        Map<String, Object> invalidWrappedKey = copyEnvelope(envelope);
        Map<String, Object> recipientEntry = recipients(invalidWrappedKey).get(0);
        byte[] encryptedKey = decode((String) recipientEntry.get("encrypted_key"));
        encryptedKey[encryptedKey.length - 1] ^= 0x01;
        recipientEntry.put("encrypted_key", encode(encryptedKey));
        assertThrows(IllegalArgumentException.class, () -> JweMlkem.decrypt(invalidWrappedKey, sender));
    }

    @Test
    void rejectsTamperingWrongSuiteWrongKeyAndRecipientLength() {
        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle unrelated = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle hybrid = ExchangeKeyBundle.generate("suite-pq-hybrid-v1");
        Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                "tamper-test",
                "hash-secret".getBytes(StandardCharsets.UTF_8),
                sender,
                recipient,
                "2026-03-12T00:00:00Z",
                "exchange-tamper");

        Map<String, Object> tamperedCiphertext = new LinkedHashMap<>(envelope);
        tamperedCiphertext.put("ciphertext", mutateBase64((String) envelope.get("ciphertext")));
        assertThrows(IllegalArgumentException.class,
                () -> ExchangeKem.decryptExchangeEnvelopeV2(tamperedCiphertext, sender));

        Map<String, Object> tamperedHeader = new LinkedHashMap<>(envelope);
        Map<String, Object> protectedHeader = ExchangeJsonTestSupport.readObject(
                decode((String) envelope.get("protected")));
        protectedHeader.put("exchangeId", "different-exchange");
        tamperedHeader.put("protected", encode(ExchangeJsonTestSupport.writeObject(protectedHeader)));
        assertThrows(IllegalArgumentException.class,
                () -> ExchangeKem.decryptExchangeEnvelopeV2(tamperedHeader, sender));

        Map<String, Object> tamperedAad = new LinkedHashMap<>(envelope);
        Map<String, Object> aadHeader = ExchangeJsonTestSupport.readObject(
                decode((String) envelope.get("protected")));
        aadHeader.put("aadTamper", true);
        tamperedAad.put("protected", encode(ExchangeJsonTestSupport.writeObject(aadHeader)));
        assertThrows(IllegalArgumentException.class,
                () -> ExchangeKem.decryptExchangeEnvelopeV2(tamperedAad, sender));

        assertThrows(IllegalArgumentException.class,
                () -> ExchangeKem.decryptExchangeEnvelopeV2(envelope, hybrid));
        assertThrows(IllegalArgumentException.class,
                () -> ExchangeKem.decryptExchangeEnvelopeV2(envelope, unrelated));

        Map<String, Object> shortRecipient = copyEnvelope(envelope);
        List<Map<String, Object>> recipients = recipients(shortRecipient);
        recipients.get(0).put("encrypted_key", encode(Arrays.copyOf(
                decode((String) recipients.get(0).get("encrypted_key")), 1127)));
        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeKem.decryptExchangeEnvelopeV2(shortRecipient, sender));
        assertTrue(exception.getMessage().contains("1128"));
    }

    @Test
    void rejectsMismatchedSuitesAndInvalidExchangeInputs() {
        ExchangeKeyBundle pure = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle shake = ExchangeKeyBundle.generate("suite-pq-shake-v1");

        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeKem.buildExchangeEnvelopeV2(
                        "mismatch",
                        new byte[] {1},
                        pure,
                        shake,
                        "2026-03-12T00:00:00Z",
                        "mismatch-id"));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeKem.buildExchangeEnvelopeV2(
                        "",
                        new byte[] {1},
                        pure,
                        pure,
                        "2026-03-12T00:00:00Z",
                        "empty-name"));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeKem.buildExchangeEnvelopeV2(
                        "negative-count",
                        new byte[] {1},
                        pure,
                        pure,
                        "2026-03-12T00:00:00Z",
                        "negative-count-id",
                        new byte[0],
                        -1,
                        0.05,
                        List.of()));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeKem.buildExchangeEnvelopeV2(
                        "short-kmac-secret",
                        new byte[31],
                        shake,
                        shake,
                        "2026-03-12T00:00:00Z",
                        "short-kmac-secret-id"));
    }

    @Test
    void preservesNonKmacEmptyHashingSecretBehavior() {
        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                "empty-secret",
                new byte[0],
                sender,
                recipient,
                "2026-03-12T00:00:00Z",
                "empty-secret-id");

        ExchangeKem.DecryptionResult result = ExchangeKem.decryptExchangeEnvelopeV2(envelope, recipient);
        Map<String, Object> payload = ExchangeJsonTestSupport.readObject(result.getPlaintext());
        assertEquals("", payload.get("hashingSecret"));
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> recipients(Map<String, Object> envelope) {
        return (List<Map<String, Object>>) envelope.get("recipients");
    }

    private static Map<String, Object> copyEnvelope(Map<String, Object> envelope) {
        Map<String, Object> copy = new LinkedHashMap<>(envelope);
        List<Map<String, Object>> recipientCopies = new ArrayList<>();
        for (Map<String, Object> recipient : recipients(envelope)) {
            Map<String, Object> recipientCopy = new LinkedHashMap<>(recipient);
            recipientCopy.put("header", copyStringMap((Map<?, ?>) recipient.get("header")));
            recipientCopies.add(recipientCopy);
        }
        copy.put("recipients", recipientCopies);
        return copy;
    }

    private static Map<String, Object> protectedHeader(String suiteId) {
        Map<String, Object> header = new LinkedHashMap<>();
        header.put("typ", JweMlkem.EXCHANGE_V2_TYPE);
        header.put("cty", JweMlkem.EXCHANGE_V2_CONTENT_TYPE);
        header.put("enc", JweMlkem.EXCHANGE_V2_ENCRYPTION);
        header.put("version", JweMlkem.EXCHANGE_V2_VERSION);
        header.put("cryptoSuite", suiteId);
        header.put("exchangeId", "direct-build-test");
        return header;
    }

    private static Map<String, Object> copyFirstRecipientHeader(Map<String, Object> envelope) {
        return copyStringMap((Map<?, ?>) recipients(envelope).get(0).get("header"));
    }

    private static void setFirstRecipientHeader(Map<String, Object> envelope, Map<String, Object> header) {
        recipients(envelope).get(0).put("header", header);
    }

    private static Map<String, Object> copyStringMap(Map<?, ?> source) {
        Map<String, Object> copy = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            copy.put((String) entry.getKey(), entry.getValue());
        }
        return copy;
    }

    private static byte[] decode(String value) {
        return Base64.getUrlDecoder().decode(value);
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private static String mutateBase64(String value) {
        byte[] decoded = decode(value);
        decoded[0] ^= 0x01;
        return encode(decoded);
    }

    private static final class Hex {
        private Hex() {
        }

        private static String encode(byte[] value) {
            StringBuilder result = new StringBuilder(value.length * 2);
            for (byte item : value) {
                result.append(String.format("%02x", item & 0xff));
            }
            return result.toString();
        }
    }

    private static final class SetOf {
        private SetOf() {
        }

        private static Set<String> members(String... values) {
            return Set.of(values);
        }
    }
}
