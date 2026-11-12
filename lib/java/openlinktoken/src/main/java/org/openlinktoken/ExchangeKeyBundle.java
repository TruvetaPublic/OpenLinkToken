/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.IOException;
import java.io.Serializable;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.bouncycastle.crypto.AsymmetricCipherKeyPair;
import org.bouncycastle.crypto.generators.MLKEMKeyPairGenerator;
import org.bouncycastle.crypto.params.MLKEMKeyGenerationParameters;
import org.bouncycastle.crypto.params.MLKEMParameters;
import org.bouncycastle.crypto.params.MLKEMPrivateKeyParameters;
import org.bouncycastle.crypto.params.MLKEMPublicKeyParameters;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Immutable version-two exchange key material and its JSON representation.
 */
public final class ExchangeKeyBundle implements Serializable {
    private static final long serialVersionUID = 1L;

    /** Key-bundle schema version. */
    public static final int BUNDLE_VERSION = 1;

    /** Key-bundle type discriminator. */
    public static final String BUNDLE_TYPE = "openlinktoken-key-bundle";

    /** ML-KEM algorithm identifier used by the bundle format. */
    public static final String MLKEM_ALGORITHM = CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768;

    /** Raw ML-KEM-768 public-key size. */
    public static final int MLKEM_PUBLIC_KEY_SIZE = 1184;

    /** Raw ML-KEM-768 private seed size. */
    public static final int MLKEM_PRIVATE_SEED_SIZE = 64;

    private static final TypeReference<Map<String, Object>> JSON_OBJECT_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private final CryptoSuite suite;
    private final byte[] mlkemPublicKey;
    private final byte[] mlkemPrivateSeed;
    private final String kid;

    /**
     * Creates and validates a key bundle.
     *
     * @param suite the version-two crypto suite
     * @param mlkemPublicKey the raw ML-KEM-768 public key
     * @param mlkemPrivateSeed the optional raw ML-KEM-768 private seed
     */
    public ExchangeKeyBundle(
            CryptoSuite suite,
            byte[] mlkemPublicKey,
            byte[] mlkemPrivateSeed) {
        this.suite = requireVersionTwoSuite(suite);
        this.mlkemPublicKey = copy(mlkemPublicKey);
        this.mlkemPrivateSeed = copy(mlkemPrivateSeed);
        validateKeyMaterial();
        this.kid = calculateKid();
    }

    /**
     * Generates a private version-two key bundle for a registered suite.
     *
     * @param suiteId the version-two suite identifier
     * @return a generated key bundle
     */
    public static ExchangeKeyBundle generate(String suiteId) {
        if (suiteId == null || suiteId.isBlank()) {
            throw new KeyBundleException("Crypto suite ID must be a non-empty string.");
        }
        try {
            return generate(CryptoSuite.fromId(suiteId));
        } catch (IllegalArgumentException exception) {
            throw new KeyBundleException(exception.getMessage(), exception);
        }
    }

    /**
     * Generates a private version-two key bundle for a registered suite.
     *
     * @param suite the version-two suite
     * @return a generated key bundle
     */
    public static ExchangeKeyBundle generate(CryptoSuite suite) {
        requireVersionTwoSuite(suite);
        try {
            AsymmetricCipherKeyPair keyPair = generateMlKemKeyPair();
            MLKEMPublicKeyParameters publicKey = (MLKEMPublicKeyParameters) keyPair.getPublic();
            MLKEMPrivateKeyParameters privateKey = (MLKEMPrivateKeyParameters) keyPair.getPrivate();

            return new ExchangeKeyBundle(
                    suite,
                    publicKey.getEncoded(),
                    privateKey.getSeed());
        } catch (RuntimeException exception) {
            if (exception instanceof KeyBundleException) {
                throw exception;
            }
            throw new KeyBundleException("Unable to generate ML-KEM-768 key material.", exception);
        }
    }

    /**
     * Parses and validates a JSON key bundle.
     *
     * @param json UTF-8 JSON bytes
     * @param requirePrivate whether all private material required by the suite must be present
     * @return the parsed key bundle
     */
    public static ExchangeKeyBundle fromJson(byte[] json, boolean requirePrivate) {
        try {
            return fromMapping(readJsonObject(json), requirePrivate);
        } catch (KeyBundleException exception) {
            throw exception;
        } catch (RuntimeException exception) {
            throw new KeyBundleException("Key bundle is not valid JSON.", exception);
        }
    }

