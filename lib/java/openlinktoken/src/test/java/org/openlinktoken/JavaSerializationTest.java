/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.openlinktoken.crypto.CryptoSuite;
import org.openlinktoken.tokens.TokenGenerator;
import org.openlinktoken.tokens.tokenizer.CryptoSuiteTokenizer;
import org.openlinktoken.tokens.tokenizer.SHA256TokenDigest;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokens.tokenizer.SHA3TokenDigest;
import org.openlinktoken.tokens.tokenizer.SHAKE256TokenDigest;
import org.openlinktoken.tokens.tokenizer.TokenDigest;
import org.openlinktoken.tokens.tokenizer.TokenDigestFactory;
import org.openlinktoken.tokentransformer.DecryptTokenTransformer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.JweMatchTokenFormatter;

class JavaSerializationTest {

    private static final byte[] HASHING_SECRET = "0123456789abcdef0123456789abcdef".getBytes(StandardCharsets.UTF_8);

    @Test
    void featureProductionTypesImplementSerializable() throws ClassNotFoundException {
        List<Class<?>> types = List.of(
                EcKeyUtils.class,
                ExchangeConfig.class,
                ExchangeConfig.LoadedExchangeConfig.class,
                ExchangeConfig.ResolvedExchangeConfig.class,
                Class.forName("org.openlinktoken.ExchangeConfig$DecodedPayload"),
                ExchangeJwe.class,
                ExchangeJwe.ExchangePayload.class,
                ExchangeJwe.ExchangeJweException.class,
                ExchangeKem.class,
                ExchangeKem.DecryptionResult.class,
                ExchangeKeyBundle.class,
                ExchangeKeyBundle.KeyBundleException.class,
                JweMlkem.class,
                JweMlkem.Decryption.class,
                Class.forName("org.openlinktoken.JweMlkem$Encapsulation"),
                CryptoSuite.class,
                CryptoSuiteTokenizer.class,
                TokenDigest.class,
                TokenDigestFactory.class,
                SHA256TokenDigest.class,
                SHA3TokenDigest.class,
                SHAKE256TokenDigest.class,
                TokenGenerator.class,
                SHA256Tokenizer.class,
                DecryptTokenTransformer.class,
                HashTokenTransformer.class,
                JweMatchTokenFormatter.class);

        for (Class<?> type : types) {
            assertTrue(Serializable.class.isAssignableFrom(type), type.getName());
        }
    }

    @Test
    void loadedAndResolvedConfigsRoundTripPathsAndSecrets() throws Exception {
        Path path = Path.of("exchange-config.json");
        Map<String, Object> config = Map.of(
                "version", 1,
                "claims", List.of("exchange-name", true, 3));
        ExchangeConfig.LoadedExchangeConfig loaded =
                new ExchangeConfig.LoadedExchangeConfig(path, 1, config);

        ExchangeConfig.LoadedExchangeConfig loadedCopy =
                roundTrip(loaded, ExchangeConfig.LoadedExchangeConfig.class);

        assertEquals(path, loadedCopy.path());
        assertEquals(config, loadedCopy.config());

        byte[] privateKeyPem = "private-key-pem".getBytes(StandardCharsets.UTF_8);
        byte[] rotationIv = "rotation-iv".getBytes(StandardCharsets.UTF_8);
        ExchangeConfig.ResolvedExchangeConfig resolved = new ExchangeConfig.ResolvedExchangeConfig(
                path,
                1,
                config,
                Map.of("exchangeName", "serialized-exchange"),
                privateKeyPem,
                null,
                "sender",
                CryptoSuite.defaultSuite(),
                HASHING_SECRET,
                rotationIv,
                2,
                0.05,
                List.of(0.1, -0.2),
                null);

        ExchangeConfig.ResolvedExchangeConfig resolvedCopy =
                roundTrip(resolved, ExchangeConfig.ResolvedExchangeConfig.class);

        assertEquals(path, resolvedCopy.path());
        assertArrayEquals(privateKeyPem, resolvedCopy.privateKeyPem());
        assertArrayEquals(HASHING_SECRET, resolvedCopy.hashingSecret());
        assertArrayEquals(rotationIv, resolvedCopy.rotationIv());
    }

