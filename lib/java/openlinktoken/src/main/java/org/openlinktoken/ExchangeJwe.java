/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.IOException;
import java.io.Serializable;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.nimbusds.jose.EncryptionMethod;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.JWEAlgorithm;
import com.nimbusds.jose.JWEHeader;
import com.nimbusds.jose.JWEObjectJSON;
import com.nimbusds.jose.Payload;
import com.nimbusds.jose.crypto.MultiDecrypter;
import com.nimbusds.jose.crypto.MultiEncrypter;
import com.nimbusds.jose.jwk.Curve;
import com.nimbusds.jose.jwk.ECKey;
import com.nimbusds.jose.jwk.JWK;
import com.nimbusds.jose.jwk.JWKSet;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Builds and decrypts legacy version-one exchange configuration envelopes.
 *
 * <p>The envelope is the general JSON serialization from RFC 7516 with a
 * non-JOSE top-level {@code version} marker retained for the legacy exchange
 * reader. Nimbus's multi-recipient JWE provider supplies one shared content
 * encryption key and an ECDH-wrapped copy for each participant.</p>
 */
public final class ExchangeJwe implements Serializable {
    private static final long serialVersionUID = 1L;

    /** Legacy exchange envelope version. */
    public static final int VERSION = 1;

    /** Protected JWE type. */
    public static final String TYPE = "openlinktoken-exchange+jwe";

    /** Protected JWE content type. */
    public static final String CONTENT_TYPE = "application/openlinktoken-exchange+json";

    /** Protected JWE content-encryption algorithm. */
    public static final String ENCRYPTION = CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM;

    /** Per-recipient JWE key-management algorithm. */
    public static final String RECIPIENT_ALGORITHM = "ECDH-ES+A256KW";

    /** Alias matching the Python exchange helper constant. */
    public static final int EXCHANGE_JWE_VERSION = VERSION;

    /** Alias matching the Python exchange helper constant. */
    public static final String EXCHANGE_JWE_TYPE = TYPE;

    /** Alias matching the Python exchange helper constant. */
    public static final String EXCHANGE_JWE_CONTENT_TYPE = CONTENT_TYPE;

    /** Alias matching the Python exchange helper constant. */
    public static final String EXCHANGE_JWE_ENCRYPTION = ENCRYPTION;

    /** Alias matching the Python exchange helper constant. */
    public static final String EXCHANGE_JWE_RECIPIENT_ALGORITHM = RECIPIENT_ALGORITHM;

    private static final String BASE64URL_ENCODING = "base64url";
    private static final JWEAlgorithm RECIPIENT_JWE_ALGORITHM = JWEAlgorithm.ECDH_ES_A256KW;
    private static final TypeReference<Map<String, Object>> JSON_OBJECT_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private ExchangeJwe() {
    }

    /**
     * Builds an exchange envelope using the default legacy payload options.
     *
     * @param exchangeName exchange name
     * @param hashingSecret raw hashing secret bytes
     * @param senderPublicPem sender public EC key PEM
     * @param recipientPublicPem recipient public EC key PEM
     * @param curve Open Link Token curve name
     * @param createdAt exchange creation timestamp
     * @param exchangeId stable exchange identifier
     * @return a mutable JSON-compatible general JWE object
     */
    public static Map<String, Object> buildExchangeEnvelope(
            String exchangeName,
            byte[] hashingSecret,
            byte[] senderPublicPem,
            byte[] recipientPublicPem,
            String curve,
            String createdAt,
            String exchangeId) {
        return buildExchangeEnvelope(
                exchangeName,
                hashingSecret,
                senderPublicPem,
                recipientPublicPem,
                curve,
                createdAt,
                exchangeId,
                new byte[0],
                0,
                0.05,
                List.of(),
                CryptoSuite.defaultSuite());
    }