    /**
     * Parses and validates a public JSON key bundle.
     *
     * @param json UTF-8 JSON bytes
     * @return the parsed public key bundle
     */
    public static ExchangeKeyBundle fromJson(byte[] json) {
        return fromJson(json, false);
    }

    /**
     * Parses and validates a JSON key bundle.
     *
     * @param json UTF-8 JSON text
     * @param requirePrivate whether all private material required by the suite must be present
     * @return the parsed key bundle
     */
    public static ExchangeKeyBundle fromJson(String json, boolean requirePrivate) {
        if (json == null) {
            throw new KeyBundleException("Key bundle JSON must not be null.");
        }
        return fromJson(json.getBytes(StandardCharsets.UTF_8), requirePrivate);
    }

    /**
     * Parses and validates a public JSON key bundle.
     *
     * @param json UTF-8 JSON text
     * @return the parsed public key bundle
     */
    public static ExchangeKeyBundle fromJson(String json) {
        return fromJson(json, false);
    }

    /**
     * Parses and validates a JSON key-bundle mapping.
     *
     * @param mapping JSON object values
     * @param requirePrivate whether all private material required by the suite must be present
     * @return the parsed key bundle
     */
    public static ExchangeKeyBundle fromMapping(Map<String, ?> mapping, boolean requirePrivate) {
        if (mapping == null) {
            throw new KeyBundleException("Key bundle must be a JSON object.");
        }
        if (!Integer.valueOf(BUNDLE_VERSION).equals(mapping.get("version"))
                || !BUNDLE_TYPE.equals(mapping.get("type"))) {
            throw new KeyBundleException("Unsupported or missing key-bundle version/type.");
        }

        CryptoSuite suite;
        try {
            suite = CryptoSuite.fromId(stringValue(mapping.get("suite"), "suite"));
        } catch (IllegalArgumentException exception) {
            throw new KeyBundleException("Key bundle has an invalid crypto suite.", exception);
        }
        requireVersionTwoSuite(suite);

        Object keysValue = mapping.get("keys");
        if (!(keysValue instanceof Map<?, ?> keys)) {
            throw new KeyBundleException("Key bundle is missing its keys object.");
        }
        validateKeySections(keys);

        byte[] mlkemPublicKey = null;
        byte[] mlkemPrivateSeed = null;
        if (usesMlKem(suite)) {
            Map<?, ?> mlkem = section(keys, "mlkem", "The selected suite requires an mlkem key section.");
            validateSectionKeys(
                    mlkem,
                    Set.of("algorithm", "publicKeyEncoding", "publicKey", "fingerprint",
                            "privateKeyEncoding", "privateKey"),
                    "mlkem");
            if (!MLKEM_ALGORITHM.equals(mlkem.get("algorithm"))) {
                throw new KeyBundleException("Unsupported ML-KEM algorithm '" + mlkem.get("algorithm") + "'.");
            }
            requireEquals(mlkem.get("publicKeyEncoding"), "base64url", "mlkem.publicKeyEncoding must be base64url.");
            mlkemPublicKey = decodeBase64(mlkem.get("publicKey"), "mlkem.publicKey");
            if (mlkemPublicKey.length != MLKEM_PUBLIC_KEY_SIZE) {
                throw new KeyBundleException("mlkem.publicKey must be " + MLKEM_PUBLIC_KEY_SIZE + " bytes.");
            }
            requireEquals(
                    mlkem.get("fingerprint"),
                    fingerprint(mlkemPublicKey),
                    "mlkem.fingerprint does not match mlkem.publicKey.");
            boolean hasPrivateKey = mlkem.containsKey("privateKey");
            boolean hasPrivateKeyEncoding = mlkem.containsKey("privateKeyEncoding");
            if (hasPrivateKey != hasPrivateKeyEncoding) {
                throw new KeyBundleException("mlkem.privateKey and mlkem.privateKeyEncoding must appear together.");
            }
            if (hasPrivateKey) {
                requireEquals(
                        mlkem.get("privateKeyEncoding"),
                        "base64url",
                        "mlkem.privateKeyEncoding must be base64url.");
                mlkemPrivateSeed = decodeBase64(mlkem.get("privateKey"), "mlkem.privateKey");
                if (mlkemPrivateSeed.length != MLKEM_PRIVATE_SEED_SIZE) {
                    throw new KeyBundleException(
                            "mlkem.privateKey must be " + MLKEM_PRIVATE_SEED_SIZE + " bytes.");
                }
            }
        }

        ExchangeKeyBundle bundle = new ExchangeKeyBundle(
                suite,
                mlkemPublicKey,
                mlkemPrivateSeed);
        if (!bundle.getKid().equals(mapping.get("kid"))) {
            throw new KeyBundleException("Key-bundle kid does not match its public key material.");
        }
        if (requirePrivate && !bundle.hasPrivateMaterial()) {
            throw new KeyBundleException("Key bundle does not contain the private material required by its suite.");
        }
        return bundle;
    }

