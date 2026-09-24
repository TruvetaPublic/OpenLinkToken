/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.IOException;
import java.io.Serializable;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import javax.crypto.KeyAgreement;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.bouncycastle.crypto.digests.SHA256Digest;
import org.bouncycastle.crypto.generators.HKDFBytesGenerator;
import org.bouncycastle.crypto.params.HKDFParameters;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Loads, validates, decrypts, and resolves exchange configuration envelopes.
 *
 * <p>This class intentionally only handles caller-supplied values. It does not
 * select default paths, inspect the environment, parse command-line options, or
 * resolve private keys from disk.</p>
 */
public final class ExchangeConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    /** Legacy exchange configuration version. */
    public static final int VERSION_ONE = 1;

    /** Post-quantum exchange configuration version. */
    public static final int VERSION_TWO = 2;

    /** HKDF domain-separation label for the legacy token transport key. */
    public static final String TRANSPORT_KEY_INFO = "openlinktoken:token-encryption:v1";

    private static final String BASE64URL_ENCODING = "base64url";
    private static final Path PROVIDED_CONFIG_PATH = Path.of("<provided exchange config>");
    private static final TypeReference<Map<String, Object>> JSON_OBJECT_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
    private static final Set<String> V2_REQUIRED_PROTECTED_FIELDS = Set.of(
            "typ",
            "cty",
            "enc",
            "version",
            "cryptoSuite",
            "exchangeId");

    private ExchangeConfig() {
    }

    /**
     * Loads an exchange configuration from a caller-provided path.
     *
     * @param path the JSON file path
     * @return the validated, versioned envelope
     */
    public static LoadedExchangeConfig loadExchangeConfig(Path path) {
        Objects.requireNonNull(path, "Exchange config path must not be null.");
        try {
            return loadExchangeConfig(Files.readAllBytes(path), path);
        } catch (IOException exception) {
            throw new IllegalArgumentException("Unable to read exchange config '" + path + "'.", exception);
        }
    }

    /**
     * Loads an exchange configuration from UTF-8 JSON bytes.
     *
     * @param json UTF-8 JSON object bytes
     * @return the validated, versioned envelope
     */
    public static LoadedExchangeConfig loadExchangeConfig(byte[] json) {
        return loadExchangeConfig(json, PROVIDED_CONFIG_PATH);
    }

    /**
     * Loads an exchange configuration from a JSON string.
     *
     * @param json JSON object text
     * @return the validated, versioned envelope
     */
    public static LoadedExchangeConfig loadExchangeConfig(String json) {
        if (json == null) {
            throw new IllegalArgumentException("Exchange config JSON must not be null.");
        }
        return loadExchangeConfig(json.getBytes(StandardCharsets.UTF_8), PROVIDED_CONFIG_PATH);
    }

    /**
     * Loads an exchange configuration from a JSON-compatible mapping.
     *
     * @param config JSON object values
     * @return the validated, versioned envelope
     */
    public static LoadedExchangeConfig loadExchangeConfig(Map<String, ?> config) {
        return loadExchangeConfig(config, PROVIDED_CONFIG_PATH);
    }

    /**
     * Resolves a version-one envelope with an EC private-key PEM.
     *
     * @param exchangeConfig loaded exchange configuration
     * @param privateKeyPem unencrypted PKCS#8 EC private-key PEM
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(
            LoadedExchangeConfig exchangeConfig,
            byte[] privateKeyPem) {
        requireVersion(exchangeConfig, VERSION_ONE, "EC private-key PEM");
        byte[] privatePem = requireBytes(privateKeyPem, "privateKeyPem", true);
        byte[] plaintext;
        try {
            plaintext = ExchangeJwe.decryptExchangeEnvelope(exchangeConfig.config(), privatePem);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException(
                    "Failed to decrypt exchange config '" + exchangeConfig.path() + "'.",
                    exception);
        }

        Map<String, Object> payload = readJsonObject(plaintext);
        CryptoSuite cryptoSuite = ExchangeJwe.resolveCryptoSuite(exchangeConfig.config());
        DecodedPayload decoded = decodePayload(payload, VERSION_ONE, cryptoSuite);
        String role = resolveV1Role(privatePem, payload);
        return new ResolvedExchangeConfig(
                exchangeConfig.path(),
                VERSION_ONE,
                exchangeConfig.config(),
                payload,
                privatePem,
                null,
                role,
                decoded.cryptoSuite(),
                decoded.hashingSecret(),
                decoded.rotationIv(),
                decoded.rotationCount(),
                decoded.binWidth(),
                decoded.dimensionBias(),
                null);
    }

    /**
     * Resolves a version-two envelope with a private exchange key bundle.
     *
     * @param exchangeConfig loaded exchange configuration
     * @param privateBundle private exchange key bundle
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(
            LoadedExchangeConfig exchangeConfig,
            ExchangeKeyBundle privateBundle) {
        requireVersion(exchangeConfig, VERSION_TWO, "private ExchangeKeyBundle");
        if (privateBundle == null || !privateBundle.hasPrivateMaterial()) {
            throw new IllegalArgumentException(
                    "Version-two exchange resolution requires a private ExchangeKeyBundle.");
        }

        ExchangeKem.DecryptionResult decryption;
        try {
            decryption = ExchangeKem.decryptExchangeEnvelopeV2(exchangeConfig.config(), privateBundle);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException(
                    "Failed to decrypt exchange config '" + exchangeConfig.path() + "'.",
                    exception);
        }

        Map<String, Object> payload = readJsonObject(decryption.getPlaintext());
        DecodedPayload decoded = decodePayload(payload, VERSION_TWO);
        String role = resolveV2Role(privateBundle, payload);
        return new ResolvedExchangeConfig(
                exchangeConfig.path(),
                VERSION_TWO,
                exchangeConfig.config(),
                payload,
                null,
                privateBundle,
                role,
                decoded.cryptoSuite(),
                decoded.hashingSecret(),
                decoded.rotationIv(),
                decoded.rotationCount(),
                decoded.binWidth(),
                decoded.dimensionBias(),
                decryption.getTransportKey());
    }

    /**
     * Resolves a version-one envelope from a caller-provided path.
     *
     * @param path exchange configuration path
     * @param privateKeyPem unencrypted PKCS#8 EC private-key PEM
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(Path path, byte[] privateKeyPem) {
        return resolveExchangeConfig(loadExchangeConfig(path), privateKeyPem);
    }

    /**
     * Resolves a version-two envelope from a caller-provided path.
     *
     * @param path exchange configuration path
     * @param privateBundle private exchange key bundle
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(Path path, ExchangeKeyBundle privateBundle) {
        return resolveExchangeConfig(loadExchangeConfig(path), privateBundle);
    }

    /**
     * Resolves a version-one envelope from UTF-8 JSON bytes.
     *
     * @param json exchange configuration JSON bytes
     * @param privateKeyPem unencrypted PKCS#8 EC private-key PEM
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(byte[] json, byte[] privateKeyPem) {
        return resolveExchangeConfig(loadExchangeConfig(json), privateKeyPem);
    }

    /**
     * Resolves a version-two envelope from UTF-8 JSON bytes.
     *
     * @param json exchange configuration JSON bytes
     * @param privateBundle private exchange key bundle
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(byte[] json, ExchangeKeyBundle privateBundle) {
        return resolveExchangeConfig(loadExchangeConfig(json), privateBundle);
    }

    /**
     * Resolves a version-one envelope from JSON text.
     *
     * @param json exchange configuration JSON text
     * @param privateKeyPem unencrypted PKCS#8 EC private-key PEM
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(String json, byte[] privateKeyPem) {
        return resolveExchangeConfig(loadExchangeConfig(json), privateKeyPem);
    }

    /**
     * Resolves a version-two envelope from JSON text.
     *
     * @param json exchange configuration JSON text
     * @param privateBundle private exchange key bundle
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(String json, ExchangeKeyBundle privateBundle) {
        return resolveExchangeConfig(loadExchangeConfig(json), privateBundle);
    }

    /**
     * Resolves a version-one envelope from a JSON-compatible mapping.
     *
     * @param config exchange configuration object
     * @param privateKeyPem unencrypted PKCS#8 EC private-key PEM
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(
            Map<String, ?> config,
            byte[] privateKeyPem) {
        return resolveExchangeConfig(loadExchangeConfig(config), privateKeyPem);
    }

    /**
     * Resolves a version-two envelope from a JSON-compatible mapping.
     *
     * @param config exchange configuration object
     * @param privateBundle private exchange key bundle
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveExchangeConfig(
            Map<String, ?> config,
            ExchangeKeyBundle privateBundle) {
        return resolveExchangeConfig(loadExchangeConfig(config), privateBundle);
    }

    /**
     * Alias for resolving an already loaded version-one envelope.
     *
     * @param exchangeConfig loaded exchange configuration
     * @param privateKeyPem unencrypted PKCS#8 EC private-key PEM
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveLoadedExchangeConfig(
            LoadedExchangeConfig exchangeConfig,
            byte[] privateKeyPem) {
        return resolveExchangeConfig(exchangeConfig, privateKeyPem);
    }

    /**
     * Alias for resolving an already loaded version-two envelope.
     *
     * @param exchangeConfig loaded exchange configuration
     * @param privateBundle private exchange key bundle
     * @return the decrypted and validated exchange state
     */
    public static ResolvedExchangeConfig resolveLoadedExchangeConfig(
            LoadedExchangeConfig exchangeConfig,
            ExchangeKeyBundle privateBundle) {
        return resolveExchangeConfig(exchangeConfig, privateBundle);
    }

    /**
     * Derives the token transport key for a resolved exchange.
     *
     * <p>Version two returns the authenticated key produced by
     * {@link ExchangeKem}. Version one derives the shared ECDH secret and
     * expands it with HKDF-SHA256.</p>
     *
     * @param exchange resolved exchange configuration
     * @return a defensive copy of the 32-byte transport key
     */
    public static byte[] deriveTransportEncryptionKey(ResolvedExchangeConfig exchange) {
        Objects.requireNonNull(exchange, "Resolved exchange config must not be null.");
        byte[] storedTransportKey = exchange.storedTransportEncryptionKey();
        if (exchange.version() == VERSION_TWO) {
            if (storedTransportKey == null || storedTransportKey.length != 32) {
                throw new IllegalArgumentException(
                        "Version-two exchange config did not provide a 32-byte transport encryption key.");
            }
            return storedTransportKey;
        }
        if (exchange.version() != VERSION_ONE) {
            throw new IllegalArgumentException("Unsupported exchange config version.");
        }

        byte[] privatePem = exchange.privateKeyPem();
        if (privatePem == null) {
            throw new IllegalArgumentException("Version-one exchange config is missing its private key PEM.");
        }
        String otherPublicKey = "sender".equals(exchange.privateKeyRole())
                ? requireText(exchange.payload().get("recipientPublicKey"), "recipientPublicKey")
                : requireText(exchange.payload().get("senderPublicKey"), "senderPublicKey");
        String exchangeId = requireText(exchange.payload().get("exchangeId"), "exchangeId");

        try {
            ECPrivateKey privateKey = EcKeyUtils.privateKeyFromPem(privatePem);
            ECPublicKey publicKey = EcKeyUtils.publicKeyFromPem(otherPublicKey.getBytes(StandardCharsets.UTF_8));
            KeyAgreement agreement = KeyAgreement.getInstance("ECDH");
            agreement.init(privateKey);
            agreement.doPhase(publicKey, true);
            byte[] sharedSecret = agreement.generateSecret();
            return hkdfSha256(
                    sharedSecret,
                    exchangeId.getBytes(StandardCharsets.UTF_8),
                    TRANSPORT_KEY_INFO.getBytes(StandardCharsets.US_ASCII));
        } catch (GeneralSecurityException | RuntimeException exception) {
            throw new IllegalArgumentException("Failed to derive the transport encryption key.", exception);
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

    private static LoadedExchangeConfig loadExchangeConfig(byte[] json, Path path) {
        Map<String, Object> config = readJsonObject(json);
        return loadExchangeConfig(config, path);
    }

    private static LoadedExchangeConfig loadExchangeConfig(Map<String, ?> config, Path path) {
        Map<String, Object> copy = copyJsonMap(config, "exchangeConfig");
        int version = detectVersion(copy);
        return new LoadedExchangeConfig(path, version, copy);
    }

    private static int detectVersion(Map<String, Object> config) {
        Object topLevelVersion = config.get("version");
        if (numericEquals(topLevelVersion, VERSION_ONE)) {
            rejectAmbiguousVersionOne(config);
            return VERSION_ONE;
        }
        if (numericEquals(topLevelVersion, VERSION_TWO)) {
            throw new IllegalArgumentException(
                    "Version-two exchange configs must authenticate version in the protected header.");
        }
        if (topLevelVersion != null) {
            throw new IllegalArgumentException(
                    "Unsupported exchange config version '" + topLevelVersion + "'. Supported versions: 1, 2.");
        }

        Map<String, Object> protectedHeader = decodeProtectedHeader(config.get("protected"));
        for (String field : V2_REQUIRED_PROTECTED_FIELDS) {
            if (!protectedHeader.containsKey(field)) {
                throw new IllegalArgumentException("Version-two protected header is missing field '" + field + "'.");
            }
        }
        if (!numericEquals(protectedHeader.get("version"), VERSION_TWO)) {
            throw new IllegalArgumentException(
                    "Exchange config must declare top-level version 1 or protected version 2.");
        }
        validateProtectedHeader(protectedHeader);
        return VERSION_TWO;
    }

    private static void rejectAmbiguousVersionOne(Map<String, Object> config) {
        Object protectedValue = config.get("protected");
        if (!(protectedValue instanceof String value) || value.isEmpty()) {
            return;
        }
        try {
            Map<String, Object> protectedHeader = decodeProtectedHeader(value);
            if (protectedHeader.containsKey("version")
                    && !numericEquals(protectedHeader.get("version"), VERSION_ONE)) {
                throw new IllegalArgumentException(
                        "Exchange config contains both top-level version 1 and a protected version marker.");
            }
        } catch (IllegalArgumentException exception) {
            if (exception.getMessage() != null
                    && exception.getMessage().startsWith("Exchange config contains both")) {
                throw exception;
            }
        }
    }

    /**
     * Decodes and parses a protected-header value from an exchange configuration.
     *
     * @param value configured protected-header value
     * @return the parsed protected-header object
     * @throws IllegalArgumentException if the value is missing or is not valid base64url JSON
     */
    private static Map<String, Object> decodeProtectedHeader(Object value) {
        if (!(value instanceof String protectedValue) || protectedValue.isEmpty()) {
            throw new IllegalArgumentException("Exchange config is missing its protected header.");
        }
        try {
            return readJsonObject(decodeBase64Url(protectedValue, "protected"));
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException(
                    "Exchange config protected header is not valid base64url JSON.",
                    exception);
        }
    }

    private static void validateProtectedHeader(Map<String, Object> protectedHeader) {
        if (!ExchangeKem.TYPE.equals(protectedHeader.get("typ"))) {
            throw new IllegalArgumentException("Version-two protected header has an unsupported typ.");
        }
        if (!ExchangeKem.CONTENT_TYPE.equals(protectedHeader.get("cty"))) {
            throw new IllegalArgumentException("Version-two protected header has an unsupported cty.");
        }
        if (!ExchangeKem.ENCRYPTION.equals(protectedHeader.get("enc"))) {
            throw new IllegalArgumentException("Version-two protected header must use A256GCM.");
        }
        if (!(protectedHeader.get("cryptoSuite") instanceof String suite)
                || suite.isEmpty()) {
            throw new IllegalArgumentException("Version-two protected header cryptoSuite must be a string.");
        }
        if (!(protectedHeader.get("exchangeId") instanceof String exchangeId)
                || exchangeId.isEmpty()) {
            throw new IllegalArgumentException(
                    "Version-two protected header exchangeId must be a non-empty string.");
        }
    }

    private static DecodedPayload decodePayload(Map<String, Object> payload, int version) {
        return decodePayload(payload, version, null);
    }

    private static DecodedPayload decodePayload(
            Map<String, Object> payload, int version, CryptoSuite protectedV1Suite) {
        if (payload == null) {
            throw new IllegalArgumentException("Exchange config decrypted to an invalid payload.");
        }

        CryptoSuite suite = resolvePayloadSuite(payload, version, protectedV1Suite);
        requireText(payload.get("exchangeName"), "exchangeName");
        requireText(payload.get("createdAt"), "createdAt");
        requireText(payload.get("exchangeId"), "exchangeId");
        if (version == VERSION_TWO) {
            requireText(payload.get("senderKeyId"), "senderKeyId");
            requireText(payload.get("recipientKeyId"), "recipientKeyId");
            requireMapping(payload.get("senderKeyBundle"), "senderKeyBundle");
            requireMapping(payload.get("recipientKeyBundle"), "recipientKeyBundle");
        } else {
            requireText(payload.get("senderKeyFingerprint"), "senderKeyFingerprint");
            requireText(payload.get("recipientKeyFingerprint"), "recipientKeyFingerprint");
        }

        byte[] hashingSecret = decodeRequiredBase64(payload, "hashingSecretEncoding", "hashingSecret");
        byte[] rotationIv = decodeRotationIv(payload);
        int rotationCount = decodeRotationCount(payload);
        double binWidth = decodeBinWidth(payload);
        List<Double> dimensionBias = decodeDimensionBias(payload);
        return new DecodedPayload(
                suite,
                hashingSecret,
                rotationIv,
                rotationCount,
                binWidth,
                dimensionBias);
    }

    private static CryptoSuite resolvePayloadSuite(
            Map<String, Object> payload, int version, CryptoSuite protectedV1Suite) {
        CryptoSuite suite;
        if (version == VERSION_ONE) {
            if (payload.containsKey("cryptoSuite")) {
                throw new IllegalArgumentException(
                        "Version 1 exchange payload must not contain cryptoSuite; suite selection belongs in the protected header.");
            }
            suite = protectedV1Suite == null ? CryptoSuite.defaultSuite() : protectedV1Suite;
        } else {
            Object value = payload.get("cryptoSuite");
            String suiteId = requireText(value, "cryptoSuite");
            try {
                suite = CryptoSuite.fromId(suiteId);
            } catch (IllegalArgumentException exception) {
                throw new IllegalArgumentException("Exchange config payload has an invalid crypto suite.", exception);
            }
        }

        if (suite.getExchangeConfigVersion() != version) {
            throw new IllegalArgumentException(
                    "Exchange config version " + version + " does not match suite '" + suite.getSuiteId() + "'.");
        }
        if (version == VERSION_ONE
                && !CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH.equals(suite.getExchangeKeyAgreement())) {
            throw new IllegalArgumentException(
                    "Version 1 exchange configs require an ECDH crypto suite; suite '"
                            + suite.getSuiteId()
                            + "' is incompatible.");
        }
        return suite;
    }

    private static String resolveV1Role(byte[] privatePem, Map<String, Object> payload) {
        byte[] publicPem = EcKeyUtils.derivePublicKeyFromPrivatePem(privatePem);
        String fingerprint = EcKeyUtils.publicKeyFingerprint(publicPem);
        boolean sender = fingerprint.equals(requireText(payload.get("senderKeyFingerprint"), "senderKeyFingerprint"));
        boolean recipient =
                fingerprint.equals(requireText(payload.get("recipientKeyFingerprint"), "recipientKeyFingerprint"));
        if (sender == recipient) {
            throw new IllegalArgumentException(
                    "Resolved private key does not uniquely match a sender or recipient fingerprint.");
        }
        return sender ? "sender" : "recipient";
    }

    private static String resolveV2Role(ExchangeKeyBundle privateBundle, Map<String, Object> payload) {
        String senderKeyId = requireText(payload.get("senderKeyId"), "senderKeyId");
        String recipientKeyId = requireText(payload.get("recipientKeyId"), "recipientKeyId");
        boolean sender = privateBundle.getKid().equals(senderKeyId);
        boolean recipient = privateBundle.getKid().equals(recipientKeyId);
        if (sender == recipient) {
            throw new IllegalArgumentException(
                    "Resolved private key bundle does not uniquely match a sender or recipient key identifier.");
        }
        return sender ? "sender" : "recipient";
    }

    /**
     * Validates an encoding marker and decodes its required base64url payload field.
     *
     * @param payload exchange payload fields
     * @param encodingField field containing the required encoding marker
     * @param valueField field containing the encoded bytes
     * @return the decoded payload bytes
     */
    private static byte[] decodeRequiredBase64(
            Map<String, Object> payload,
            String encodingField,
            String valueField) {
        String encoding = requireText(payload.get(encodingField), encodingField);
        if (!BASE64URL_ENCODING.equals(encoding)) {
            throw new IllegalArgumentException("Unsupported " + encodingField + " '" + encoding + "'.");
        }
        return decodeBase64Url(requireText(payload.get(valueField), valueField), valueField);
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
            if (!value.equals(Base64.getUrlEncoder().withoutPadding().encodeToString(decoded))) {
                throw new IllegalArgumentException("non-canonical base64url encoding");
            }
            return decoded;
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(fieldName + " is not valid base64url data.", exception);
        }
    }

    private static byte[] decodeRotationIv(Map<String, Object> payload) {
        Object value = payload.get("rotationIv");
        if (value == null) {
            return new byte[0];
        }
        String encoding = requireText(payload.get("rotationIvEncoding"), "rotationIvEncoding");
        if (!BASE64URL_ENCODING.equals(encoding)) {
            throw new IllegalArgumentException("Unsupported rotationIvEncoding '" + encoding + "'.");
        }
        String text = requireTextAllowEmpty(value, "rotationIv");
        return text.isEmpty() ? new byte[0] : decodeBase64Url(text, "rotationIv");
    }

    private static int decodeRotationCount(Map<String, Object> payload) {
        Object value = payload.get("rotationCount");
        if (value == null || numericEquals(value, 0)) {
            return 0;
        }
        if (!isIntegralNumber(value)) {
            throw new IllegalArgumentException(
                    "Exchange config payload has an invalid rotationCount. Must be a positive integer.");
        }
        long count = ((Number) value).longValue();
        if (count < 1 || count > Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "Exchange config payload has an invalid rotationCount. Must be a positive integer.");
        }
        return (int) count;
    }

    private static double decodeBinWidth(Map<String, Object> payload) {
        Object value = payload.get("binWidth");
        if (value == null) {
            return 0.05;
        }
        if (!(value instanceof Number number)
                || !Double.isFinite(number.doubleValue())
                || number.doubleValue() <= 0.0) {
            throw new IllegalArgumentException(
                    "Exchange config payload has an invalid binWidth. Must be a positive number.");
        }
        return number.doubleValue();
    }

    private static List<Double> decodeDimensionBias(Map<String, Object> payload) {
        Object value = payload.get("dimensionBias");
        if (value == null) {
            return List.of();
        }
        if (!(value instanceof List<?> values)) {
            throw new IllegalArgumentException(
                    "Exchange config payload has an invalid dimensionBias. Must be a list of numbers.");
        }
        List<Double> result = new ArrayList<>(values.size());
        for (int index = 0; index < values.size(); index++) {
            Object item = values.get(index);
            if (!(item instanceof Number number) || !Double.isFinite(number.doubleValue())) {
                throw new IllegalArgumentException("dimensionBias[" + index + "] is not a valid number.");
            }
            result.add(number.doubleValue());
        }
        return List.copyOf(result);
    }

    private static byte[] hkdfSha256(byte[] input, byte[] salt, byte[] info) {
        try {
            HKDFBytesGenerator generator = new HKDFBytesGenerator(new SHA256Digest());
            generator.init(new HKDFParameters(input, salt, info));
            byte[] output = new byte[32];
            generator.generateBytes(output, 0, output.length);
            return output;
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Unable to derive an HKDF-SHA256 key.", exception);
        }
    }

    private static void requireVersion(
            LoadedExchangeConfig exchangeConfig,
            int expectedVersion,
            String keyDescription) {
        Objects.requireNonNull(exchangeConfig, "Loaded exchange config must not be null.");
        if (exchangeConfig.version() != expectedVersion) {
            throw new IllegalArgumentException(
                    "Exchange config version " + exchangeConfig.version()
                            + " requires " + (expectedVersion == VERSION_ONE
                                    ? "an EC private-key PEM."
                                    : keyDescription + "."));
        }
    }

    private static Map<String, Object> requireMapping(Object value, String fieldName) {
        if (!(value instanceof Map<?, ?> mapping)) {
            throw new IllegalArgumentException("Exchange config payload is missing " + fieldName + ".");
        }
        return copyJsonMap(mapping, fieldName);
    }

    private static String requireText(Object value, String fieldName) {
        if (!(value instanceof String text) || text.isBlank()) {
            throw new IllegalArgumentException(fieldName + " must be a non-empty string.");
        }
        return text;
    }

    private static String requireTextAllowEmpty(Object value, String fieldName) {
        if (!(value instanceof String text)) {
            throw new IllegalArgumentException(fieldName + " must be a string.");
        }
        return text;
    }

    private static byte[] requireBytes(byte[] value, String fieldName, boolean nonEmpty) {
        if (value == null || (nonEmpty && value.length == 0)) {
            throw new IllegalArgumentException(fieldName + " must not be empty.");
        }
        return Arrays.copyOf(value, value.length);
    }

    private static boolean isIntegralNumber(Object value) {
        return value instanceof Byte
                || value instanceof Short
                || value instanceof Integer
                || value instanceof Long
                || value instanceof BigInteger;
    }

    private static boolean numericEquals(Object value, int expected) {
        return value instanceof Number number
                && Double.isFinite(number.doubleValue())
                && number.doubleValue() == expected;
    }

    private static Map<String, Object> copyJsonMap(Map<?, ?> value, String fieldName) {
        if (value == null) {
            throw new IllegalArgumentException(fieldName + " must be a JSON object.");
        }
        Map<String, Object> copy = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : value.entrySet()) {
            if (!(entry.getKey() instanceof String key)) {
                throw new IllegalArgumentException(fieldName + " must contain string field names.");
            }
            copy.put(key, copyJsonValue(entry.getValue(), fieldName + "." + key));
        }
        return Collections.unmodifiableMap(copy);
    }

    private static Object copyJsonValue(Object value, String fieldName) {
        if (value instanceof Map<?, ?> mapping) {
            return copyJsonMap(mapping, fieldName);
        }
        if (value instanceof List<?> values) {
            List<Object> copy = new ArrayList<>(values.size());
            for (int index = 0; index < values.size(); index++) {
                copy.add(copyJsonValue(values.get(index), fieldName + "[" + index + "]"));
            }
            return Collections.unmodifiableList(copy);
        }
        if (value instanceof byte[] bytes) {
            return Arrays.copyOf(bytes, bytes.length);
        }
        if (value == null || value instanceof String || value instanceof Number || value instanceof Boolean) {
            return value;
        }
        throw new IllegalArgumentException(fieldName + " contains an unsupported JSON value.");
    }

    private static byte[] copy(byte[] value) {
        return value == null ? null : Arrays.copyOf(value, value.length);
    }

    private record DecodedPayload(
            CryptoSuite cryptoSuite,
            byte[] hashingSecret,
            byte[] rotationIv,
            int rotationCount,
            double binWidth,
            List<Double> dimensionBias) implements Serializable {
    }

    /**
     * Immutable, versioned exchange envelope loaded from a caller-supplied source.
     *
     * @param path source path or the in-memory source marker
     * @param version detected exchange configuration version
     * @param config immutable JSON-compatible envelope
     */
    public record LoadedExchangeConfig(Path path, int version, Map<String, Object> config) implements Serializable {

        /**
         * Canonicalizes and defensively copies the loaded envelope.
         */
        public LoadedExchangeConfig {
            path = Objects.requireNonNull(path, "Exchange config path must not be null.");
            if (version != VERSION_ONE && version != VERSION_TWO) {
                throw new IllegalArgumentException("Unsupported exchange config version '" + version + "'.");
            }
            config = copyJsonMap(config, "exchangeConfig");
        }

        private Object writeReplace() {
            return new LoadedExchangeConfigSerializedForm(path.toString(), version, config);
        }
    }

    /**
     * Immutable decrypted exchange state for consumer operations.
     *
     * @param path source path or the in-memory source marker
     * @param version exchange configuration version
     * @param config immutable encrypted envelope
     * @param payload immutable decrypted payload
     * @param privateKeyPem EC private-key PEM for version one
     * @param privateKeyBundle private key bundle for version two
     * @param privateKeyRole sender or recipient
     * @param cryptoSuite validated crypto suite
     * @param hashingSecret decoded hashing secret
     * @param rotationIv decoded rotation IV
     * @param rotationCount validated rotation count
     * @param binWidth validated positive bin width
     * @param dimensionBias validated dimension-bias values
     * @param transportEncryptionKey version-two transport key, or null for version one
     */
    public record ResolvedExchangeConfig(
            Path path,
            int version,
            Map<String, Object> config,
            Map<String, Object> payload,
            byte[] privateKeyPem,
            ExchangeKeyBundle privateKeyBundle,
            String privateKeyRole,
            CryptoSuite cryptoSuite,
            byte[] hashingSecret,
            byte[] rotationIv,
            int rotationCount,
            double binWidth,
            List<Double> dimensionBias,
            byte[] transportEncryptionKey) implements Serializable {

        /**
         * Canonicalizes and defensively copies mutable resolved values.
         */
        public ResolvedExchangeConfig {
            path = Objects.requireNonNull(path, "Exchange config path must not be null.");
            if (version != VERSION_ONE && version != VERSION_TWO) {
                throw new IllegalArgumentException("Unsupported exchange config version '" + version + "'.");
            }
            config = copyJsonMap(config, "exchangeConfig");
            payload = copyJsonMap(payload, "payload");
            privateKeyPem = copy(privateKeyPem);
            if (privateKeyRole == null || privateKeyRole.isBlank()) {
                throw new IllegalArgumentException("Private key role must be a non-empty string.");
            }
            cryptoSuite = Objects.requireNonNull(cryptoSuite, "Crypto suite must not be null.");
            hashingSecret = requireBytes(hashingSecret, "hashingSecret", true);
            rotationIv = rotationIv == null ? new byte[0] : copy(rotationIv);
            if (rotationCount < 0) {
                throw new IllegalArgumentException("rotationCount must be non-negative.");
            }
            if (!Double.isFinite(binWidth) || binWidth <= 0.0) {
                throw new IllegalArgumentException("binWidth must be positive.");
            }
            dimensionBias = dimensionBias == null ? List.of() : List.copyOf(dimensionBias);
            transportEncryptionKey = copy(transportEncryptionKey);
        }

        private Object writeReplace() {
            return new ResolvedExchangeConfigSerializedForm(
                    path.toString(),
                    version,
                    config,
                    payload,
                    privateKeyPem,
                    privateKeyBundle,
                    privateKeyRole,
                    cryptoSuite,
                    hashingSecret,
                    rotationIv,
                    rotationCount,
                    binWidth,
                    dimensionBias,
                    transportEncryptionKey);
        }

        @Override
        public byte[] privateKeyPem() {
            return copy(privateKeyPem);
        }

        @Override
        public byte[] hashingSecret() {
            return copy(hashingSecret);
        }

        @Override
        public byte[] rotationIv() {
            return copy(rotationIv);
        }

        /**
         * Returns the transport key, deriving the version-one key on demand.
         *
         * @return a defensive copy of the 32-byte transport key
         */
        @Override
        public byte[] transportEncryptionKey() {
            return deriveTransportEncryptionKey(this);
        }

        private byte[] storedTransportEncryptionKey() {
            return copy(transportEncryptionKey);
        }
    }

    private static final class LoadedExchangeConfigSerializedForm implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String path;
        private final int version;
        private final Map<String, Object> config;

        private LoadedExchangeConfigSerializedForm(String path, int version, Map<String, Object> config) {
            this.path = path;
            this.version = version;
            this.config = config;
        }

        private Object readResolve() {
            return new LoadedExchangeConfig(Path.of(path), version, config);
        }
    }

    private static final class ResolvedExchangeConfigSerializedForm implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String path;
        private final int version;
        private final Map<String, Object> config;
        private final Map<String, Object> payload;
        private final byte[] privateKeyPem;
        private final ExchangeKeyBundle privateKeyBundle;
        private final String privateKeyRole;
        private final CryptoSuite cryptoSuite;
        private final byte[] hashingSecret;
        private final byte[] rotationIv;
        private final int rotationCount;
        private final double binWidth;
        private final List<Double> dimensionBias;
        private final byte[] transportEncryptionKey;

        private ResolvedExchangeConfigSerializedForm(
                String path,
                int version,
                Map<String, Object> config,
                Map<String, Object> payload,
                byte[] privateKeyPem,
                ExchangeKeyBundle privateKeyBundle,
                String privateKeyRole,
                CryptoSuite cryptoSuite,
                byte[] hashingSecret,
                byte[] rotationIv,
                int rotationCount,
                double binWidth,
                List<Double> dimensionBias,
                byte[] transportEncryptionKey) {
            this.path = path;
            this.version = version;
            this.config = config;
            this.payload = payload;
            this.privateKeyPem = privateKeyPem;
            this.privateKeyBundle = privateKeyBundle;
            this.privateKeyRole = privateKeyRole;
            this.cryptoSuite = cryptoSuite;
            this.hashingSecret = hashingSecret;
            this.rotationIv = rotationIv;
            this.rotationCount = rotationCount;
            this.binWidth = binWidth;
            this.dimensionBias = dimensionBias;
            this.transportEncryptionKey = transportEncryptionKey;
        }

        private Object readResolve() {
            return new ResolvedExchangeConfig(
                    Path.of(path),
                    version,
                    config,
                    payload,
                    privateKeyPem,
                    privateKeyBundle,
                    privateKeyRole,
                    cryptoSuite,
                    hashingSecret,
                    rotationIv,
                    rotationCount,
                    binWidth,
                    dimensionBias,
                    transportEncryptionKey);
        }
    }
}