    /**
     * Builds an exchange envelope with explicit payload options.
     *
     * @param exchangeName exchange name
     * @param hashingSecret raw hashing secret bytes
     * @param senderPublicPem sender public EC key PEM
     * @param recipientPublicPem recipient public EC key PEM
     * @param curve Open Link Token curve name
     * @param createdAt exchange creation timestamp
     * @param exchangeId stable exchange identifier
     * @param rotationIv raw rotation-matrix initialization vector
     * @param rotationCount number of rotation matrices
     * @param binWidth rotation quantization bin width
     * @param dimensionBias rotation dimension bias values
     * @return a mutable JSON-compatible general JWE object
     */
    public static Map<String, Object> buildExchangeEnvelope(
            String exchangeName,
            byte[] hashingSecret,
            byte[] senderPublicPem,
            byte[] recipientPublicPem,
            String curve,
            String createdAt,
            String exchangeId,
            byte[] rotationIv,
            int rotationCount,
            double binWidth,
            List<Double> dimensionBias) {
        return buildExchangeEnvelope(
                exchangeName,
                hashingSecret,
                senderPublicPem,
                recipientPublicPem,
                curve,
                createdAt,
                exchangeId,
                rotationIv,
                rotationCount,
                binWidth,
                dimensionBias,
                CryptoSuite.defaultSuite());
    }

    /**
     * Builds a two-recipient legacy exchange envelope.
     *
     * <p>Version-one envelopes intentionally accept only the registered
     * default suite. The suite is not encoded in the unauthenticated
     * top-level marker, so accepting another suite would make the marker
     * ambiguous to legacy consumers.</p>
     *
     * @param exchangeName exchange name
     * @param hashingSecret raw hashing secret bytes
     * @param senderPublicPem sender public EC key PEM
     * @param recipientPublicPem recipient public EC key PEM
     * @param curve Open Link Token curve name
     * @param createdAt exchange creation timestamp
     * @param exchangeId stable exchange identifier
     * @param rotationIv raw rotation-matrix initialization vector
     * @param rotationCount number of rotation matrices
     * @param binWidth rotation quantization bin width
     * @param dimensionBias rotation dimension bias values
     * @param cryptoSuite requested crypto suite
     * @return a mutable JSON-compatible general JWE object
     * @throws ExchangeJweException if the arguments or suite are invalid
     */
    public static Map<String, Object> buildExchangeEnvelope(
            String exchangeName,
            byte[] hashingSecret,
            byte[] senderPublicPem,
            byte[] recipientPublicPem,
            String curve,
            String createdAt,
            String exchangeId,
            byte[] rotationIv,
            int rotationCount,
            double binWidth,
            List<Double> dimensionBias,
            CryptoSuite cryptoSuite) {
        requireDefaultSuite(cryptoSuite);
        ExchangePayload payload = new ExchangePayload(
                requireText(exchangeName, "exchangeName"),
                requireBytes(hashingSecret, "hashingSecret", true),
                requireBytes(senderPublicPem, "senderPublicPem", true),
                requireBytes(recipientPublicPem, "recipientPublicPem", true),
                requireText(curve, "curve"),
                requireText(createdAt, "createdAt"),
                requireText(exchangeId, "exchangeId"),
                rotationIv == null ? new byte[0] : rotationIv,
                rotationCount,
                binWidth,
                dimensionBias == null ? List.of() : dimensionBias);
        return encryptPayload(payload);
    }

    /**
     * Decrypts a JSON-compatible legacy exchange envelope.
     *
     * @param exchangeConfig general JWE object including top-level version
     * @param privatePem recipient private EC key PEM
     * @return decrypted UTF-8 payload JSON bytes
     * @throws ExchangeJweException if the envelope is malformed, unsupported,
     *         or cannot be decrypted by the private key
     */
    public static byte[] decryptExchangeEnvelope(Map<String, ?> exchangeConfig, byte[] privatePem) {
        Map<String, Object> envelope = copyObject(exchangeConfig, "exchangeConfig");
        validateVersion(envelope);
        JWEObjectJSON jwe = parseJwe(envelope);
        validateJwe(jwe);

        ECPrivateKey privateKey = EcKeyUtils.privateKeyFromPem(requireBytes(privatePem, "privatePem", true));
        String curve = EcKeyUtils.curveName(privateKey);
        byte[] publicPem = EcKeyUtils.derivePublicKeyFromPrivatePem(privatePem);
        String kid = EcKeyUtils.fingerprintToKid(EcKeyUtils.publicKeyFingerprint(publicPem));
        ECKey privateJwk = new ECKey.Builder(Curve.parse(curve), EcKeyUtils.publicKeyFromPem(publicPem))
                .privateKey(privateKey)
                .algorithm(RECIPIENT_JWE_ALGORITHM)
                .keyID(kid)
                .build();

        try {
            jwe.decrypt(new MultiDecrypter(privateJwk));
            byte[] payload = jwe.getPayload().toBytes();
            parseExchangePayload(payload);
            return payload;
        } catch (JOSEException | RuntimeException exception) {
            if (exception instanceof ExchangeJweException exchangeJweException) {
                throw exchangeJweException;
            }
            throw new ExchangeJweException("Unable to decrypt exchange envelope.", exception);
        }
    }

