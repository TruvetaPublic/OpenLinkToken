/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Version-two ML-KEM exchange facade backed by standard general JWE JSON serialization.
 */
public final class ExchangeKem {

    /** Version-two exchange envelope version. */
    public static final int VERSION = JweMlkem.EXCHANGE_V2_VERSION;

    /** Version-two protected JWE type. */
    public static final String TYPE = JweMlkem.EXCHANGE_V2_TYPE;

    /** Version-two protected JWE content type. */
    public static final String CONTENT_TYPE = JweMlkem.EXCHANGE_V2_CONTENT_TYPE;

    /** Version-two protected JWE content-encryption algorithm. */
    public static final String ENCRYPTION = JweMlkem.EXCHANGE_V2_ENCRYPTION;

    /** Pure ML-KEM-768 recipient algorithm. */
    public static final String PURE_KEM_ALGORITHM = JweMlkem.PURE_KEM_ALGORITHM;

    /** Hybrid P-256 and ML-KEM-768 recipient algorithm. */
    public static final String HYBRID_KEM_ALGORITHM = JweMlkem.HYBRID_KEM_ALGORITHM;

    /** HKDF domain-separation label for the v2 token transport key. */
    public static final String TOKEN_TRANSPORT_KEY_INFO = JweMlkem.TOKEN_TRANSPORT_KEY_INFO;

    /** Alias matching the versioned Python exchange helper constants. */
    public static final int EXCHANGE_V2_VERSION = VERSION;

    /** Alias matching the versioned Python exchange helper constants. */
    public static final String EXCHANGE_V2_TYPE = TYPE;

    /** Alias matching the versioned Python exchange helper constants. */
    public static final String EXCHANGE_V2_CONTENT_TYPE = CONTENT_TYPE;

    /** Alias matching the versioned Python exchange helper constants. */
    public static final String EXCHANGE_V2_ENCRYPTION = ENCRYPTION;

    private static final String HASHING_SECRET_ENCODING = "base64url";
    private static final String ROTATION_IV_ENCODING = "base64url";

    private ExchangeKem() {
    }

    /**
     * Builds a version-two exchange envelope using the default exchange payload options.
     *
     * @param exchangeName the logical exchange name
     * @param hashingSecret the hashing secret
     * @param senderBundle the sender's private or public key bundle
     * @param recipientBundle the recipient's public key bundle
     * @param createdAt the exchange creation timestamp
     * @param exchangeId the authenticated exchange identifier
     * @return a standard general JWE JSON object
     */
    public static Map<String, Object> buildExchangeEnvelopeV2(
            String exchangeName,
            byte[] hashingSecret,
            ExchangeKeyBundle senderBundle,
            ExchangeKeyBundle recipientBundle,
            String createdAt,
            String exchangeId) {
        return buildExchangeEnvelopeV2(
                exchangeName,
                hashingSecret,
                senderBundle,
                recipientBundle,
                createdAt,
                exchangeId,
                new byte[0],
                0,
                0.05,
                List.of());
    }

