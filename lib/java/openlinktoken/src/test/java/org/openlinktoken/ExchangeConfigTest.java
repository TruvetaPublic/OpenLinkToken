/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.openlinktoken.crypto.CryptoSuite;

class ExchangeConfigTest {

    private static final byte[] HASHING_SECRET = "shared-hashing-secret".getBytes(StandardCharsets.UTF_8);
    private static final byte[] ROTATION_IV = "test-rotation-iv".getBytes(StandardCharsets.UTF_8);

    @Test
    void loadsV1FromMappingJsonAndPath() throws Exception {
        V1Keys keys = generateV1Keys();
        Map<String, Object> envelope = buildV1Envelope(keys, 3);

        ExchangeConfig.LoadedExchangeConfig fromMapping = ExchangeConfig.loadExchangeConfig(envelope);
        ExchangeConfig.LoadedExchangeConfig fromJson = ExchangeConfig.loadExchangeConfig(
                ExchangeJsonTestSupport.writeObject(envelope));
        Path path = Files.createTempFile("openlinktoken-exchange", ".json");
        Files.write(path, ExchangeJsonTestSupport.writeObject(envelope));
        ExchangeConfig.LoadedExchangeConfig fromPath = ExchangeConfig.loadExchangeConfig(path);

        assertEquals(1, fromMapping.version());
        assertEquals(1, fromJson.version());
        assertEquals(path, fromPath.path());
        assertEquals(envelope.keySet(), fromMapping.config().keySet());
    }

    @Test
    void resolvesV1ForBothRolesAndDerivesSharedTransportKey() {
        V1Keys keys = generateV1Keys();
        ExchangeConfig.LoadedExchangeConfig loaded =
                ExchangeConfig.loadExchangeConfig(buildV1Envelope(keys, 3));

        ExchangeConfig.ResolvedExchangeConfig sender =
                ExchangeConfig.resolveExchangeConfig(loaded, keys.senderPrivatePem());
        ExchangeConfig.ResolvedExchangeConfig recipient =
                ExchangeConfig.resolveExchangeConfig(loaded, keys.recipientPrivatePem());

        assertEquals(1, sender.version());
        assertEquals(CryptoSuite.defaultSuite(), sender.cryptoSuite());
        assertEquals("sender", sender.privateKeyRole());
        assertEquals("recipient", recipient.privateKeyRole());
        assertArrayEquals(HASHING_SECRET, sender.hashingSecret());
        assertArrayEquals(ROTATION_IV, sender.rotationIv());
        assertEquals(3, sender.rotationCount());
        assertEquals(0.05, sender.binWidth());
        assertEquals(List.of(0.1, -0.2), sender.dimensionBias());
        assertArrayEquals(sender.transportEncryptionKey(), recipient.transportEncryptionKey());
        assertArrayEquals(sender.transportEncryptionKey(), ExchangeConfig.deriveTransportEncryptionKey(sender));
        assertEquals(32, sender.transportEncryptionKey().length);
    }

    @Test
    void resolvesV2ForBothRolesAndReturnsKemTransportKey() {
        ExchangeKeyBundle senderBundle = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipientBundle = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                "pqc-exchange",
                "0123456789abcdef0123456789abcdef".getBytes(StandardCharsets.UTF_8),
                senderBundle,
                recipientBundle,
                "2026-03-12T00:00:00Z",
                "exchange-pqc");

        ExchangeConfig.LoadedExchangeConfig loaded = ExchangeConfig.loadExchangeConfig(envelope);
        ExchangeConfig.ResolvedExchangeConfig sender =
                ExchangeConfig.resolveExchangeConfig(loaded, senderBundle);
        ExchangeConfig.ResolvedExchangeConfig recipient =
                ExchangeConfig.resolveExchangeConfig(loaded, recipientBundle);