    /**
     * Decrypts a UTF-8 JSON legacy exchange envelope.
     *
     * @param exchangeConfig UTF-8 JSON object including top-level version
     * @param privatePem recipient private EC key PEM
     * @return decrypted UTF-8 payload JSON bytes
     */
    public static byte[] decryptExchangeEnvelope(byte[] exchangeConfig, byte[] privatePem) {
        Map<String, Object> envelope;
        try {
            envelope = readJsonObject(exchangeConfig);
        } catch (RuntimeException exception) {
            throw new ExchangeJweException("Exchange envelope is not valid JSON.", exception);
        }
        return decryptExchangeEnvelope(envelope, privatePem);
    }

    /**
     * Decrypts and parses a typed exchange payload.
     *
     * @param exchangeConfig general JWE object including top-level version
     * @param privatePem recipient private EC key PEM
     * @return the validated exchange payload
     */
    public static ExchangePayload decryptExchangePayload(Map<String, ?> exchangeConfig, byte[] privatePem) {
        return parseExchangePayload(decryptExchangeEnvelope(exchangeConfig, privatePem));
    }

    /**
     * Decrypts and parses a UTF-8 JSON legacy exchange envelope.
     *
     * @param exchangeConfig UTF-8 JSON object including top-level version
     * @param privatePem recipient private EC key PEM
     * @return the validated exchange payload
     */
    public static ExchangePayload decryptExchangePayload(byte[] exchangeConfig, byte[] privatePem) {
        return parseExchangePayload(decryptExchangeEnvelope(exchangeConfig, privatePem));
    }

    /**
     * Parses and validates a decrypted exchange payload.
     *
     * @param payloadJson UTF-8 JSON payload bytes
     * @return the validated typed payload
     */
    public static ExchangePayload parseExchangePayload(byte[] payloadJson) {
        Map<String, Object> payload = readJsonObject(payloadJson);
        return payloadFromMapping(payload);
    }

    /**
     * Encrypts a validated exchange payload for its sender and recipient.
     *
     * @param payload exchange payload to encrypt
     * @return the serialized general JWE envelope
     */
    private static Map<String, Object> encryptPayload(ExchangePayload payload) {
        ECPublicKey senderPublicKey = EcKeyUtils.publicKeyFromPem(payload.senderPublicPem());
        ECPublicKey recipientPublicKey = EcKeyUtils.publicKeyFromPem(payload.recipientPublicPem());
        validateCurve(payload.curve(), senderPublicKey, recipientPublicKey);

        JWEHeader protectedHeader = new JWEHeader.Builder(EncryptionMethod.A256GCM)
                .type(new JOSEObjectType(TYPE))
                .contentType(CONTENT_TYPE)
                .build();
        JWK senderJwk = toRecipientJwk(senderPublicKey, payload.senderPublicPem());
        JWK recipientJwk = toRecipientJwk(recipientPublicKey, payload.recipientPublicPem());

        try {
            JWEObjectJSON jwe = new JWEObjectJSON(
                    protectedHeader,
                    new Payload(writeJsonObject(payloadToMapping(payload))));
            jwe.encrypt(new MultiEncrypter(new JWKSet(List.of(senderJwk, recipientJwk))));
            Map<String, Object> envelope = new LinkedHashMap<>(jwe.toGeneralJSONObject());
            envelope.put("version", VERSION);
            return envelope;
        } catch (JOSEException exception) {
            throw new ExchangeJweException("Unable to encrypt exchange envelope.", exception);
        }
    }

    private static JWK toRecipientJwk(ECPublicKey publicKey, byte[] publicPem) {
        String kid = EcKeyUtils.fingerprintToKid(EcKeyUtils.publicKeyFingerprint(publicPem));
        return new ECKey.Builder(Curve.parse(EcKeyUtils.curveName(publicKey)), publicKey)
                .algorithm(RECIPIENT_JWE_ALGORITHM)
                .keyID(kid)
                .build();
    }