    /**
     * Builds a version-two exchange envelope using standard general JWE JSON serialization.
     *
     * @param exchangeName the logical exchange name
     * @param hashingSecret the hashing secret
     * @param senderBundle the sender's private or public key bundle
     * @param recipientBundle the recipient's public key bundle
     * @param createdAt the exchange creation timestamp
     * @param exchangeId the authenticated exchange identifier
     * @param rotationIv the rotation-matrix initialization vector
     * @param rotationCount the number of rotation matrices
     * @param binWidth the quantization bin width
     * @param dimensionBias the rotation bias vector
     * @return a standard general JWE JSON object
     */
    public static Map<String, Object> buildExchangeEnvelopeV2(
            String exchangeName,
            byte[] hashingSecret,
            ExchangeKeyBundle senderBundle,
            ExchangeKeyBundle recipientBundle,
            String createdAt,
            String exchangeId,
            byte[] rotationIv,
            int rotationCount,
            double binWidth,
            List<Double> dimensionBias) {
        if (senderBundle == null || recipientBundle == null) {
            throw new IllegalArgumentException("Sender and recipient key bundles must not be null.");
        }
        if (!senderBundle.getSuite().getSuiteId().equals(recipientBundle.getSuite().getSuiteId())) {
            throw new IllegalArgumentException("Sender and recipient key bundles must use the same crypto suite.");
        }
        CryptoSuite suite = senderBundle.getSuite();
        if (suite.getExchangeConfigVersion() != JweMlkem.EXCHANGE_V2_VERSION) {
            throw new IllegalArgumentException(
                    "Suite '" + suite.getSuiteId() + "' does not use exchange configuration version 2.");
        }
        if (exchangeName == null || exchangeName.isEmpty() || exchangeId == null || exchangeId.isEmpty()) {
            throw new IllegalArgumentException("Exchange name and exchange ID must be non-empty.");
        }
        validateHashingSecret(hashingSecret, suite);
        if (rotationIv == null) {
            throw new IllegalArgumentException("Rotation IV must be bytes.");
        }
        if (rotationCount < 0) {
            throw new IllegalArgumentException("Rotation count must be non-negative.");
        }
        if (!(binWidth > 0.0) || !Double.isFinite(binWidth)) {
            throw new IllegalArgumentException("Bin width must be positive.");
        }
        List<Double> biases = dimensionBias == null ? List.of() : List.copyOf(dimensionBias);

        Map<String, Object> protectedHeader = new LinkedHashMap<>();
        protectedHeader.put("typ", JweMlkem.EXCHANGE_V2_TYPE);
        protectedHeader.put("cty", JweMlkem.EXCHANGE_V2_CONTENT_TYPE);
        protectedHeader.put("enc", JweMlkem.EXCHANGE_V2_ENCRYPTION);
        protectedHeader.put("version", JweMlkem.EXCHANGE_V2_VERSION);
        protectedHeader.put("cryptoSuite", suite.getSuiteId());
        protectedHeader.put("exchangeId", exchangeId);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("exchangeName", exchangeName);
        payload.put("cryptoSuite", suite.getSuiteId());
        payload.put("hashingSecret", CryptoEncoding.encodeBase64Url(hashingSecret));
        payload.put("hashingSecretEncoding", HASHING_SECRET_ENCODING);
        payload.put("senderKeyId", senderBundle.getKid());
        payload.put("recipientKeyId", recipientBundle.getKid());
        payload.put("senderKeyBundle", senderBundle.toMapping());
        payload.put("recipientKeyBundle", recipientBundle.toMapping());
        payload.put("createdAt", createdAt);
        payload.put("exchangeId", exchangeId);
        payload.put("rotationIv", CryptoEncoding.encodeBase64Url(rotationIv));
        payload.put("rotationIvEncoding", ROTATION_IV_ENCODING);
        payload.put("rotationCount", rotationCount);
        payload.put("binWidth", binWidth);
        payload.put("dimensionBias", biases);

        return JweMlkem.build(
                JsonSupport.writeObject(payload),
                protectedHeader,
                List.of(senderBundle, recipientBundle));
    }

    /**
     * Decrypts a version-two exchange envelope and returns its payload and transport key.
     *
     * @param exchangeConfig a standard general JWE JSON object
     * @param privateBundle the matching private key bundle
     * @return the authenticated plaintext and the separately derived transport key
     */
    public static DecryptionResult decryptExchangeEnvelopeV2(
            Map<String, ?> exchangeConfig,
            ExchangeKeyBundle privateBundle) {
        JweMlkem.Decryption decrypted = JweMlkem.decrypt(exchangeConfig, privateBundle);
        Map<String, Object> protectedHeader = decrypted.protectedHeader();
        CryptoSuite suite = CryptoSuite.fromId((String) protectedHeader.get("cryptoSuite"));
        Map<String, Object> payload = parsePayload(decrypted.plaintext());
        validatePayload(payload, suite, protectedHeader);
        return new DecryptionResult(decrypted.plaintext(), decrypted.transportKey());
    }

    /**
     * Decrypts a UTF-8 JSON version-two exchange envelope.
     *
     * @param exchangeConfig UTF-8 standard general JWE JSON
     * @param privateBundle the matching private key bundle
     * @return the authenticated plaintext and separately derived transport key
     */
    public static DecryptionResult decryptExchangeEnvelopeV2(
            byte[] exchangeConfig,
            ExchangeKeyBundle privateBundle) {
        try {
            return decryptExchangeEnvelopeV2(JsonSupport.readObject(exchangeConfig), privateBundle);
        } catch (IllegalArgumentException exception) {
            throw exception;
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Version-2 exchange envelope is not valid JSON.", exception);
        }
    }

    /**
     * Decrypts a version-two exchange envelope and returns only its plaintext payload.
     *
     * @param exchangeConfig a standard general JWE JSON object
     * @param privateBundle the matching private key bundle
     * @return the authenticated plaintext
     */
    public static byte[] decryptExchangeEnvelope(
            Map<String, ?> exchangeConfig,
            ExchangeKeyBundle privateBundle) {
        return decryptExchangeEnvelopeV2(exchangeConfig, privateBundle).getPlaintext();
    }