    /**
     * Parses and validates a public key-bundle mapping.
     *
     * @param mapping JSON object values
     * @return the parsed public key bundle
     */
    public static ExchangeKeyBundle fromMapping(Map<String, ?> mapping) {
        return fromMapping(mapping, false);
    }

    /**
     * Serializes this bundle without private material.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return a mutable JSON-compatible mapping
     */
    public Map<String, Object> toMapping() {
        return toMapping(false);
    }

    /**
     * Serializes this bundle to a JSON-compatible mapping.
     *
     * @param includePrivate whether private material should be included
     * @return a mutable JSON-compatible mapping
     */
    public Map<String, Object> toMapping(boolean includePrivate) {
        Map<String, Object> keys = new LinkedHashMap<>();
        Map<String, Object> mlkem = new LinkedHashMap<>();
        mlkem.put("algorithm", MLKEM_ALGORITHM);
        mlkem.put("publicKeyEncoding", "base64url");
        mlkem.put("publicKey", encodeBase64Url(mlkemPublicKey));
        mlkem.put("fingerprint", fingerprint(mlkemPublicKey));
        if (includePrivate) {
            if (mlkemPrivateSeed == null) {
                throw new KeyBundleException("ML-KEM private seed is missing.");
            }
            mlkem.put("privateKeyEncoding", "base64url");
            mlkem.put("privateKey", encodeBase64Url(mlkemPrivateSeed));
        }
        keys.put("mlkem", mlkem);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("version", BUNDLE_VERSION);
        result.put("type", BUNDLE_TYPE);
        result.put("suite", suite.getSuiteId());
        result.put("kid", kid);
        result.put("keys", keys);
        return result;
    }

    /**
     * Serializes this bundle without private material.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return deterministic UTF-8 JSON
     */
    public byte[] toJson() {
        return toJson(false);
    }

    /**
     * Serializes this bundle to deterministic UTF-8 JSON.
     *
     * @param includePrivate whether private material should be included
     * @return deterministic UTF-8 JSON
     */
    public byte[] toJson(boolean includePrivate) {
        return writeJsonObject(toMapping(includePrivate));
    }

    /**
     * Returns the crypto suite.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the immutable suite
     */
    public CryptoSuite getSuite() {
        return suite;
    }

    /**
     * Returns a copy of the raw ML-KEM public key.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the public key, or {@code null} when absent
     */
    public byte[] getMlkemPublicKey() {
        return copy(mlkemPublicKey);
    }

    /**
     * Returns a copy of the raw ML-KEM private seed.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the private seed, or {@code null} when absent
     */
    public byte[] getMlkemPrivateSeed() {
        return copy(mlkemPrivateSeed);
    }

    /**
     * Returns the stable public-material identifier.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the portable key identifier
     */
    public String getKid() {
        return kid;
    }

    /**
     * Returns whether all private material required by the suite is present.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return true when the bundle can be used for private-key operations
     */
    public boolean hasPrivateMaterial() {
        return mlkemPrivateSeed != null;
    }

    /**
     * Generates an ML-KEM-768 key pair.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the generated public and private key parameters
     */
    private static AsymmetricCipherKeyPair generateMlKemKeyPair() {
        MLKEMKeyPairGenerator generator = new MLKEMKeyPairGenerator();
        generator.init(new MLKEMKeyGenerationParameters(new SecureRandom(), MLKEMParameters.ml_kem_768));
        return generator.generateKeyPair();
    }