    private static JWEObjectJSON parseJwe(Map<String, Object> envelope) {
        Map<String, Object> joseObject = new LinkedHashMap<>(envelope);
        joseObject.remove("version");
        try {
            return JWEObjectJSON.parse(joseObject);
        } catch (ParseException | RuntimeException exception) {
            throw new ExchangeJweException("Exchange envelope is not a valid general JWE JSON object.", exception);
        }
    }

    private static void validateJwe(JWEObjectJSON jwe) {
        JWEHeader header = jwe.getHeader();
        if (header.getType() == null || !TYPE.equals(header.getType().getType())) {
            throw new ExchangeJweException("Exchange envelope has an unsupported protected typ.");
        }
        if (!CONTENT_TYPE.equals(header.getContentType())) {
            throw new ExchangeJweException("Exchange envelope has an unsupported protected cty.");
        }
        if (!EncryptionMethod.A256GCM.equals(header.getEncryptionMethod())) {
            throw new ExchangeJweException("Exchange envelope must use A256GCM.");
        }
        if (header.getAlgorithm() != null) {
            throw new ExchangeJweException("Exchange envelope must keep alg in each recipient header.");
        }
        if (jwe.getRecipients().size() != 2) {
            throw new ExchangeJweException("Exchange envelope must contain exactly two recipients.");
        }
        if (jwe.getIV() == null || jwe.getCipherText() == null || jwe.getAuthTag() == null) {
            throw new ExchangeJweException("Exchange envelope is missing encrypted JWE parts.");
        }
        for (JWEObjectJSON.Recipient recipient : jwe.getRecipients()) {
            if (recipient.getUnprotectedHeader() == null) {
                throw new ExchangeJweException("Exchange recipient is missing its header.");
            }
            JWEHeader recipientHeader = joinRecipientHeader(header, recipient);
            if (!RECIPIENT_JWE_ALGORITHM.equals(recipientHeader.getAlgorithm())) {
                throw new ExchangeJweException("Exchange recipient must use ECDH-ES+A256KW.");
            }
            if (recipientHeader.getKeyID() == null || recipientHeader.getKeyID().isBlank()) {
                throw new ExchangeJweException("Exchange recipient is missing its kid.");
            }
            if (!(recipientHeader.getEphemeralPublicKey() instanceof ECKey)) {
                throw new ExchangeJweException("Exchange recipient is missing its EC epk.");
            }
        }
    }

    private static JWEHeader joinRecipientHeader(JWEHeader protectedHeader, JWEObjectJSON.Recipient recipient) {
        try {
            return (JWEHeader) protectedHeader.join(recipient.getUnprotectedHeader());
        } catch (ParseException | RuntimeException exception) {
            throw new ExchangeJweException("Exchange recipient header is malformed.", exception);
        }
    }

    /**
     * Converts a typed exchange payload to its JSON-compatible representation.
     *
     * @param payload validated exchange payload
     * @return payload fields ready for JSON serialization
     */
    private static Map<String, Object> payloadToMapping(ExchangePayload payload) {
        Map<String, Object> mapping = new LinkedHashMap<>();
        mapping.put("exchangeName", payload.exchangeName());
        mapping.put("hashingSecret", encodeBase64Url(payload.hashingSecret()));
        mapping.put("hashingSecretEncoding", BASE64URL_ENCODING);
        mapping.put("senderKeyFingerprint", EcKeyUtils.publicKeyFingerprint(payload.senderPublicPem()));
        mapping.put("recipientKeyFingerprint", EcKeyUtils.publicKeyFingerprint(payload.recipientPublicPem()));
        mapping.put("senderPublicKey", new String(payload.senderPublicPem(), StandardCharsets.UTF_8));
        mapping.put("recipientPublicKey", new String(payload.recipientPublicPem(), StandardCharsets.UTF_8));
        mapping.put("curve", payload.curve());
        mapping.put("createdAt", payload.createdAt());
        mapping.put("exchangeId", payload.exchangeId());
        mapping.put("rotationIv", encodeBase64Url(payload.rotationIv()));
        mapping.put("rotationIvEncoding", BASE64URL_ENCODING);
        mapping.put("rotationCount", payload.rotationCount());
        mapping.put("binWidth", payload.binWidth());
        mapping.put("dimensionBias", payload.dimensionBias());
        return mapping;
    }