    /**
     * Decrypts a UTF-8 JSON version-two exchange envelope and returns its plaintext.
     *
     * @param exchangeConfig UTF-8 standard general JWE JSON
     * @param privateBundle the matching private key bundle
     * @return the authenticated plaintext
     */
    public static byte[] decryptExchangeEnvelope(
            byte[] exchangeConfig,
            ExchangeKeyBundle privateBundle) {
        return decryptExchangeEnvelopeV2(exchangeConfig, privateBundle).getPlaintext();
    }

    private static void validateHashingSecret(byte[] hashingSecret, CryptoSuite suite) {
        if (hashingSecret == null) {
            throw new IllegalArgumentException("Hashing secret must be bytes.");
        }
        if (CryptoSuite.TOKEN_MAC_KMAC256_256.equals(suite.getTokenMacAlgorithm())
                && hashingSecret.length < 32) {
            throw new IllegalArgumentException(
                    "Crypto suite '" + suite.getSuiteId()
                            + "' requires a hashing secret of at least 32 bytes.");
        }
    }

    private static Map<String, Object> parsePayload(byte[] plaintext) {
        try {
            return JsonSupport.readObject(plaintext);
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(
                    "Version-2 exchange payload is not valid JSON.", exception);
        }
    }

    private static void validatePayload(
            Map<String, Object> payload,
            CryptoSuite suite,
            Map<String, Object> protectedHeader) {
        if (!suite.getSuiteId().equals(payload.get("cryptoSuite"))) {
            throw new IllegalArgumentException(
                    "Version-2 exchange payload suite does not match the protected header.");
        }
        if (!protectedHeader.get("exchangeId").equals(payload.get("exchangeId"))) {
            throw new IllegalArgumentException(
                    "Version-2 exchange payload exchangeId does not match the protected header.");
        }

        String senderKeyId = requiredPayloadString(payload, "senderKeyId");
        String recipientKeyId = requiredPayloadString(payload, "recipientKeyId");
        validatePayloadBundle(payload, "senderKeyBundle", senderKeyId, suite);
        validatePayloadBundle(payload, "recipientKeyBundle", recipientKeyId, suite);
    }

    private static String requiredPayloadString(Map<String, Object> payload, String fieldName) {
        Object value = payload.get(fieldName);
        if (!(value instanceof String string) || string.isEmpty()) {
            throw new IllegalArgumentException("Version-2 exchange payload is missing " + fieldName + ".");
        }
        return string;
    }

    private static void validatePayloadBundle(
            Map<String, Object> payload,
            String fieldName,
            String expectedKid,
            CryptoSuite suite) {
        Object value = payload.get(fieldName);
        if (!(value instanceof Map<?, ?> map)) {
            throw new IllegalArgumentException("Version-2 exchange payload is missing " + fieldName + ".");
        }
        Map<String, Object> mapping = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (!(entry.getKey() instanceof String key)) {
                throw new IllegalArgumentException(fieldName + " must contain string field names.");
            }
            mapping.put(key, entry.getValue());
        }
        ExchangeKeyBundle bundle = ExchangeKeyBundle.fromMapping(mapping);
        if (!suite.getSuiteId().equals(bundle.getSuite().getSuiteId())
                || !expectedKid.equals(bundle.getKid())) {
            throw new IllegalArgumentException(
                    "Version-2 exchange payload " + fieldName + " does not match its key ID or suite.");
        }
    }

    /**
     * Immutable result returned by version-two exchange decryption.
     */
    public static final class DecryptionResult {
        private final byte[] plaintext;
        private final byte[] transportKey;

        private DecryptionResult(byte[] plaintext, byte[] transportKey) {
            this.plaintext = Arrays.copyOf(plaintext, plaintext.length);
            this.transportKey = Arrays.copyOf(transportKey, transportKey.length);
        }

        /**
         * Returns a copy of the decrypted exchange payload.
         *
         * @return UTF-8 JSON payload bytes
         */
        public byte[] getPlaintext() {
            return Arrays.copyOf(plaintext, plaintext.length);
        }

        /**
         * Returns a copy of the decrypted exchange payload.
         *
         * @return UTF-8 JSON payload bytes
         */
        public byte[] plaintext() {
            return getPlaintext();
        }

        /**
         * Returns a copy of the v2 token transport key.
         *
         * @return the 32-byte transport key
         */
        public byte[] getTransportKey() {
            return Arrays.copyOf(transportKey, transportKey.length);
        }

        /**
         * Returns a copy of the v2 token transport key.
         *
         * @return the 32-byte transport key
         */
        public byte[] transportKey() {
            return getTransportKey();
        }
    }
}