    /**
     * Requires a registered suite that uses version-two exchange key bundles.
     *
     * @param suite candidate crypto suite
     * @return the validated version-two suite
     */
    private static CryptoSuite requireVersionTwoSuite(CryptoSuite suite) {
        if (suite == null) {
            throw new KeyBundleException("Crypto suite must not be null.");
        }
        if (suite.getExchangeConfigVersion() != 2 || !usesMlKem(suite)) {
            throw new KeyBundleException(
                    "Suite '" + suite.getSuiteId() + "' does not use key-bundle exchange configuration.");
        }
        return suite;
    }

    /**
     * Checks whether a suite uses an ML-KEM key-agreement mechanism.
     *
     * @param suite crypto suite to inspect
     * @return {@code true} if the suite uses ML-KEM
     */
    private static boolean usesMlKem(CryptoSuite suite) {
        return CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768.equals(suite.getExchangeKeyAgreement());
    }

    /**
     * Validates that the stored public and optional private keys match the suite.
     *
     * <p>This method accepts no arguments and returns no value.</p>
     */
    private void validateKeyMaterial() {
        if (mlkemPublicKey == null || mlkemPublicKey.length != MLKEM_PUBLIC_KEY_SIZE) {
            throw new KeyBundleException("mlkem.publicKey must be " + MLKEM_PUBLIC_KEY_SIZE + " bytes.");
        }
        try {
            new MLKEMPublicKeyParameters(MLKEMParameters.ml_kem_768, mlkemPublicKey);
        } catch (RuntimeException exception) {
            throw new KeyBundleException("mlkem.publicKey is not a valid ML-KEM-768 public key.", exception);
        }
        if (mlkemPrivateSeed != null) {
            if (mlkemPrivateSeed.length != MLKEM_PRIVATE_SEED_SIZE) {
                throw new KeyBundleException("mlkem.privateKey must be " + MLKEM_PRIVATE_SEED_SIZE + " bytes.");
            }
            try {
                byte[] derivedPublic = new MLKEMPrivateKeyParameters(
                        MLKEMParameters.ml_kem_768,
                        mlkemPrivateSeed).getPublicKey();
                if (!Arrays.equals(mlkemPublicKey, derivedPublic)) {
                    throw new KeyBundleException("mlkem.privateKey does not match mlkem.publicKey.");
                }
            } catch (KeyBundleException exception) {
                throw exception;
            } catch (RuntimeException exception) {
                throw new KeyBundleException("mlkem.privateKey is not a valid ML-KEM-768 seed.", exception);
            }
        }

    }

    /**
     * Derives the stable key identifier from this bundle's suite and public keys.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the suite-bound key identifier
     */
    private String calculateKid() {
        byte[] prefix = ("openlinktoken:key-bundle:v1:" + suite.getSuiteId()).getBytes(StandardCharsets.US_ASCII);
        byte[] fingerprintInput = new byte[prefix.length
                + ":mlkem:".length() + mlkemPublicKey.length];
        int offset = 0;
        System.arraycopy(prefix, 0, fingerprintInput, offset, prefix.length);
        offset += prefix.length;
        byte[] mlkemMarker = ":mlkem:".getBytes(StandardCharsets.US_ASCII);
        System.arraycopy(mlkemMarker, 0, fingerprintInput, offset, mlkemMarker.length);
        offset += mlkemMarker.length;
        System.arraycopy(mlkemPublicKey, 0, fingerprintInput, offset, mlkemPublicKey.length);
        return EcKeyUtils.fingerprintToKid(fingerprint(fingerprintInput));
    }

    /**
     * Retrieves a named key section from a mapping.
     *
     * @param keys key sections mapping
     * @param name requested section name
     * @param message validation message when the section is absent or invalid
     * @return the requested mapping section
     */
    private static Map<?, ?> section(Map<?, ?> keys, String name, String message) {
        Object value = keys.get(name);
        if (!(value instanceof Map<?, ?> section)) {
            throw new KeyBundleException(message);
        }
        return section;
    }