        assertEquals(2, sender.version());
        assertEquals(CryptoSuite.SUITE_PQ_V1, sender.cryptoSuite());
        assertEquals("sender", sender.privateKeyRole());
        assertEquals("recipient", recipient.privateKeyRole());
        assertArrayEquals(sender.transportEncryptionKey(), recipient.transportEncryptionKey());
        assertArrayEquals(sender.transportEncryptionKey(), ExchangeConfig.deriveTransportEncryptionKey(sender));
        assertEquals(32, sender.transportEncryptionKey().length);
        assertEquals(sender.payload(), recipient.payload());
    }

    @Test
    void rejectsMalformedUnsupportedAndAmbiguousVersions() {
        V1Keys keys = generateV1Keys();
        Map<String, Object> v1 = buildV1Envelope(keys, 3);

        Map<String, Object> missingVersion = new LinkedHashMap<>(v1);
        missingVersion.remove("version");
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.loadExchangeConfig(missingVersion));

        Map<String, Object> unsupported = new LinkedHashMap<>(v1);
        unsupported.put("version", 7);
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.loadExchangeConfig(unsupported));

        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> v2 = ExchangeKem.buildExchangeEnvelopeV2(
                "pqc-exchange",
                HASHING_SECRET,
                sender,
                recipient,
                "2026-03-12T00:00:00Z",
                "exchange-pqc");

        Map<String, Object> topLevelV2 = new LinkedHashMap<>(v2);
        topLevelV2.put("version", 2);
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.loadExchangeConfig(topLevelV2));

        Map<String, Object> ambiguous = new LinkedHashMap<>(v2);
        ambiguous.put("version", 1);
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.loadExchangeConfig(ambiguous));
    }

    @Test
    void rejectsInvalidPayloadValuesAndWrongPrivateKeys() {
        V1Keys keys = generateV1Keys();
        IllegalArgumentException invalidPayload = assertThrows(
                IllegalArgumentException.class,
                () -> buildV1Envelope(keys, -1));
        assertTrue(invalidPayload.getMessage().contains("rotationCount"));

        V1Keys unrelated = generateV1Keys();
        ExchangeConfig.LoadedExchangeConfig validLoaded =
                ExchangeConfig.loadExchangeConfig(buildV1Envelope(keys, 3));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.resolveExchangeConfig(validLoaded, unrelated.senderPrivatePem()));

        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle unrelatedBundle = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeConfig.LoadedExchangeConfig v2Loaded = ExchangeConfig.loadExchangeConfig(
                ExchangeKem.buildExchangeEnvelopeV2(
                        "pqc-exchange",
                        HASHING_SECRET,
                        sender,
                        recipient,
                        "2026-03-12T00:00:00Z",
                        "exchange-pqc"));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.resolveExchangeConfig(v2Loaded, unrelatedBundle));
    }

    @Test
    void keepsLoadedAndResolvedValuesDefensive() {
        V1Keys keys = generateV1Keys();
        Map<String, Object> envelope = buildV1Envelope(keys, 3);
        ExchangeConfig.LoadedExchangeConfig loaded = ExchangeConfig.loadExchangeConfig(envelope);

        envelope.put("version", 99);
        assertEquals(1, loaded.version());
        assertThrows(
                UnsupportedOperationException.class,
                () -> loaded.config().put("unexpected", true));

        ExchangeConfig.ResolvedExchangeConfig resolved =
                ExchangeConfig.resolveExchangeConfig(loaded, keys.senderPrivatePem());
        byte[] hashingSecret = resolved.hashingSecret();
        byte[] rotationIv = resolved.rotationIv();
        byte[] transportKey = resolved.transportEncryptionKey();
        hashingSecret[0] ^= 0x01;
        rotationIv[0] ^= 0x01;
        transportKey[0] ^= 0x01;

        assertArrayEquals(HASHING_SECRET, resolved.hashingSecret());
        assertArrayEquals(ROTATION_IV, resolved.rotationIv());
        assertNotEquals(transportKey[0], resolved.transportEncryptionKey()[0]);
        assertNotNull(resolved.privateKeyPem());
        assertFalse(resolved.payload().isEmpty());
        assertThrows(
                UnsupportedOperationException.class,
                () -> resolved.payload().put("unexpected", true));
    }

    private static Map<String, Object> buildV1Envelope(V1Keys keys, int rotationCount) {
        return ExchangeJwe.buildExchangeEnvelope(
                "demo-exchange",
                HASHING_SECRET,
                keys.senderPublicPem(),
                keys.recipientPublicPem(),
                "P-256",
                "2026-03-11T00:00:00Z",
                "exchange-123",
                ROTATION_IV,
                rotationCount,
                0.05,
                List.of(0.1, -0.2),
                CryptoSuite.defaultSuite());
    }

    private static V1Keys generateV1Keys() {
        KeyPair sender = EcKeyUtils.generateKeyPair("P-256");
        KeyPair recipient = EcKeyUtils.generateKeyPair("P-256");
        return new V1Keys(
                EcKeyUtils.privateKeyToPem(sender.getPrivate()),
                EcKeyUtils.publicKeyToPem(sender.getPublic()),
                EcKeyUtils.privateKeyToPem(recipient.getPrivate()),
                EcKeyUtils.publicKeyToPem(recipient.getPublic()));
    }

    private record V1Keys(
            byte[] senderPrivatePem,
            byte[] senderPublicPem,
            byte[] recipientPrivatePem,
            byte[] recipientPublicPem) {
    }
}
