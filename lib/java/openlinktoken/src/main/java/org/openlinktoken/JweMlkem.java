/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.IOException;
import java.io.Serializable;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.bouncycastle.crypto.SecretWithEncapsulation;
import org.bouncycastle.crypto.digests.SHA256Digest;
import org.bouncycastle.crypto.engines.AESWrapEngine;
import org.bouncycastle.crypto.generators.HKDFBytesGenerator;
import org.bouncycastle.crypto.kems.MLKEMExtractor;
import org.bouncycastle.crypto.kems.MLKEMGenerator;
import org.bouncycastle.crypto.params.HKDFParameters;
import org.bouncycastle.crypto.params.KeyParameter;
import org.bouncycastle.crypto.params.MLKEMParameters;
import org.bouncycastle.crypto.params.MLKEMPrivateKeyParameters;
import org.bouncycastle.crypto.params.MLKEMPublicKeyParameters;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Package-private standard JWE JSON support for version-two ML-KEM exchange envelopes.
 */
final class JweMlkem implements Serializable {
    private static final long serialVersionUID = 1L;

    static final int EXCHANGE_V2_VERSION = 2;
    static final String EXCHANGE_V2_TYPE = "openlinktoken-exchange+jwe";
    static final String EXCHANGE_V2_CONTENT_TYPE = "application/openlinktoken-exchange+json";
    static final String EXCHANGE_V2_ENCRYPTION = CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM;
    static final String PURE_KEM_ALGORITHM = CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768;
    static final String TOKEN_TRANSPORT_KEY_INFO = "openlinktoken:token-encryption:v2";

    static final int CEK_SIZE = 32;
    static final int IV_SIZE = 12;
    static final int TAG_SIZE = 16;
    static final int MLKEM_CIPHERTEXT_SIZE = 1088;
    static final int AES_KW_WRAPPED_CEK_SIZE = 40;
    static final int RECIPIENT_ENCRYPTED_KEY_SIZE = MLKEM_CIPHERTEXT_SIZE + AES_KW_WRAPPED_CEK_SIZE;

    private static final Set<String> JWE_MEMBERS = Set.of(
            "protected",
            "recipients",
            "iv",
            "ciphertext",
            "tag");
    private static final Set<String> REQUIRED_PROTECTED_FIELDS = Set.of(
            "typ",
            "cty",
            "enc",
            "version",
            "cryptoSuite",
            "exchangeId");
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final TypeReference<Map<String, Object>> JSON_OBJECT_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    /**
     * Creates the utility instance with no arguments.
     */
    private JweMlkem() {
    }