    /**
     * Validates and converts decrypted JSON fields to a typed exchange payload.
     *
     * @param mapping decrypted payload fields
     * @return the validated exchange payload
     */
    private static ExchangePayload payloadFromMapping(Map<String, Object> mapping) {
        Object suite = mapping.get("cryptoSuite");
        if (suite != null && !CryptoSuite.defaultSuite().getSuiteId().equals(requireText(suite, "cryptoSuite"))) {
            throw new ExchangeJweException(
                    "Legacy version 1 exchange envelopes only support the default crypto suite '"
                            + CryptoSuite.defaultSuite().getSuiteId()
                            + "'.");
        }

        String hashingSecretEncoding = requireText(mapping.get("hashingSecretEncoding"), "hashingSecretEncoding");
        if (!BASE64URL_ENCODING.equals(hashingSecretEncoding)) {
            throw new ExchangeJweException("Unsupported hashingSecretEncoding '" + hashingSecretEncoding + "'.");
        }
        byte[] hashingSecret = decodeBase64Url(
                requireText(mapping.get("hashingSecret"), "hashingSecret"),
                "hashingSecret");
        byte[] senderPublicPem = requireText(mapping.get("senderPublicKey"), "senderPublicKey")
                .getBytes(StandardCharsets.UTF_8);
        byte[] recipientPublicPem = requireText(mapping.get("recipientPublicKey"), "recipientPublicKey")
                .getBytes(StandardCharsets.UTF_8);
        String curve = requireText(mapping.get("curve"), "curve");
        String senderFingerprint = requireText(mapping.get("senderKeyFingerprint"), "senderKeyFingerprint");
        String recipientFingerprint = requireText(mapping.get("recipientKeyFingerprint"), "recipientKeyFingerprint");
        if (!senderFingerprint.equals(EcKeyUtils.publicKeyFingerprint(senderPublicPem))
                || !recipientFingerprint.equals(EcKeyUtils.publicKeyFingerprint(recipientPublicPem))) {
            throw new ExchangeJweException("Exchange payload key fingerprints do not match their public keys.");
        }

        String rotationIvEncoding = requireText(mapping.get("rotationIvEncoding"), "rotationIvEncoding");
        if (!BASE64URL_ENCODING.equals(rotationIvEncoding)) {
            throw new ExchangeJweException("Unsupported rotationIvEncoding '" + rotationIvEncoding + "'.");
        }
        String rotationIvValue = requireTextAllowEmpty(mapping.get("rotationIv"), "rotationIv");
        byte[] rotationIv = rotationIvValue.isEmpty()
                ? new byte[0]
                : decodeBase64Url(rotationIvValue, "rotationIv");

        int rotationCount = mapping.containsKey("rotationCount")
                ? requireInteger(mapping.get("rotationCount"), "rotationCount")
                : 0;
        double binWidth = mapping.containsKey("binWidth")
                ? requireNumber(mapping.get("binWidth"), "binWidth")
                : 0.05;
        List<Double> dimensionBias = mapping.containsKey("dimensionBias")
                ? requireNumbers(mapping.get("dimensionBias"), "dimensionBias")
                : List.of();

        ExchangePayload payload = new ExchangePayload(
                requireText(mapping.get("exchangeName"), "exchangeName"),
                hashingSecret,
                senderPublicPem,
                recipientPublicPem,
                curve,
                requireText(mapping.get("createdAt"), "createdAt"),
                requireText(mapping.get("exchangeId"), "exchangeId"),
                rotationIv,
                rotationCount,
                binWidth,
                dimensionBias);
        validateCurve(
                curve,
                EcKeyUtils.publicKeyFromPem(senderPublicPem),
                EcKeyUtils.publicKeyFromPem(recipientPublicPem));
        return payload;
    }

    private static void validateVersion(Map<String, Object> envelope) {
        if (!Integer.valueOf(VERSION).equals(envelope.get("version"))) {
            throw new ExchangeJweException("Exchange envelope must declare top-level version 1.");
        }
    }

