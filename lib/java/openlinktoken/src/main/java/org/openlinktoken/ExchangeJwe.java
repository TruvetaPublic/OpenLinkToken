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
import java.util.Set;

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
    private static final String CRYPTO_SUITE_HEADER = "cryptoSuite";
    private static final JWEAlgorithm RECIPIENT_JWE_ALGORITHM = JWEAlgorithm.ECDH_ES_A256KW;
    private static final TypeReference<Map<String, Object>> JSON_OBJECT_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    /**
     * Creates the utility instance with no arguments.
     */
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
     * Builds a two-recipient version-one exchange envelope.
     *
     * <p>Non-default v1 suites are identified by a critical {@code cryptoSuite}
     * parameter in the authenticated protected header. The default suite keeps
     * the legacy header and payload shape.</p>
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
        CryptoSuite resolvedSuite = requireV1Suite(cryptoSuite);
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
        return encryptPayload(payload, resolvedSuite);
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
        validateJweAndResolveSuite(jwe, envelope);

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
            jwe.decrypt(new MultiDecrypter(privateJwk, Set.of(CRYPTO_SUITE_HEADER)));
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
     * Resolves the suite authenticated by an exchange envelope's protected header.
     *
     * @param exchangeConfig general JSON exchange envelope
     * @return the registered version-one ECDH suite
     */
    static CryptoSuite resolveCryptoSuite(Map<String, ?> exchangeConfig) {
        Map<String, Object> envelope = copyObject(exchangeConfig, "exchangeConfig");
        validateVersion(envelope);
        return validateJweAndResolveSuite(parseJwe(envelope), envelope);
    }

    /**
     * Encrypts a validated exchange payload for its sender and recipient.
     *
     * @param payload exchange payload to encrypt
     * @param cryptoSuite crypto suite authenticated by the protected header
     * @return the serialized general JWE envelope
     */
    private static Map<String, Object> encryptPayload(ExchangePayload payload, CryptoSuite cryptoSuite) {
        ECPublicKey senderPublicKey = EcKeyUtils.publicKeyFromPem(payload.senderPublicPem());
        ECPublicKey recipientPublicKey = EcKeyUtils.publicKeyFromPem(payload.recipientPublicPem());
        validateCurve(payload.curve(), senderPublicKey, recipientPublicKey);

        JWEHeader.Builder protectedHeaderBuilder = new JWEHeader.Builder(EncryptionMethod.A256GCM)
                .type(new JOSEObjectType(TYPE))
                .contentType(CONTENT_TYPE);
        if (!CryptoSuite.defaultSuite().equals(cryptoSuite)) {
            protectedHeaderBuilder
                    .customParam(CRYPTO_SUITE_HEADER, cryptoSuite.getSuiteId())
                    .criticalParams(Set.of(CRYPTO_SUITE_HEADER));
        }
        JWEHeader protectedHeader = protectedHeaderBuilder.build();
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

    /**
     * Creates a recipient JWK from its public key and PEM representation.
     *
     * @param publicKey EC public key
     * @param publicPem SubjectPublicKeyInfo PEM bytes
     * @return the JWK with the exchange key identifier and algorithm
     */
    private static JWK toRecipientJwk(ECPublicKey publicKey, byte[] publicPem) {
        String kid = EcKeyUtils.fingerprintToKid(EcKeyUtils.publicKeyFingerprint(publicPem));
        return new ECKey.Builder(Curve.parse(EcKeyUtils.curveName(publicKey)), publicKey)
                .algorithm(RECIPIENT_JWE_ALGORITHM)
                .keyID(kid)
                .build();
    }

    /**
     * Parses a general JWE after removing the exchange-specific version marker.
     *
     * @param envelope exchange envelope fields
     * @return the parsed general JWE object
     */
    private static JWEObjectJSON parseJwe(Map<String, Object> envelope) {
        Map<String, Object> joseObject = new LinkedHashMap<>(envelope);
        joseObject.remove("version");
        try {
            return JWEObjectJSON.parse(joseObject);
        } catch (ParseException | RuntimeException exception) {
            throw new ExchangeJweException("Exchange envelope is not a valid general JWE JSON object.", exception);
        }
    }

    /**
     * Validates the envelope structure and resolves its protected-header suite.
     *
     * @param jwe parsed general JWE object
     * @param envelope original general JSON exchange envelope
     * @return the validated crypto suite
     */
    private static CryptoSuite validateJweAndResolveSuite(JWEObjectJSON jwe, Map<String, Object> envelope) {
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
        rejectUnprotectedSuiteMarker(envelope);
        CryptoSuite cryptoSuite = resolveProtectedHeaderSuite(header);
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
        return cryptoSuite;
    }

    /**
     * Resolves and validates suite metadata from the authenticated protected header.
     *
     * @param protectedHeader authenticated JWE protected header
     * @return the registered version-one ECDH suite
     */
    private static CryptoSuite resolveProtectedHeaderSuite(JWEHeader protectedHeader) {
        Set<String> criticalParams = protectedHeader.getCriticalParams();
        if (criticalParams == null) {
            criticalParams = Set.of();
        }
        boolean hasSuiteMarker = protectedHeader.getIncludedParams().contains(CRYPTO_SUITE_HEADER);
        if (!hasSuiteMarker) {
            if (!criticalParams.isEmpty()) {
                throw new ExchangeJweException("Exchange envelope has an unsupported critical protected parameter.");
            }
            return CryptoSuite.defaultSuite();
        }

        Object suiteValue = protectedHeader.getCustomParam(CRYPTO_SUITE_HEADER);
        if (!(suiteValue instanceof String suiteId) || suiteId.isBlank()) {
            throw new ExchangeJweException("Protected-header cryptoSuite must be a non-empty string.");
        }
        if (!Set.of(CRYPTO_SUITE_HEADER).equals(criticalParams)) {
            throw new ExchangeJweException("Protected-header cryptoSuite must be the only critical parameter.");
        }

        CryptoSuite suite = CryptoSuite.fromId(suiteId);
        if (suite.getExchangeConfigVersion() != VERSION
                || !CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH.equals(suite.getExchangeKeyAgreement())) {
            throw new ExchangeJweException(
                    "Crypto suite '" + suite.getSuiteId() + "' is incompatible with version 1 ECDH exchange.");
        }
        return suite;
    }

    /**
     * Rejects suite markers placed in unauthenticated headers; returns no value.
     *
     * @param envelope general JSON exchange envelope
     */
    private static void rejectUnprotectedSuiteMarker(Map<String, Object> envelope) {
        if (containsSuiteMarker(envelope.get("unprotected"))) {
            throw new ExchangeJweException("Version 1 cryptoSuite must appear only in the protected header.");
        }

        Object recipientsValue = envelope.get("recipients");
        if (recipientsValue instanceof List<?> recipients) {
            for (Object recipientValue : recipients) {
                if (recipientValue instanceof Map<?, ?> recipient
                        && containsSuiteMarker(recipient.get("header"))) {
                    throw new ExchangeJweException("Version 1 cryptoSuite must appear only in the protected header.");
                }
            }
        }
    }

    /**
     * Checks whether a header value contains the suite marker.
     *
     * @param value candidate JOSE header value
     * @return {@code true} if the value is a mapping that contains {@code cryptoSuite}
     */
    private static boolean containsSuiteMarker(Object value) {
        return value instanceof Map<?, ?> header && header.containsKey(CRYPTO_SUITE_HEADER);
    }

    /**
     * Joins a recipient header with its authenticated protected header.
     *
     * @param protectedHeader authenticated protected JWE header
     * @param recipient general-JWE recipient
     * @return the joined recipient header
     */
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
        if (mapping.containsKey(CRYPTO_SUITE_HEADER)) {
            throw new ExchangeJweException(
                    "Version 1 exchange payload must not contain cryptoSuite; suite selection belongs in the protected header.");
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

    /**
     * Requires the legacy top-level exchange version marker.
     *
     * <p>This method returns no value.</p>
     *
     * @param envelope exchange envelope fields
     */
    private static void validateVersion(Map<String, Object> envelope) {
        if (!Integer.valueOf(VERSION).equals(envelope.get("version"))) {
            throw new ExchangeJweException("Exchange envelope must declare top-level version 1.");
        }
    }

    /**
     * Resolves a requested suite to its registered version-one ECDH definition.
     *
     * @param suite requested suite, or {@code null} to select the default
     * @return the registered version-one ECDH suite
     */
    private static CryptoSuite requireV1Suite(CryptoSuite suite) {
        CryptoSuite selectedSuite = suite == null
                ? CryptoSuite.defaultSuite()
                : CryptoSuite.fromId(suite.getSuiteId());
        if (selectedSuite.getExchangeConfigVersion() != VERSION
                || !CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH.equals(selectedSuite.getExchangeKeyAgreement())) {
            throw new ExchangeJweException(
                    "Version 1 exchange envelopes require a registered v1 ECDH suite; suite '"
                            + selectedSuite.getSuiteId()
                            + "' cannot be encoded.");
        }
        return selectedSuite;
    }

    /**
     * Validates that both public keys use the selected supported curve.
     *
     * <p>This method returns no value.</p>
     *
     * @param curve Open Link Token curve name
     * @param senderPublicKey sender EC public key
     * @param recipientPublicKey recipient EC public key
     */
    private static void validateCurve(String curve, ECPublicKey senderPublicKey, ECPublicKey recipientPublicKey) {
        if (!EcKeyUtils.SUPPORTED_CURVES.contains(curve)) {
            throw new ExchangeJweException("Unsupported curve '" + curve + "'.");
        }
        if (!curve.equals(EcKeyUtils.curveName(senderPublicKey))
                || !curve.equals(EcKeyUtils.curveName(recipientPublicKey))) {
            throw new ExchangeJweException("Exchange public keys do not match the selected curve.");
        }
    }

    /**
     * Validates and shallow-copies a JSON object mapping.
     *
     * @param value source mapping
     * @param fieldName field name used in validation errors
     * @return a mutable copy of the mapping
     */
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

    /**
     * Requires a non-empty text value.
     *
     * @param value candidate value
     * @param fieldName field name used in validation errors
     * @return the validated text
     */
    private static String requireText(Object value, String fieldName) {
        if (!(value instanceof String text) || text.isBlank()) {
            throw new ExchangeJweException(fieldName + " must be a non-empty string.");
        }
        return text;
    }

    /**
     * Requires a text value while allowing it to be empty.
     *
     * @param value candidate value
     * @param fieldName field name used in validation errors
     * @return the validated text
     */
    private static String requireTextAllowEmpty(Object value, String fieldName) {
        if (!(value instanceof String text)) {
            throw new ExchangeJweException(fieldName + " must be a string.");
        }
        return text;
    }

    /**
     * Validates and defensively copies byte-array input.
     *
     * @param value candidate bytes
     * @param fieldName field name used in validation errors
     * @param nonEmpty whether the value must contain at least one byte
     * @return a defensive copy of the validated bytes
     */
    private static byte[] requireBytes(byte[] value, String fieldName, boolean nonEmpty) {
        if (value == null || (nonEmpty && value.length == 0)) {
            throw new ExchangeJweException(fieldName + " must not be empty.");
        }
        return Arrays.copyOf(value, value.length);
    }

    /**
     * Requires an integral numeric value within the integer range.
     *
     * @param value candidate value
     * @param fieldName field name used in validation errors
     * @return the validated integer
     */
    private static int requireInteger(Object value, String fieldName) {
        if (!(value instanceof Number number)
                || number.doubleValue() != Math.rint(number.doubleValue())
                || number.doubleValue() < Integer.MIN_VALUE
                || number.doubleValue() > Integer.MAX_VALUE) {
            throw new ExchangeJweException(fieldName + " must be an integer.");
        }
        return number.intValue();
    }

    /**
     * Requires a finite numeric value.
     *
     * @param value candidate value
     * @param fieldName field name used in validation errors
     * @return the validated finite number
     */
    private static double requireNumber(Object value, String fieldName) {
        if (!(value instanceof Number number) || !Double.isFinite(number.doubleValue())) {
            throw new ExchangeJweException(fieldName + " must be a finite number.");
        }
        return number.doubleValue();
    }

    /**
     * Requires a list whose elements are finite numbers.
     *
     * @param value candidate list
     * @param fieldName field name used in validation errors
     * @return the validated numeric values
     */
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
         * Constructs and validates an exchange payload, copying mutable values.
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
         * @param dimensionBias rotation dimension-bias values
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

        /**
         * Returns a defensive copy of the hashing secret.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the raw hashing secret bytes
         */
        @Override
        public byte[] hashingSecret() {
            return Arrays.copyOf(hashingSecret, hashingSecret.length);
        }

        /**
         * Returns a defensive copy of the sender public-key PEM.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the sender SubjectPublicKeyInfo PEM bytes
         */
        @Override
        public byte[] senderPublicPem() {
            return Arrays.copyOf(senderPublicPem, senderPublicPem.length);
        }

        /**
         * Returns a defensive copy of the recipient public-key PEM.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the recipient SubjectPublicKeyInfo PEM bytes
         */
        @Override
        public byte[] recipientPublicPem() {
            return Arrays.copyOf(recipientPublicPem, recipientPublicPem.length);
        }

        /**
         * Returns a defensive copy of the rotation IV.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the raw rotation initialization vector
         */
        @Override
        public byte[] rotationIv() {
            return Arrays.copyOf(rotationIv, rotationIv.length);
        }

        /**
         * Returns the sender public key PEM bytes under the wire-oriented name.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return sender public key PEM bytes
         */
        public byte[] senderPublicKey() {
            return senderPublicPem();
        }

        /**
         * Returns the recipient public key PEM bytes under the wire-oriented name.
         *
         * <p>This method accepts no arguments.</p>
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

        /**
         * Creates an exchange exception with a detail message.
         *
         * @param message exception detail message
         */
        private ExchangeJweException(String message) {
            super(message);
        }

        /**
         * Creates an exchange exception with a detail message and cause.
         *
         * @param message exception detail message
         * @param cause underlying cause
         */
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