    /**
     * Encrypts plaintext into a version-two general JWE for the supplied recipients.
     *
     * @param plaintext plaintext bytes
     * @param protectedHeader protected JWE header fields
     * @param recipients recipient key bundles
     * @return the serialized general JWE envelope
     */
    static Map<String, Object> build(
            byte[] plaintext,
            Map<String, ?> protectedHeader,
            List<ExchangeKeyBundle> recipients) {
        if (plaintext == null) {
            throw new IllegalArgumentException("JWE plaintext must not be null.");
        }
        Map<String, Object> header = copyStringMap(protectedHeader, "Version-2 protected header");
        validateProtectedHeader(header);
        CryptoSuite suite = suiteForHeader(header);
        String algorithm = algorithmForSuite(suite);
        if (recipients == null || recipients.size() < 2) {
            throw new IllegalArgumentException("Version-2 general JWE JSON requires at least two recipients.");
        }

        Set<String> kids = new HashSet<>();
        for (ExchangeKeyBundle bundle : recipients) {
            if (bundle == null) {
                throw new IllegalArgumentException("Version-2 recipients must not contain null bundles.");
            }
            if (!suite.getSuiteId().equals(bundle.getSuite().getSuiteId())) {
                throw new IllegalArgumentException(
                        "Exchange key bundle suite does not match the protected exchange suite.");
            }
            if (!kids.add(bundle.getKid())) {
                throw new IllegalArgumentException("Version-2 recipients must have unique key identifiers.");
            }
        }

        String protectedValue = encodeBase64(writeJsonObject(header));
        byte[] cek = randomBytes(CEK_SIZE);
        byte[] iv = randomBytes(IV_SIZE);
        List<Map<String, Object>> serializedRecipients = recipients.stream()
                .map(bundle -> buildRecipient(bundle, algorithm, header, cek))
                .toList();
        byte[] encrypted;
        try {
            encrypted = encryptContent(plaintext, cek, iv, protectedValue);
        } finally {
            Arrays.fill(cek, (byte) 0);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("protected", protectedValue);
        result.put("recipients", serializedRecipients);
        result.put("iv", encodeBase64(iv));
        result.put("ciphertext", encodeBase64(Arrays.copyOf(encrypted, encrypted.length - TAG_SIZE)));
        result.put("tag", encodeBase64(Arrays.copyOfRange(encrypted, encrypted.length - TAG_SIZE, encrypted.length)));
        return result;
    }

    /**
     * Decrypts a version-two JWE for the matching private key bundle.
     *
     * @param envelope general JWE JSON fields
     * @param privateBundle recipient private key bundle
     * @return decrypted payload, transport key, content key, and protected header
     */
    static Decryption decrypt(Map<String, ?> envelope, ExchangeKeyBundle privateBundle) {
        validateTopLevel(envelope);
        if (privateBundle == null) {
            throw new IllegalArgumentException("Version-2 decryption requires an ExchangeKeyBundle.");
        }

        String protectedValue = stringValue(envelope.get("protected"), "protected");
        Map<String, Object> protectedHeader = decodeJsonObject(
                decodeBase64(protectedValue, "protected", false),
                "Protected version-2 JWE header");
        validateProtectedHeader(protectedHeader);
        CryptoSuite suite = suiteForHeader(protectedHeader);
        String algorithm = algorithmForSuite(suite);
        if (!suite.getSuiteId().equals(privateBundle.getSuite().getSuiteId())) {
            throw new IllegalArgumentException(
                    "Private key bundle suite does not match the protected exchange suite.");
        }
        if (privateBundle.getMlkemPrivateSeed() == null) {
            throw new IllegalArgumentException("Exchange key bundle is missing its ML-KEM private seed.");
        }

        Object recipientsValue = envelope.get("recipients");
        if (!(recipientsValue instanceof List<?> recipients) || recipients.size() < 2) {
            throw new IllegalArgumentException("Version-2 JWE must contain at least two recipients.");
        }

        Map<String, Object> matchingRecipient = null;
        for (Object value : recipients) {
            Map<String, Object> recipient = validateRecipient(value, algorithm);
            Map<String, Object> header = mapValue(recipient.get("header"), "Version-2 recipient header");
            if (privateBundle.getKid().equals(header.get("kid"))) {
                if (matchingRecipient != null) {
                    throw new IllegalArgumentException(
                            "No unique recipient entry matches the supplied private key bundle.");
                }
                matchingRecipient = recipient;
            }
        }
        if (matchingRecipient == null) {
            throw new IllegalArgumentException(
                    "No unique recipient entry matches the supplied private key bundle.");
        }

        Map<String, Object> recipientHeader = mapValue(matchingRecipient.get("header"), "Version-2 recipient header");
        byte[] encryptedKey = decodeBase64(
                stringValue(matchingRecipient.get("encrypted_key"), "recipient encrypted_key"),
                "recipient encrypted_key",
                false);
        byte[] ciphertext = decodeBase64(
                stringValueAllowEmpty(envelope.get("ciphertext"), "ciphertext"),
                "ciphertext",
                true);
        byte[] iv = decodeBase64(stringValue(envelope.get("iv"), "iv"), "iv", false);
        byte[] tag = decodeBase64(stringValue(envelope.get("tag"), "tag"), "tag", false);
        if (iv.length != IV_SIZE) {
            throw new IllegalArgumentException("Version-2 JWE iv must be " + IV_SIZE + " bytes.");
        }
        if (tag.length != TAG_SIZE) {
            throw new IllegalArgumentException("Version-2 JWE tag must be " + TAG_SIZE + " bytes.");
        }

        byte[] sharedSecret = decapsulate(privateBundle, encryptedKey);
        byte[] cek;
        byte[] kek = null;
        try {
            kek = deriveRecipientKek(
                    sharedSecret,
                    protectedHeader,
                    algorithm,
                    (String) recipientHeader.get("kid"),
                    Arrays.copyOf(encryptedKey, MLKEM_CIPHERTEXT_SIZE),
                    privateBundle.getMlkemPublicKey());
            cek = unwrap(kek, Arrays.copyOfRange(encryptedKey, MLKEM_CIPHERTEXT_SIZE, encryptedKey.length));
        } finally {
            Arrays.fill(sharedSecret, (byte) 0);
            if (kek != null) {
                Arrays.fill(kek, (byte) 0);
            }
        }
        byte[] encrypted = new byte[ciphertext.length + tag.length];
        System.arraycopy(ciphertext, 0, encrypted, 0, ciphertext.length);
        System.arraycopy(tag, 0, encrypted, ciphertext.length, tag.length);
        byte[] plaintext = decryptContent(encrypted, cek, iv, protectedValue);
        byte[] transportKey = deriveTokenTransportKey(cek, (String) protectedHeader.get("exchangeId"));
        return new Decryption(plaintext, transportKey, cek, protectedHeader);
    }

    /**
     * Derives the separate token transport key from the JWE content key and exchange ID.
     *
     * @param cek 32-byte JWE content-encryption key
     * @param exchangeId authenticated exchange identifier
     * @return the derived 32-byte token transport key
     */
    static byte[] deriveTokenTransportKey(byte[] cek, String exchangeId) {
        if (cek == null || cek.length != CEK_SIZE) {
            throw new IllegalArgumentException("Version-2 JWE CEK must be " + CEK_SIZE + " bytes.");
        }
        if (exchangeId == null || exchangeId.isEmpty()) {
            throw new IllegalArgumentException("Version-2 exchange ID must be a non-empty string.");
        }
        return hkdf(
                cek,
                exchangeId.getBytes(StandardCharsets.UTF_8),
                TOKEN_TRANSPORT_KEY_INFO.getBytes(StandardCharsets.US_ASCII),
                CEK_SIZE);
    }

    /**
     * Creates a recipient entry containing the encapsulated and wrapped content key.
     *
     * @param bundle recipient public key bundle
     * @param algorithm recipient key-management algorithm
     * @param protectedHeader authenticated protected-header fields
     * @param cek content-encryption key to wrap
     * @return the serialized recipient header and encrypted key
     */
    private static Map<String, Object> buildRecipient(
            ExchangeKeyBundle bundle,
            String algorithm,
            Map<String, Object> protectedHeader,
            byte[] cek) {
        Encapsulation encapsulation = encapsulate(bundle);
        byte[] kek = deriveRecipientKek(
                encapsulation.sharedSecret,
                protectedHeader,
                algorithm,
                bundle.getKid(),
                encapsulation.ciphertext,
                bundle.getMlkemPublicKey());
        byte[] wrappedCek;
        try {
            wrappedCek = wrap(kek, cek);
        } finally {
            Arrays.fill(kek, (byte) 0);
            Arrays.fill(encapsulation.sharedSecret, (byte) 0);
        }
        byte[] encryptedKey = new byte[encapsulation.ciphertext.length + wrappedCek.length];
        System.arraycopy(encapsulation.ciphertext, 0, encryptedKey, 0, encapsulation.ciphertext.length);
        System.arraycopy(wrappedCek, 0, encryptedKey, encapsulation.ciphertext.length, wrappedCek.length);

        Map<String, Object> header = new LinkedHashMap<>();
        header.put("alg", algorithm);
        header.put("kid", bundle.getKid());
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("header", header);
        result.put("encrypted_key", encodeBase64(encryptedKey));
        return result;
    }

    /**
     * Encapsulates a shared secret for an ML-KEM recipient.
     *
     * @param bundle recipient public key bundle
     * @return the shared secret and ML-KEM ciphertext
     */
    private static Encapsulation encapsulate(ExchangeKeyBundle bundle) {
        MLKEMPublicKeyParameters publicKey;
        try {
            publicKey = new MLKEMPublicKeyParameters(
                    MLKEMParameters.ml_kem_768,
                    bundle.getMlkemPublicKey());
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Exchange key bundle ML-KEM public key is invalid.", exception);
        }
        SecretWithEncapsulation encapsulated;
        try {
            encapsulated = new MLKEMGenerator(RANDOM).generateEncapsulated(publicKey);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Unable to encapsulate ML-KEM-768.", exception);
        }
        byte[] mlkemSecret = encapsulated.getSecret();
        byte[] ciphertext = encapsulated.getEncapsulation();
        if (ciphertext.length != MLKEM_CIPHERTEXT_SIZE) {
            throw new IllegalArgumentException(
                    CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768
                            + " produced an unexpected ciphertext length.");
        }
        return new Encapsulation(mlkemSecret, ciphertext);
    }

    /**
     * Decapsulates the recipient's ML-KEM secret.
     *
     * @param bundle recipient private key bundle
     * @param encryptedKey combined ML-KEM ciphertext and wrapped content key
     * @return the derived shared secret
     */
    private static byte[] decapsulate(
            ExchangeKeyBundle bundle,
            byte[] encryptedKey) {
        if (encryptedKey.length != RECIPIENT_ENCRYPTED_KEY_SIZE) {
            throw new IllegalArgumentException(
                    "Recipient encrypted_key must be " + RECIPIENT_ENCRYPTED_KEY_SIZE
                            + " bytes, got " + encryptedKey.length + ".");
        }
        byte[] ciphertext = Arrays.copyOf(encryptedKey, MLKEM_CIPHERTEXT_SIZE);
        MLKEMPrivateKeyParameters privateKey;
        byte[] seed = bundle.getMlkemPrivateSeed();
        try {
            privateKey = new MLKEMPrivateKeyParameters(MLKEMParameters.ml_kem_768, seed);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Exchange key bundle ML-KEM private seed is invalid.", exception);
        } finally {
            Arrays.fill(seed, (byte) 0);
        }
        byte[] mlkemSecret;
        try {
            mlkemSecret = new MLKEMExtractor(privateKey).extractSecret(ciphertext);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Unable to decapsulate ML-KEM-768.", exception);
        }
        return mlkemSecret;
    }

    /**
     * Derives the recipient key-encryption key using the exchange context.
     *
     * @param sharedSecret encapsulated shared secret
     * @param protectedHeader authenticated protected-header fields
     * @param algorithm recipient key-management algorithm
     * @param kid recipient key identifier
     * @param mlkemCiphertext ML-KEM ciphertext bound into the derivation
     * @param recipientPublicKey recipient ML-KEM public key bound into the derivation
     * @return the derived AES key-encryption key
     */
    private static byte[] deriveRecipientKek(
            byte[] sharedSecret,
            Map<String, Object> protectedHeader,
            String algorithm,
            String kid,
            byte[] mlkemCiphertext,
            byte[] recipientPublicKey) {
        String info = String.join(
                ":",
                "openlinktoken",
                "jwe",
                "v2",
                (String) protectedHeader.get("cryptoSuite"),
                algorithm,
                kid,
                kemTranscriptHash(mlkemCiphertext, recipientPublicKey));
        return hkdf(
                sharedSecret,
                ((String) protectedHeader.get("exchangeId")).getBytes(StandardCharsets.UTF_8),
                info.getBytes(StandardCharsets.US_ASCII),
                CEK_SIZE);
    }

    /**
     * Hashes the ML-KEM ciphertext and recipient public key for KDF context binding.
     *
     * @param mlkemCiphertext ML-KEM ciphertext
     * @param recipientPublicKey recipient ML-KEM public key
     * @return lowercase hex SHA-256 of ciphertext followed by public key
     */
    private static String kemTranscriptHash(byte[] mlkemCiphertext, byte[] recipientPublicKey) {
        SHA256Digest digest = new SHA256Digest();
        digest.update(mlkemCiphertext, 0, mlkemCiphertext.length);
        digest.update(recipientPublicKey, 0, recipientPublicKey.length);
        byte[] out = new byte[digest.getDigestSize()];
        digest.doFinal(out, 0);
        return HexFormat.of().formatHex(out);
    }

    /**
     * Wraps the content-encryption key with the derived key-encryption key.
     *
     * @param kek AES key-encryption key
     * @param cek content-encryption key
     * @return the wrapped content-encryption key
     */
    private static byte[] wrap(byte[] kek, byte[] cek) {
        try {
            AESWrapEngine wrapper = new AESWrapEngine();
            wrapper.init(true, new KeyParameter(kek));
            return wrapper.wrap(cek, 0, cek.length);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Failed to wrap the version-2 JWE CEK.", exception);
        }
    }

    /**
     * Unwraps and validates the content-encryption key.
     *
     * @param kek AES key-encryption key
     * @param wrappedCek wrapped content-encryption key
     * @return the unwrapped 32-byte content-encryption key
     */
    private static byte[] unwrap(byte[] kek, byte[] wrappedCek) {
        try {
            AESWrapEngine wrapper = new AESWrapEngine();
            wrapper.init(false, new KeyParameter(kek));
            byte[] cek = wrapper.unwrap(wrappedCek, 0, wrappedCek.length);
            if (cek.length != CEK_SIZE) {
                throw new IllegalArgumentException("Unwrapped version-2 JWE CEK must be " + CEK_SIZE + " bytes.");
            }
            return cek;
        } catch (IllegalArgumentException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new IllegalArgumentException("Failed to unwrap the version-2 JWE CEK.", exception);
        }
    }

    /**
     * Derives key bytes with HKDF-SHA256.
     *
     * @param input input keying material
     * @param salt HKDF salt
     * @param info HKDF context information
     * @param length requested output length in bytes
     * @return the derived key bytes
     */
    private static byte[] hkdf(byte[] input, byte[] salt, byte[] info, int length) {
        try {
            HKDFBytesGenerator generator = new HKDFBytesGenerator(new SHA256Digest());
            generator.init(new HKDFParameters(input, salt, info));
            byte[] output = new byte[length];
            generator.generateBytes(output, 0, output.length);
            return output;
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Unable to derive an HKDF-SHA256 key.", exception);
        }
    }

    /**
     * Encrypts plaintext with AES-256-GCM and authenticates the protected header.
     *
     * @param plaintext plaintext bytes
     * @param cek 32-byte content-encryption key
     * @param iv GCM initialization vector
     * @param protectedValue encoded protected-header value used as additional authenticated data
     * @return ciphertext followed by the authentication tag
     */
    private static byte[] encryptContent(byte[] plaintext, byte[] cek, byte[] iv, String protectedValue) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(
                    Cipher.ENCRYPT_MODE,
                    new SecretKeySpec(cek, "AES"),
                    new GCMParameterSpec(TAG_SIZE * 8, iv));
            cipher.updateAAD(protectedValue.getBytes(StandardCharsets.US_ASCII));
            return cipher.doFinal(plaintext);
        } catch (GeneralSecurityException exception) {
            throw new IllegalArgumentException("Unable to encrypt the version-2 JWE payload.", exception);
        }
    }

    /**
     * Decrypts authenticated AES-256-GCM content.
     *
     * @param encrypted ciphertext followed by the authentication tag
     * @param cek 32-byte content-encryption key
     * @param iv GCM initialization vector
     * @param protectedValue encoded protected-header value used as additional authenticated data
     * @return decrypted plaintext bytes
     */
    private static byte[] decryptContent(byte[] encrypted, byte[] cek, byte[] iv, String protectedValue) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(
                    Cipher.DECRYPT_MODE,
                    new SecretKeySpec(cek, "AES"),
                    new GCMParameterSpec(TAG_SIZE * 8, iv));
            cipher.updateAAD(protectedValue.getBytes(StandardCharsets.US_ASCII));
            return cipher.doFinal(encrypted);
        } catch (GeneralSecurityException exception) {
            throw new IllegalArgumentException("Failed to decrypt the version-2 JWE exchange.", exception);
        }
    }

    /**
     * Validates and copies a serialized recipient entry.
     *
     * @param value candidate recipient value
     * @param algorithm required recipient key-management algorithm
     * @return the validated recipient mapping
     */
    private static Map<String, Object> validateRecipient(Object value, String algorithm) {
        Map<String, Object> recipient = mapValue(value, "Version-2 recipient");
        if (!recipient.keySet().equals(Set.of("header", "encrypted_key"))) {
            throw new IllegalArgumentException(
                    "Version-2 recipients must contain only header and encrypted_key.");
        }
        Map<String, Object> header = mapValue(recipient.get("header"), "Version-2 recipient header");
        if (!algorithm.equals(header.get("alg"))) {
            throw new IllegalArgumentException(
                    "Version-2 recipient algorithm does not match the protected suite.");
        }
        stringValue(header.get("kid"), "Version-2 recipient header kid");
        byte[] encryptedKey = decodeBase64(
                stringValue(recipient.get("encrypted_key"), "recipient encrypted_key"),
                "recipient encrypted_key",
                false);
        if (encryptedKey.length != RECIPIENT_ENCRYPTED_KEY_SIZE) {
            throw new IllegalArgumentException(
                    "Recipient encrypted_key must decode to " + RECIPIENT_ENCRYPTED_KEY_SIZE
                            + " bytes, got " + encryptedKey.length + ".");
        }
        if (header.containsKey("epk")) {
            throw new IllegalArgumentException("ML-KEM recipients must not contain epk.");
        }
        return recipient;
    }

    /**
     * Requires the envelope to contain exactly the general-JWE members.
     *
     * <p>This method returns no value.</p>
     *
     * @param envelope candidate envelope mapping
     */
    private static void validateTopLevel(Map<String, ?> envelope) {
        if (envelope == null || !new HashSet<>(envelope.keySet()).equals(JWE_MEMBERS)) {
            throw new IllegalArgumentException(
                    "Version-2 JWE must contain only standard general JSON members.");
        }
    }

    /**
     * Validates the required authenticated version-two protected-header fields.
     *
     * <p>This method returns no value.</p>
     *
     * @param header candidate protected-header mapping
     */
    private static void validateProtectedHeader(Map<String, ?> header) {
        if (header == null) {
            throw new IllegalArgumentException("Version-2 protected header must be a JSON object.");
        }
        Set<String> missing = new HashSet<>(REQUIRED_PROTECTED_FIELDS);
        missing.removeAll(header.keySet());
        if (!missing.isEmpty()) {
            throw new IllegalArgumentException(
                    "Version-2 protected header is missing fields: " + String.join(", ", missing) + ".");
        }
        if (!EXCHANGE_V2_TYPE.equals(header.get("typ"))) {
            throw new IllegalArgumentException("Version-2 protected header has an unsupported typ.");
        }
        if (!EXCHANGE_V2_CONTENT_TYPE.equals(header.get("cty"))) {
            throw new IllegalArgumentException("Version-2 protected header has an unsupported cty.");
        }
        if (!EXCHANGE_V2_ENCRYPTION.equals(header.get("enc"))) {
            throw new IllegalArgumentException("Version-2 protected header must use A256GCM.");
        }
        if (!Integer.valueOf(EXCHANGE_V2_VERSION).equals(header.get("version"))) {
            throw new IllegalArgumentException("Version-2 protected header must declare version 2.");
        }
        if (!(header.get("cryptoSuite") instanceof String)) {
            throw new IllegalArgumentException("Version-2 protected header cryptoSuite must be a string.");
        }
        if (!(header.get("exchangeId") instanceof String exchangeId) || exchangeId.isEmpty()) {
            throw new IllegalArgumentException(
                    "Version-2 protected header exchangeId must be a non-empty string.");
        }
        if (header.containsKey("alg") || header.containsKey("kid") || header.containsKey("epk")) {
            throw new IllegalArgumentException(
                    "Version-2 key-management headers must be recipient-specific.");
        }
    }

    /**
     * Resolves the registered suite named by a protected header.
     *
     * @param header validated protected-header fields
     * @return the registered crypto suite
     */
    private static CryptoSuite suiteForHeader(Map<String, ?> header) {
        try {
            return CryptoSuite.fromId((String) header.get("cryptoSuite"));
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException("Version-2 protected header has an invalid crypto suite.", exception);
        }
    }

    /**
     * Selects the version-two recipient algorithm for a crypto suite.
     *
     * @param suite version-two crypto suite
     * @return the ML-KEM recipient algorithm identifier
     */
    private static String algorithmForSuite(CryptoSuite suite) {
        if (suite.getExchangeConfigVersion() != EXCHANGE_V2_VERSION) {
            throw new IllegalArgumentException(
                    "Suite '" + suite.getSuiteId() + "' does not use exchange configuration version 2.");
        }
        if (CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768.equals(suite.getExchangeKeyAgreement())) {
            return PURE_KEM_ALGORITHM;
        }
        throw new IllegalArgumentException(
                "Unsupported version-2 exchange agreement '" + suite.getExchangeKeyAgreement() + "'.");
    }

    /**
     * Parses JSON bytes as an object and adds a field-specific validation error.
     *
     * @param json UTF-8 JSON bytes
     * @param fieldName description used in validation errors
     * @return the parsed JSON object
     * @throws IllegalArgumentException if the bytes are not a valid JSON object
     */
    private static Map<String, Object> decodeJsonObject(byte[] json, String fieldName) {
        try {
            return readJsonObject(json);
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(fieldName + " is not valid JSON.", exception);
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
     * Copies a mapping whose keys are expected to be strings.
     *
     * @param value candidate mapping
     * @param fieldName field name used in validation errors
     * @return a mutable copy of the string-keyed mapping
     */
    private static Map<String, Object> copyStringMap(Map<String, ?> value, String fieldName) {
        if (value == null) {
            throw new IllegalArgumentException(fieldName + " must be a JSON object.");
        }
        Map<String, Object> copy = new LinkedHashMap<>();
        for (Map.Entry<String, ?> entry : value.entrySet()) {
            if (entry.getKey() == null) {
                throw new IllegalArgumentException(fieldName + " must contain string field names.");
            }
            copy.put(entry.getKey(), entry.getValue());
        }
        return copy;
    }

    /**
     * Requires a mapping value with string keys.
     *
     * @param value candidate mapping value
     * @param fieldName field name used in validation errors
     * @return a mutable copy of the string-keyed mapping
     */
    private static Map<String, Object> mapValue(Object value, String fieldName) {
        if (!(value instanceof Map<?, ?> map)) {
            throw new IllegalArgumentException(fieldName + " must be a JSON object.");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (!(entry.getKey() instanceof String key)) {
                throw new IllegalArgumentException(fieldName + " must contain string field names.");
            }
            result.put(key, entry.getValue());
        }
        return result;
    }

    /**
     * Requires a non-empty string value.
     *
     * @param value candidate value
     * @param fieldName field name used in validation errors
     * @return the validated string
     */
    private static String stringValue(Object value, String fieldName) {
        if (!(value instanceof String string) || string.isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must be a non-empty string.");
        }
        return string;
    }

    /**
     * Requires a string value while allowing it to be empty.
     *
     * @param value candidate value
     * @param fieldName field name used in validation errors
     * @return the validated string
     */
    private static String stringValueAllowEmpty(Object value, String fieldName) {
        if (!(value instanceof String string)) {
            throw new IllegalArgumentException(fieldName + " must be a string.");
        }
        return string;
    }

    /**
     * Decodes a canonical base64url value, optionally allowing an empty value.
     *
     * @param value encoded value
     * @param fieldName field name used in validation errors
     * @param allowEmpty whether empty input represents an empty byte array
     * @return decoded bytes
     * @throws IllegalArgumentException if the value is malformed or non-canonical
     */
    private static byte[] decodeBase64(String value, String fieldName, boolean allowEmpty) {
        if (value == null || (!allowEmpty && value.isEmpty())) {
            throw new IllegalArgumentException(fieldName + " must be non-empty base64url data.");
        }
        if (value.isEmpty()) {
            return new byte[0];
        }
        try {
            byte[] decoded = Base64.getUrlDecoder().decode(value);
            if (!value.equals(encodeBase64(decoded))) {
                throw new IllegalArgumentException(fieldName + " is not canonical base64url data.");
            }
            return decoded;
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(fieldName + " is not valid base64url data.", exception);
        }
    }

    /**
     * Encodes bytes as unpadded base64url.
     *
     * @param value bytes to encode
     * @return unpadded base64url text
     */
    private static String encodeBase64(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    /**
     * Generates cryptographically random bytes.
     *
     * @param length requested output length in bytes
     * @return the generated bytes
     */
    private static byte[] randomBytes(int length) {
        byte[] value = new byte[length];
        RANDOM.nextBytes(value);
        return value;
    }

    /**
     * Holds decrypted JWE values required by exchange processing.
     */
    static final class Decryption implements Serializable {
        private static final long serialVersionUID = 1L;

        private final byte[] plaintext;
        private final byte[] transportKey;
        private final byte[] cek;
        private final Map<String, Object> protectedHeader;

        /**
         * Creates a decryption result from plaintext, keys, and protected-header fields.
         *
         * @param plaintext decrypted exchange payload bytes
         * @param transportKey derived token transport key
         * @param cek JWE content-encryption key
         * @param protectedHeader authenticated protected-header fields
         */
        private Decryption(
                byte[] plaintext,
                byte[] transportKey,
                byte[] cek,
                Map<String, Object> protectedHeader) {
            this.plaintext = plaintext;
            this.transportKey = transportKey;
            this.cek = cek;
            this.protectedHeader = protectedHeader;
        }

        /**
         * Returns a defensive copy of the decrypted plaintext.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the decrypted payload bytes
         */
        byte[] plaintext() {
            return Arrays.copyOf(plaintext, plaintext.length);
        }

        /**
         * Returns a defensive copy of the token transport key.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the derived transport key
         */
        byte[] transportKey() {
            return Arrays.copyOf(transportKey, transportKey.length);
        }

        /**
         * Returns a defensive copy of the JWE content-encryption key.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return the content-encryption key
         */
        byte[] cek() {
            return Arrays.copyOf(cek, cek.length);
        }

        /**
         * Returns a mutable copy of the authenticated protected-header fields.
         *
         * <p>This method accepts no arguments.</p>
         *
         * @return a copy of the protected-header mapping
         */
        Map<String, Object> protectedHeader() {
            return new LinkedHashMap<>(protectedHeader);
        }
    }

    /**
     * Holds a recipient's encapsulated secret and serialized key material.
     *
     * @param sharedSecret encapsulated shared secret
     * @param ciphertext ML-KEM ciphertext
     */
    private record Encapsulation(byte[] sharedSecret, byte[] ciphertext)
            implements Serializable {
    }
}