    private static void requireDefaultSuite(CryptoSuite suite) {
        CryptoSuite resolvedSuite = suite == null ? CryptoSuite.defaultSuite() : suite;
        if (!CryptoSuite.defaultSuite().getSuiteId().equals(resolvedSuite.getSuiteId())
                || resolvedSuite.getExchangeConfigVersion() != VERSION
                || !CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH.equals(resolvedSuite.getExchangeKeyAgreement())) {
            throw new ExchangeJweException(
                    "Legacy version 1 exchange envelopes only support the default crypto suite '"
                            + CryptoSuite.defaultSuite().getSuiteId()
                            + "'; suite '"
                            + resolvedSuite.getSuiteId()
                            + "' cannot be encoded.");
        }
    }

    private static void validateCurve(String curve, ECPublicKey senderPublicKey, ECPublicKey recipientPublicKey) {
        if (!EcKeyUtils.SUPPORTED_CURVES.contains(curve)) {
            throw new ExchangeJweException("Unsupported curve '" + curve + "'.");
        }
        if (!curve.equals(EcKeyUtils.curveName(senderPublicKey))
                || !curve.equals(EcKeyUtils.curveName(recipientPublicKey))) {
            throw new ExchangeJweException("Exchange public keys do not match the selected curve.");
        }
    }

    private static Map<String, Object> copyObject(Map<String, ?> value, String fieldName) {
        if (value == null) {
            throw new ExchangeJweException(fieldName + " must be a JSON object.");
        }
        Map<String, Object> copy = new LinkedHashMap<>();
        for (Map.Entry<String, ?> entry : value.entrySet()) {
            copy.put(entry.getKey(), entry.getValue());
        }
        return copy;
    }

    private static String requireText(Object value, String fieldName) {
        if (!(value instanceof String text) || text.isBlank()) {
            throw new ExchangeJweException(fieldName + " must be a non-empty string.");
        }
        return text;
    }

    private static String requireTextAllowEmpty(Object value, String fieldName) {
        if (!(value instanceof String text)) {
            throw new ExchangeJweException(fieldName + " must be a string.");
        }
        return text;
    }

    private static byte[] requireBytes(byte[] value, String fieldName, boolean nonEmpty) {
        if (value == null || (nonEmpty && value.length == 0)) {
            throw new ExchangeJweException(fieldName + " must not be empty.");
        }
        return Arrays.copyOf(value, value.length);
    }

    private static int requireInteger(Object value, String fieldName) {
        if (!(value instanceof Number number)
                || number.doubleValue() != Math.rint(number.doubleValue())
                || number.doubleValue() < Integer.MIN_VALUE
                || number.doubleValue() > Integer.MAX_VALUE) {
            throw new ExchangeJweException(fieldName + " must be an integer.");
        }
        return number.intValue();
    }

    private static double requireNumber(Object value, String fieldName) {
        if (!(value instanceof Number number) || !Double.isFinite(number.doubleValue())) {
            throw new ExchangeJweException(fieldName + " must be a finite number.");
        }
        return number.doubleValue();
    }

    private static List<Double> requireNumbers(Object value, String fieldName) {
        if (!(value instanceof List<?> values)) {
            throw new ExchangeJweException(fieldName + " must be an array of numbers.");
        }
        List<Double> result = new ArrayList<>(values.size());
        for (Object item : values) {
            result.add(requireNumber(item, fieldName));
        }
        return result;
    }

