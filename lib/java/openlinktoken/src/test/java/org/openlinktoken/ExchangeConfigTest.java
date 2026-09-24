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

    /**
     * Verifies a version-one configuration can be loaded and resolved from a map, JSON bytes, text, or file.
     *
     * @throws Exception if the temporary configuration file cannot be created or read
     */
    @Test
    void loadsV1FromMappingJsonAndPath() throws Exception {
        V1Keys keys = generateV1Keys();
        Map<String, Object> envelope = buildV1Envelope(keys, 3);
        byte[] jsonBytes = ExchangeJsonTestSupport.writeObject(envelope);
        String jsonText = new String(jsonBytes, StandardCharsets.UTF_8);

        ExchangeConfig.LoadedExchangeConfig fromMapping = ExchangeConfig.loadExchangeConfig(envelope);
        ExchangeConfig.LoadedExchangeConfig fromJson = ExchangeConfig.loadExchangeConfig(jsonBytes);
        ExchangeConfig.LoadedExchangeConfig fromText = ExchangeConfig.loadExchangeConfig(jsonText);
        Path path = Files.createTempFile("openlinktoken-exchange", ".json");
        Files.write(path, jsonBytes);
        ExchangeConfig.LoadedExchangeConfig fromPath = ExchangeConfig.loadExchangeConfig(path);

        assertEquals(1, fromMapping.version());
        assertEquals(1, fromJson.version());
        assertEquals(1, fromText.version());
        assertEquals(path, fromPath.path());
        assertEquals(envelope.keySet(), fromMapping.config().keySet());
        assertEquals("sender", ExchangeConfig.resolveExchangeConfig(envelope, keys.senderPrivatePem()).privateKeyRole());
        assertEquals("sender", ExchangeConfig.resolveExchangeConfig(jsonBytes, keys.senderPrivatePem()).privateKeyRole());
        assertEquals("sender", ExchangeConfig.resolveExchangeConfig(jsonText, keys.senderPrivatePem()).privateKeyRole());
        assertEquals("sender", ExchangeConfig.resolveExchangeConfig(path, keys.senderPrivatePem()).privateKeyRole());
        assertEquals(
                "sender",
                ExchangeConfig.resolveLoadedExchangeConfig(fromMapping, keys.senderPrivatePem()).privateKeyRole());
    }

    /**
     * Verifies null, malformed, missing, and unsupported configuration inputs are rejected.
     *
     * @throws Exception if the temporary missing-path fixture cannot be created
     */
    @Test
    void rejectsInvalidConfigSources() throws Exception {
        assertThrows(NullPointerException.class, () -> ExchangeConfig.loadExchangeConfig((Path) null));
        assertThrows(IllegalArgumentException.class, () -> ExchangeConfig.loadExchangeConfig((String) null));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.loadExchangeConfig(new byte[] {(byte) 0xc3, 0x28}));
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.loadExchangeConfig("[]".getBytes(StandardCharsets.US_ASCII)));

        Path missingPath = Files.createTempFile("openlinktoken-missing-exchange", ".json");
        Files.delete(missingPath);
        assertThrows(IllegalArgumentException.class, () -> ExchangeConfig.loadExchangeConfig(missingPath));

        Map<String, Object> unsupportedValue = new LinkedHashMap<>();
        unsupportedValue.put("version", 1);
        unsupportedValue.put("unsupported", new Object());
        assertThrows(IllegalArgumentException.class, () -> ExchangeConfig.loadExchangeConfig(unsupportedValue));
    }

    /**
     * Verifies both version-one recipient roles derive the same transport key and payload settings.
     */
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
        assertArrayEquals(sender.transportEncryptionKey(), ExchangeConfig.deriveTransportEncryptionKey(recipient));
        assertEquals(32, sender.transportEncryptionKey().length);
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.resolveExchangeConfig(loaded, ExchangeKeyBundle.generate("suite-pq-v1")));
    }

    /**
     * Verifies both version-two recipient roles resolve the authenticated KEM transport key.
     */
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
        assertEquals(
                "sender",
                ExchangeConfig.resolveExchangeConfig(
                        new String(ExchangeJsonTestSupport.writeObject(envelope), StandardCharsets.UTF_8),
                        senderBundle)
                        .privateKeyRole());
        assertEquals("sender", ExchangeConfig.resolveLoadedExchangeConfig(loaded, senderBundle).privateKeyRole());
        assertThrows(
                IllegalArgumentException.class,
                () -> ExchangeConfig.resolveExchangeConfig(loaded, new byte[] {1}));
    }

    /**
     * Verifies unsupported, missing, and ambiguous version markers are rejected.
     */
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

    /**
     * Verifies invalid payload values and private keys unrelated to either supported version are rejected.
     */
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

    /**
     * Verifies loaded and resolved configurations do not expose mutable maps or byte-array state.
     */
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