    /**
     * Rejects key sections that are not supported by the selected suite.
     *
     * <p>This method returns no value.</p>
     *
     * @param keys key sections mapping
     */
    private static void validateKeySections(Map<?, ?> keys) {
        for (Object key : keys.keySet()) {
            if (!"mlkem".equals(key)) {
                throw new KeyBundleException("Key bundle contains an unsupported key section '" + key + "'.");
            }
        }
    }

    /**
     * Rejects fields not allowed in a key section.
     *
     * <p>This method returns no value.</p>
     *
     * @param section key-section mapping
     * @param allowedKeys allowed field names
     * @param sectionName section name used in validation errors
     */
    private static void validateSectionKeys(Map<?, ?> section, Set<String> allowedKeys, String sectionName) {
        for (Object key : section.keySet()) {
            if (!(key instanceof String) || !allowedKeys.contains(key)) {
                throw new KeyBundleException("Key bundle contains an unsupported " + sectionName + " field '" + key
                        + "'.");
            }
        }
    }

    /**
     * Requires a non-empty string field value.
     *
     * @param value candidate field value
     * @param fieldName field name used in validation errors
     * @return the validated string
     */
    private static String stringValue(Object value, String fieldName) {
        if (!(value instanceof String string) || string.isBlank()) {
            throw new KeyBundleException(fieldName + " must be a non-empty string.");
        }
        return string;
    }

    /**
     * Validates and decodes a required base64url field.
     *
     * @param value field value to decode
     * @param fieldName field name used in validation errors
     * @return decoded bytes
     */
    private static byte[] decodeBase64(Object value, String fieldName) {
        try {
            return decodeBase64Url(stringValue(value, fieldName), fieldName);
        } catch (IllegalArgumentException exception) {
            throw new KeyBundleException(exception.getMessage(), exception);
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

    /**
     * Computes a SHA-256 fingerprint for encoded key material.
     *
     * @param value encoded key bytes
     * @return uppercase, colon-delimited SHA-256 fingerprint
     */
    private static String fingerprint(byte[] value) {
        byte[] digest;
        try {
            digest = MessageDigest.getInstance("SHA-256").digest(value);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available.", exception);
        }

        StringBuilder result = new StringBuilder(digest.length * 3 - 1);
        for (int index = 0; index < digest.length; index++) {
            if (index > 0) {
                result.append(':');
            }
            result.append(String.format("%02X", digest[index] & 0xFF));
        }
        return result.toString();
    }

    /**
     * Requires two values to be equal.
     *
     * <p>This method returns no value.</p>
     *
     * @param actual actual value
     * @param expected expected value
     * @param message validation message when the values differ
     */
    private static void requireEquals(Object actual, Object expected, String message) {
        if (!Objects.equals(actual, expected)) {
            throw new KeyBundleException(message);
        }
    }

    /**
     * Returns a defensive copy of nullable byte-array input.
     *
     * @param value source byte array, or {@code null}
     * @return a defensive copy, or {@code null} when the input is {@code null}
     */
    private static byte[] copy(byte[] value) {
        return value == null ? null : Arrays.copyOf(value, value.length);
    }

    /**
     * Signals malformed or incompatible key-bundle data.
     */
    public static final class KeyBundleException extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;

        /**
         * Creates a key-bundle exception with a detail message.
         *
         * @param message exception detail message
         */
        private KeyBundleException(String message) {
            super(message);
        }

        /**
         * Creates a key-bundle exception with a detail message and cause.
         *
         * @param message exception detail message
         * @param cause underlying cause
         */
        private KeyBundleException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /**
     * Compares this bundle with another object for equality.
     *
     * @param object candidate object to compare
     * @return {@code true} if both objects contain the same suite and key material
     */
    @Override
    public boolean equals(Object object) {
        if (this == object) {
            return true;
        }
        if (!(object instanceof ExchangeKeyBundle other)) {
            return false;
        }
        return suite.equals(other.suite)
                && Arrays.equals(mlkemPublicKey, other.mlkemPublicKey)
                && Arrays.equals(mlkemPrivateSeed, other.mlkemPrivateSeed);
    }

    /**
     * Computes a hash code from this bundle's suite and key material.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the bundle hash code
     */
    @Override
    public int hashCode() {
        int result = Objects.hash(suite);
        result = 31 * result + Arrays.hashCode(mlkemPublicKey);
        result = 31 * result + Arrays.hashCode(mlkemPrivateSeed);
        return result;
    }
}