    /**
     * Typed exchange payload matching the v1 JSON payload fields.
     *
     * @param exchangeName exchange name
     * @param hashingSecret raw hashing secret bytes
     * @param senderPublicPem sender public EC key PEM
     * @param recipientPublicPem recipient public EC key PEM
     * @param curve Open Link Token curve name
     * @param createdAt exchange creation timestamp
     * @param exchangeId stable exchange identifier
     * @param rotationIv raw rotation-matrix initialization vector
     * @param rotationCount number of rotation matrices
     * @param binWidth rotation quantization bin width
     * @param dimensionBias rotation dimension bias values
     */
    public record ExchangePayload(
            String exchangeName,
            byte[] hashingSecret,
            byte[] senderPublicPem,
            byte[] recipientPublicPem,
            String curve,
            String createdAt,
            String exchangeId,
            byte[] rotationIv,
            int rotationCount,
            double binWidth,
            List<Double> dimensionBias) implements Serializable {

        /**
         * Canonicalizes mutable payload values.
         */
        public ExchangePayload {
            exchangeName = requireText(exchangeName, "exchangeName");
            hashingSecret = requireBytes(hashingSecret, "hashingSecret", true);
            senderPublicPem = requireBytes(senderPublicPem, "senderPublicPem", true);
            recipientPublicPem = requireBytes(recipientPublicPem, "recipientPublicPem", true);
            curve = requireText(curve, "curve");
            createdAt = requireText(createdAt, "createdAt");
            exchangeId = requireText(exchangeId, "exchangeId");
            rotationIv = rotationIv == null ? new byte[0] : Arrays.copyOf(rotationIv, rotationIv.length);
            dimensionBias = dimensionBias == null ? List.of() : List.copyOf(dimensionBias);
            if (rotationCount < 0) {
                throw new ExchangeJweException("rotationCount must be non-negative.");
            }
            if (!Double.isFinite(binWidth) || binWidth <= 0.0) {
                throw new ExchangeJweException("binWidth must be positive.");
            }
        }

        @Override
        public byte[] hashingSecret() {
            return Arrays.copyOf(hashingSecret, hashingSecret.length);
        }

        @Override
        public byte[] senderPublicPem() {
            return Arrays.copyOf(senderPublicPem, senderPublicPem.length);
        }

        @Override
        public byte[] recipientPublicPem() {
            return Arrays.copyOf(recipientPublicPem, recipientPublicPem.length);
        }

        @Override
        public byte[] rotationIv() {
            return Arrays.copyOf(rotationIv, rotationIv.length);
        }

        /**
         * Returns the sender public key PEM bytes under the wire-oriented name.
         *
         * @return sender public key PEM bytes
         */
        public byte[] senderPublicKey() {
            return senderPublicPem();
        }

        /**
         * Returns the recipient public key PEM bytes under the wire-oriented name.
         *
         * @return recipient public key PEM bytes
         */
        public byte[] recipientPublicKey() {
            return recipientPublicPem();
        }
    }

    /**
     * Signals malformed, unsupported, or undecryptable v1 exchange data.
     */
    public static final class ExchangeJweException extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;

        private ExchangeJweException(String message) {
            super(message);
        }

        private ExchangeJweException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /**
     * Parses UTF-8 JSON bytes as an object.
     *
     * @param json UTF-8 JSON bytes
     * @return the parsed JSON object
     * @throws IllegalArgumentException if the bytes are empty, invalid UTF-8, or not a JSON object
     */
    private static Map<String, Object> readJsonObject(byte[] json) {
        if (json == null || json.length == 0) {
            throw new IllegalArgumentException("JSON value must not be empty.");
        }
        try {
            return JSON_MAPPER.readValue(decodeUtf8(json), JSON_OBJECT_TYPE);
        } catch (IOException exception) {
            throw new IllegalArgumentException("JSON value must be an object.", exception);
        }
    }

    /**
     * Serializes a JSON-compatible mapping.
     *
     * @param value mapping to serialize
     * @return UTF-8 JSON bytes
     */
    private static byte[] writeJsonObject(Map<String, Object> value) {
        try {
            return JSON_MAPPER.writeValueAsBytes(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Unable to serialize JSON object.", exception);
        }
    }

    /**
     * Decodes JSON bytes using strict UTF-8 validation.
     *
     * @param json bytes to decode
     * @return the decoded JSON text
     * @throws IllegalArgumentException if the bytes are not valid UTF-8
     */
    private static String decodeUtf8(byte[] json) {
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(json))
                    .toString();
        } catch (CharacterCodingException exception) {
            throw new IllegalArgumentException("JSON value must be valid UTF-8.", exception);
        }
    }

    /**
     * Encodes bytes as unpadded base64url.
     *
     * @param value bytes to encode
     * @return unpadded base64url text
     */
    private static String encodeBase64Url(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    /**
     * Decodes a canonical, unpadded base64url value.
     *
     * @param value encoded value
     * @param fieldName field name used in validation errors
     * @return decoded bytes
     * @throws IllegalArgumentException if the value is empty, malformed, or non-canonical
     */
    private static byte[] decodeBase64Url(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldName + " must be a non-empty base64url string.");
        }
        try {
            byte[] decoded = Base64.getUrlDecoder().decode(value);
            if (!value.equals(encodeBase64Url(decoded))) {
                throw new IllegalArgumentException("non-canonical base64url encoding");
            }
            return decoded;
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(fieldName + " is not valid base64url data.", exception);
        }
    }
}