    @Test
    void cryptoSuiteAndHybridKeyBundleRoundTripPrivateState() throws Exception {
        CryptoSuite suite = roundTrip(CryptoSuite.SUITE_PQ_HYBRID_V1, CryptoSuite.class);

        assertSame(CryptoSuite.SUITE_PQ_HYBRID_V1, suite);
        assertEquals(CryptoSuite.SUITE_PQ_HYBRID_V1.getSuiteId(), suite.getSuiteId());

        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate(suite.getSuiteId());
        ExchangeKeyBundle bundleCopy = roundTrip(bundle, ExchangeKeyBundle.class);

        assertEquals(bundle, bundleCopy);
        assertEquals(bundle.hashCode(), bundleCopy.hashCode());
        assertEquals(bundle.getKid(), bundleCopy.getKid());
        assertArrayEquals(bundle.getMlkemPublicKey(), bundleCopy.getMlkemPublicKey());
        assertArrayEquals(bundle.getMlkemPrivateSeed(), bundleCopy.getMlkemPrivateSeed());
        assertArrayEquals(bundle.getEcPublicPem(), bundleCopy.getEcPublicPem());
        assertArrayEquals(bundle.getEcPrivatePem(), bundleCopy.getEcPrivatePem());
    }

    @Test
    void exchangePayloadAndV2DecryptionResultsRoundTripSecrets() throws Exception {
        ExchangeJwe.ExchangePayload payload = new ExchangeJwe.ExchangePayload(
                "serialized-exchange",
                HASHING_SECRET,
                "sender-public-key".getBytes(StandardCharsets.UTF_8),
                "recipient-public-key".getBytes(StandardCharsets.UTF_8),
                "P-256",
                "2026-09-23T00:00:00Z",
                "serialized-exchange-id",
                "rotation-iv".getBytes(StandardCharsets.UTF_8),
                3,
                0.05,
                List.of(0.1, -0.2));

        ExchangeJwe.ExchangePayload payloadCopy = roundTrip(payload, ExchangeJwe.ExchangePayload.class);

        assertArrayEquals(payload.hashingSecret(), payloadCopy.hashingSecret());
        assertArrayEquals(payload.rotationIv(), payloadCopy.rotationIv());
        assertEquals(payload.dimensionBias(), payloadCopy.dimensionBias());

        ExchangeKeyBundle sender = ExchangeKeyBundle.generate("suite-pq-v1");
        ExchangeKeyBundle recipient = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> envelope = ExchangeKem.buildExchangeEnvelopeV2(
                "serialized-exchange",
                HASHING_SECRET,
                sender,
                recipient,
                "2026-09-23T00:00:00Z",
                "serialized-exchange-id");
        ExchangeKem.DecryptionResult result = ExchangeKem.decryptExchangeEnvelopeV2(envelope, sender);
        ExchangeKem.DecryptionResult resultCopy = roundTrip(result, ExchangeKem.DecryptionResult.class);
        JweMlkem.Decryption internal = JweMlkem.decrypt(envelope, sender);
        JweMlkem.Decryption internalCopy = roundTrip(internal, JweMlkem.Decryption.class);

        assertArrayEquals(result.getPlaintext(), resultCopy.getPlaintext());
        assertArrayEquals(result.getTransportKey(), resultCopy.getTransportKey());
        assertArrayEquals(internal.plaintext(), internalCopy.plaintext());
        assertArrayEquals(internal.transportKey(), internalCopy.transportKey());
        assertArrayEquals(internal.cek(), internalCopy.cek());
        assertEquals(internal.protectedHeader(), internalCopy.protectedHeader());
    }

    @Test
    void suiteTokenizerRoundTripsItsDigestAndSecretTransformer() throws Exception {
        CryptoSuiteTokenizer tokenizer = new CryptoSuiteTokenizer(
                List.of(new HashTokenTransformer(HASHING_SECRET)),
                CryptoSuite.defaultSuite());

        CryptoSuiteTokenizer tokenizerCopy = roundTrip(tokenizer, CryptoSuiteTokenizer.class);

        assertEquals(tokenizer.tokenize("serializable-token"), tokenizerCopy.tokenize("serializable-token"));
    }

    private static <T> T roundTrip(T value, Class<T> type) throws Exception {
        ByteArrayOutputStream serialized = new ByteArrayOutputStream();
        try (ObjectOutputStream output = new ObjectOutputStream(serialized)) {
            output.writeObject(value);
        }

        try (ObjectInputStream input = new ObjectInputStream(new ByteArrayInputStream(serialized.toByteArray()))) {
            return type.cast(input.readObject());
        }
    }
}
