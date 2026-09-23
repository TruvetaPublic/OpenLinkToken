/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.IOException;
import java.io.Serializable;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.security.KeyPair;
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
import org.bouncycastle.pqc.crypto.mlkem.MLKEMKeyGenerationParameters;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMKeyPairGenerator;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMParameters;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMPrivateKeyParameters;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMPublicKeyParameters;
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

    /** EC algorithm identifier used by the hybrid bundle format. */
    public static final String EC_ALGORITHM = "ECDH-P256";

    private static final TypeReference<Map<String, Object>> JSON_OBJECT_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private final CryptoSuite suite;
    private final byte[] mlkemPublicKey;
    private final byte[] mlkemPrivateSeed;
    private final byte[] ecPublicPem;
    private final byte[] ecPrivatePem;
    private final String kid;

    /**
     * Creates and validates a key bundle.
     *
     * @param suite the version-two crypto suite
     * @param mlkemPublicKey the raw ML-KEM-768 public key
     * @param mlkemPrivateSeed the optional raw ML-KEM-768 private seed
     * @param ecPublicPem the optional P-256 public key PEM
     * @param ecPrivatePem the optional P-256 private key PEM
     */
    public ExchangeKeyBundle(
            CryptoSuite suite,
            byte[] mlkemPublicKey,
            byte[] mlkemPrivateSeed,
            byte[] ecPublicPem,
            byte[] ecPrivatePem) {
        this.suite = requireVersionTwoSuite(suite);
        this.mlkemPublicKey = copy(mlkemPublicKey);
        this.mlkemPrivateSeed = copy(mlkemPrivateSeed);
        this.ecPublicPem = copy(ecPublicPem);
        this.ecPrivatePem = copy(ecPrivatePem);
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

            byte[] ecPublicPem = null;
            byte[] ecPrivatePem = null;
            if (CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768.equals(suite.getExchangeKeyAgreement())) {
                KeyPair ecKeyPair = EcKeyUtils.generateKeyPair("P-256");
                ecPublicPem = EcKeyUtils.publicKeyToPem(ecKeyPair.getPublic());
                ecPrivatePem = EcKeyUtils.privateKeyToPem(ecKeyPair.getPrivate());
            }

            return new ExchangeKeyBundle(
                    suite,
                    publicKey.getEncoded(),
                    privateKey.getSeed(),
                    ecPublicPem,
                    ecPrivatePem);
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
        validateKeySections(keys, suite);

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

        byte[] ecPublicPem = null;
        byte[] ecPrivatePem = null;
        if (CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768.equals(suite.getExchangeKeyAgreement())) {
            Map<?, ?> ec = section(keys, "ec", "The selected hybrid suite requires an ec key section.");
            validateSectionKeys(
                    ec,
                    Set.of("algorithm", "publicKeyEncoding", "publicKey", "privateKeyEncoding", "privateKey"),
                    "ec");
            if (!EC_ALGORITHM.equals(ec.get("algorithm"))) {
                throw new KeyBundleException("Unsupported EC algorithm '" + ec.get("algorithm") + "'.");
            }
            requireEquals(ec.get("publicKeyEncoding"), "pem", "ec.publicKeyEncoding must be pem.");
            ecPublicPem = stringValue(ec.get("publicKey"), "ec.publicKey").getBytes(StandardCharsets.UTF_8);
            boolean hasPrivateKey = ec.containsKey("privateKey");
            boolean hasPrivateKeyEncoding = ec.containsKey("privateKeyEncoding");
            if (hasPrivateKey != hasPrivateKeyEncoding) {
                throw new KeyBundleException("ec.privateKey and ec.privateKeyEncoding must appear together.");
            }
            if (hasPrivateKey) {
                requireEquals(ec.get("privateKeyEncoding"), "pem", "ec.privateKeyEncoding must be pem.");
                ecPrivatePem = stringValue(ec.get("privateKey"), "ec.privateKey").getBytes(StandardCharsets.UTF_8);
            }
        }

        ExchangeKeyBundle bundle = new ExchangeKeyBundle(
                suite,
                mlkemPublicKey,
                mlkemPrivateSeed,
                ecPublicPem,
                ecPrivatePem);
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

        if (hasEcKey()) {
            Map<String, Object> ec = new LinkedHashMap<>();
            ec.put("algorithm", EC_ALGORITHM);
            ec.put("publicKeyEncoding", "pem");
            ec.put("publicKey", new String(ecPublicPem, StandardCharsets.UTF_8));
            if (includePrivate) {
                if (ecPrivatePem == null) {
                    throw new KeyBundleException("EC private key is missing.");
                }
                ec.put("privateKeyEncoding", "pem");
                ec.put("privateKey", new String(ecPrivatePem, StandardCharsets.UTF_8));
            }
            keys.put("ec", ec);
        }

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
     * @return the immutable suite
     */
    public CryptoSuite getSuite() {
        return suite;
    }

    /**
     * Returns a copy of the raw ML-KEM public key.
     *
     * @return the public key, or {@code null} when absent
     */
    public byte[] getMlkemPublicKey() {
        return copy(mlkemPublicKey);
    }

    /**
     * Returns a copy of the raw ML-KEM private seed.
     *
     * @return the private seed, or {@code null} when absent
     */
    public byte[] getMlkemPrivateSeed() {
        return copy(mlkemPrivateSeed);
    }

    /**
     * Returns a copy of the EC public key PEM.
     *
     * @return the public key, or {@code null} for a pure ML-KEM suite
     */
    public byte[] getEcPublicPem() {
        return copy(ecPublicPem);
    }

    /**
     * Returns a copy of the EC private key PEM.
     *
     * @return the private key, or {@code null} when absent
     */
    public byte[] getEcPrivatePem() {
        return copy(ecPrivatePem);
    }

    /**
     * Returns the stable public-material identifier.
     *
     * @return the portable key identifier
     */
    public String getKid() {
        return kid;
    }

    /**
     * Returns whether this bundle contains an EC key section.
     *
     * @return true for the hybrid profile
     */
    public boolean hasEcKey() {
        return ecPublicPem != null;
    }

    /**
     * Returns whether all private material required by the suite is present.
     *
     * @return true when the bundle can be used for private-key operations
     */
    public boolean hasPrivateMaterial() {
        if (CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768.equals(suite.getExchangeKeyAgreement())) {
            return mlkemPrivateSeed != null && ecPrivatePem != null;
        }
        return mlkemPrivateSeed != null;
    }

    private static AsymmetricCipherKeyPair generateMlKemKeyPair() {
        MLKEMKeyPairGenerator generator = new MLKEMKeyPairGenerator();
        generator.init(new MLKEMKeyGenerationParameters(new SecureRandom(), MLKEMParameters.ml_kem_768));
        return generator.generateKeyPair();
    }

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

    private static boolean usesMlKem(CryptoSuite suite) {
        return suite.getExchangeKeyAgreement().contains(CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX);
    }

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

        if (hasEcKey()) {
            try {
                if (!"P-256".equals(EcKeyUtils.curveName(EcKeyUtils.publicKeyFromPem(ecPublicPem)))) {
                    throw new KeyBundleException("ec.publicKey must be a P-256 public key.");
                }
            } catch (KeyBundleException exception) {
                throw exception;
            } catch (RuntimeException exception) {
                throw new KeyBundleException("ec.publicKey is not valid PEM.", exception);
            }
            if (ecPrivatePem != null) {
                try {
                    byte[] expectedPublicDer = EcKeyUtils.publicKeyToDer(EcKeyUtils.publicKeyFromPem(ecPublicPem));
                    byte[] derivedPublicDer = EcKeyUtils.publicKeyToDer(EcKeyUtils.publicKeyFromPem(
                            EcKeyUtils.derivePublicKeyFromPrivatePem(ecPrivatePem)));
                    if (!Arrays.equals(expectedPublicDer, derivedPublicDer)) {
                        throw new KeyBundleException("ec.privateKey does not match ec.publicKey.");
                    }
                } catch (KeyBundleException exception) {
                    throw exception;
                } catch (RuntimeException exception) {
                    throw new KeyBundleException("ec.privateKey is not valid PEM.", exception);
                }
            }
        } else if (ecPrivatePem != null || ecPublicPem != null) {
            throw new KeyBundleException("EC key material is only supported by the hybrid suite.");
        }
    }

    private String calculateKid() {
        byte[] prefix = ("openlinktoken:key-bundle:v1:" + suite.getSuiteId()).getBytes(StandardCharsets.US_ASCII);
        byte[] ecEncoded = hasEcKey() ? EcKeyUtils.publicKeyFromPem(ecPublicPem).getEncoded() : null;
        byte[] fingerprintInput = new byte[prefix.length
                + ":mlkem:".length() + mlkemPublicKey.length
                + (ecEncoded == null ? 0 : ":ec:".length() + ecEncoded.length)];
        int offset = 0;
        System.arraycopy(prefix, 0, fingerprintInput, offset, prefix.length);
        offset += prefix.length;
        byte[] mlkemMarker = ":mlkem:".getBytes(StandardCharsets.US_ASCII);
        System.arraycopy(mlkemMarker, 0, fingerprintInput, offset, mlkemMarker.length);
        offset += mlkemMarker.length;
        System.arraycopy(mlkemPublicKey, 0, fingerprintInput, offset, mlkemPublicKey.length);
        offset += mlkemPublicKey.length;
        if (ecEncoded != null) {
            byte[] ecMarker = ":ec:".getBytes(StandardCharsets.US_ASCII);
            System.arraycopy(ecMarker, 0, fingerprintInput, offset, ecMarker.length);
            offset += ecMarker.length;
            System.arraycopy(ecEncoded, 0, fingerprintInput, offset, ecEncoded.length);
        }
        return EcKeyUtils.fingerprintToKid(fingerprint(fingerprintInput));
    }

    private static Map<?, ?> section(Map<?, ?> keys, String name, String message) {
        Object value = keys.get(name);
        if (!(value instanceof Map<?, ?> section)) {
            throw new KeyBundleException(message);
        }
        return section;
    }

    private static void validateKeySections(Map<?, ?> keys, CryptoSuite suite) {
        boolean hybrid = CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768.equals(suite.getExchangeKeyAgreement());
        for (Object key : keys.keySet()) {
            if (!"mlkem".equals(key) && !(hybrid && "ec".equals(key))) {
                throw new KeyBundleException("Key bundle contains an unsupported key section '" + key + "'.");
            }
        }
    }

    private static void validateSectionKeys(Map<?, ?> section, Set<String> allowedKeys, String sectionName) {
        for (Object key : section.keySet()) {
            if (!(key instanceof String) || !allowedKeys.contains(key)) {
                throw new KeyBundleException("Key bundle contains an unsupported " + sectionName + " field '" + key
                        + "'.");
            }
        }
    }

    private static String stringValue(Object value, String fieldName) {
        if (!(value instanceof String string) || string.isBlank()) {
            throw new KeyBundleException(fieldName + " must be a non-empty string.");
        }
        return string;
    }

    private static byte[] decodeBase64(Object value, String fieldName) {
        try {
            return decodeBase64Url(stringValue(value, fieldName), fieldName);
        } catch (IllegalArgumentException exception) {
            throw new KeyBundleException(exception.getMessage(), exception);
        }
    }

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

    private static byte[] writeJsonObject(Map<String, Object> value) {
        try {
            return JSON_MAPPER.writeValueAsBytes(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Unable to serialize JSON object.", exception);
        }
    }

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

    private static String encodeBase64Url(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

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

    private static void requireEquals(Object actual, Object expected, String message) {
        if (!Objects.equals(actual, expected)) {
            throw new KeyBundleException(message);
        }
    }

    private static byte[] copy(byte[] value) {
        return value == null ? null : Arrays.copyOf(value, value.length);
    }

    /**
     * Signals malformed or incompatible key-bundle data.
     */
    public static final class KeyBundleException extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;

        private KeyBundleException(String message) {
            super(message);
        }

        private KeyBundleException(String message, Throwable cause) {
            super(message, cause);
        }
    }

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
                && Arrays.equals(mlkemPrivateSeed, other.mlkemPrivateSeed)
                && Arrays.equals(ecPublicPem, other.ecPublicPem)
                && Arrays.equals(ecPrivatePem, other.ecPrivatePem);
    }

    @Override
    public int hashCode() {
        int result = Objects.hash(suite);
        result = 31 * result + Arrays.hashCode(mlkemPublicKey);
        result = 31 * result + Arrays.hashCode(mlkemPrivateSeed);
        result = 31 * result + Arrays.hashCode(ecPublicPem);
        result = 31 * result + Arrays.hashCode(ecPrivatePem);
        return result;
    }
}
