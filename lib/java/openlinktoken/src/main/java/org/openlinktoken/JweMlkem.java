/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECPoint;
import java.security.spec.ECParameterSpec;
import java.security.spec.ECPublicKeySpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.crypto.Cipher;
import javax.crypto.KeyAgreement;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.bouncycastle.crypto.SecretWithEncapsulation;
import org.bouncycastle.crypto.digests.SHA256Digest;
import org.bouncycastle.crypto.engines.AESWrapEngine;
import org.bouncycastle.crypto.generators.HKDFBytesGenerator;
import org.bouncycastle.crypto.params.HKDFParameters;
import org.bouncycastle.crypto.params.KeyParameter;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMExtractor;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMGenerator;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMParameters;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMPrivateKeyParameters;
import org.bouncycastle.pqc.crypto.mlkem.MLKEMPublicKeyParameters;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Package-private standard JWE JSON support for version-two ML-KEM exchange envelopes.
 */
final class JweMlkem {

    static final int EXCHANGE_V2_VERSION = 2;
    static final String EXCHANGE_V2_TYPE = "openlinktoken-exchange+jwe";
    static final String EXCHANGE_V2_CONTENT_TYPE = "application/openlinktoken-exchange+json";
    static final String EXCHANGE_V2_ENCRYPTION = CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM;
    static final String PURE_KEM_ALGORITHM = CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768;
    static final String HYBRID_KEM_ALGORITHM = "ECDH-ES+" + CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768;
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

    private JweMlkem() {
    }

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

        String protectedValue = encodeBase64(JsonSupport.writeObject(header));
        byte[] cek = randomBytes(CEK_SIZE);
        byte[] iv = randomBytes(IV_SIZE);
        List<Map<String, Object>> serializedRecipients = recipients.stream()
                .map(bundle -> buildRecipient(bundle, algorithm, header, cek))
                .toList();
        byte[] encrypted = encryptContent(plaintext, cek, iv, protectedValue);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("protected", protectedValue);
        result.put("recipients", serializedRecipients);
        result.put("iv", encodeBase64(iv));
        result.put("ciphertext", encodeBase64(Arrays.copyOf(encrypted, encrypted.length - TAG_SIZE)));
        result.put("tag", encodeBase64(Arrays.copyOfRange(encrypted, encrypted.length - TAG_SIZE, encrypted.length)));
        return result;
    }

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
        if (HYBRID_KEM_ALGORITHM.equals(algorithm) && privateBundle.getEcPrivatePem() == null) {
            throw new IllegalArgumentException("Hybrid exchange key bundle is missing its EC private key.");
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

        byte[] sharedSecret = decapsulate(privateBundle, algorithm, encryptedKey, recipientHeader);
        byte[] kek = deriveRecipientKek(sharedSecret, protectedHeader, algorithm, (String) recipientHeader.get("kid"));
        byte[] cek = unwrap(kek, Arrays.copyOfRange(encryptedKey, MLKEM_CIPHERTEXT_SIZE, encryptedKey.length));
        byte[] encrypted = new byte[ciphertext.length + tag.length];
        System.arraycopy(ciphertext, 0, encrypted, 0, ciphertext.length);
        System.arraycopy(tag, 0, encrypted, ciphertext.length, tag.length);
        byte[] plaintext = decryptContent(encrypted, cek, iv, protectedValue);
        byte[] transportKey = deriveTokenTransportKey(cek, (String) protectedHeader.get("exchangeId"));
        return new Decryption(plaintext, transportKey, cek, protectedHeader);
    }

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

    private static Map<String, Object> buildRecipient(
            ExchangeKeyBundle bundle,
            String algorithm,
            Map<String, Object> protectedHeader,
            byte[] cek) {
        Encapsulation encapsulation = encapsulate(bundle, algorithm);
        byte[] kek = deriveRecipientKek(
                encapsulation.sharedSecret,
                protectedHeader,
                algorithm,
                bundle.getKid());
        byte[] wrappedCek = wrap(kek, cek);
        byte[] encryptedKey = new byte[encapsulation.ciphertext.length + wrappedCek.length];
        System.arraycopy(encapsulation.ciphertext, 0, encryptedKey, 0, encapsulation.ciphertext.length);
        System.arraycopy(wrappedCek, 0, encryptedKey, encapsulation.ciphertext.length, wrappedCek.length);

        Map<String, Object> header = new LinkedHashMap<>();
        header.put("alg", algorithm);
        header.put("kid", bundle.getKid());
        if (encapsulation.epk != null) {
            header.put("epk", encapsulation.epk);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("header", header);
        result.put("encrypted_key", encodeBase64(encryptedKey));
        return result;
    }

    private static Encapsulation encapsulate(ExchangeKeyBundle bundle, String algorithm) {
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
        if (PURE_KEM_ALGORITHM.equals(algorithm)) {
            return new Encapsulation(mlkemSecret, ciphertext, null);
        }

        PublicKey recipientPublic = EcKeyUtils.publicKeyFromPem(bundle.getEcPublicPem());
        KeyPair ephemeral = EcKeyUtils.generateKeyPair("P-256");
        byte[] ecdhSecret = deriveEcdhSecret(ephemeral.getPrivate(), recipientPublic);
        return new Encapsulation(
                concatenate(ecdhSecret, mlkemSecret),
                ciphertext,
                serializeEphemeralPublicKey((ECPublicKey) ephemeral.getPublic()));
    }

    private static byte[] decapsulate(
            ExchangeKeyBundle bundle,
            String algorithm,
            byte[] encryptedKey,
            Map<String, Object> recipientHeader) {
        if (encryptedKey.length != RECIPIENT_ENCRYPTED_KEY_SIZE) {
            throw new IllegalArgumentException(
                    "Recipient encrypted_key must be " + RECIPIENT_ENCRYPTED_KEY_SIZE
                            + " bytes, got " + encryptedKey.length + ".");
        }
        byte[] ciphertext = Arrays.copyOf(encryptedKey, MLKEM_CIPHERTEXT_SIZE);
        MLKEMPrivateKeyParameters privateKey;
        try {
            privateKey = new MLKEMPrivateKeyParameters(
                    MLKEMParameters.ml_kem_768,
                    bundle.getMlkemPrivateSeed());
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Exchange key bundle ML-KEM private seed is invalid.", exception);
        }
        byte[] mlkemSecret;
        try {
            mlkemSecret = new MLKEMExtractor(privateKey).extractSecret(ciphertext);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Unable to decapsulate ML-KEM-768.", exception);
        }
        if (PURE_KEM_ALGORITHM.equals(algorithm)) {
            return mlkemSecret;
        }

        PrivateKey privateEc = EcKeyUtils.privateKeyFromPem(bundle.getEcPrivatePem());
        PublicKey ephemeralPublic = parseEphemeralPublicKey(
                recipientHeader.get("epk"),
                ((ECPrivateKey) privateEc).getParams());
        return concatenate(deriveEcdhSecret(privateEc, ephemeralPublic), mlkemSecret);
    }

    private static byte[] deriveRecipientKek(
            byte[] sharedSecret,
            Map<String, Object> protectedHeader,
            String algorithm,
            String kid) {
        String info = String.join(
                ":",
                "openlinktoken",
                "jwe",
                "v2",
                (String) protectedHeader.get("cryptoSuite"),
                algorithm,
                kid);
        return hkdf(
                sharedSecret,
                ((String) protectedHeader.get("exchangeId")).getBytes(StandardCharsets.UTF_8),
                info.getBytes(StandardCharsets.US_ASCII),
                CEK_SIZE);
    }

    private static byte[] wrap(byte[] kek, byte[] cek) {
        try {
            AESWrapEngine wrapper = new AESWrapEngine();
            wrapper.init(true, new KeyParameter(kek));
            return wrapper.wrap(cek, 0, cek.length);
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Failed to wrap the version-2 JWE CEK.", exception);
        }
    }

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

    private static byte[] deriveEcdhSecret(PrivateKey privateKey, PublicKey publicKey) {
        try {
            KeyAgreement agreement = KeyAgreement.getInstance("ECDH");
            agreement.init(privateKey);
            agreement.doPhase(publicKey, true);
            return agreement.generateSecret();
        } catch (GeneralSecurityException exception) {
            throw new IllegalArgumentException("Unable to derive the P-256 ECDH secret.", exception);
        }
    }

    private static Map<String, Object> serializeEphemeralPublicKey(ECPublicKey publicKey) {
        Map<String, Object> epk = new LinkedHashMap<>();
        epk.put("kty", "EC");
        epk.put("crv", "P-256");
        epk.put("x", encodeBase64(toFixedLength(publicKey.getW().getAffineX(), 32, "epk.x")));
        epk.put("y", encodeBase64(toFixedLength(publicKey.getW().getAffineY(), 32, "epk.y")));
        return epk;
    }

    private static PublicKey parseEphemeralPublicKey(Object value, ECParameterSpec parameters) {
        Map<String, Object> epk = mapValue(value, "Hybrid recipient epk");
        if (!"EC".equals(epk.get("kty")) || !"P-256".equals(epk.get("crv"))) {
            throw new IllegalArgumentException("Hybrid recipient epk must be a P-256 EC JWK.");
        }
        if (epk.containsKey("d")) {
            throw new IllegalArgumentException("Recipient epk must not contain private key material.");
        }
        byte[] x = decodeBase64(stringValue(epk.get("x"), "recipient epk.x"), "recipient epk.x", false);
        byte[] y = decodeBase64(stringValue(epk.get("y"), "recipient epk.y"), "recipient epk.y", false);
        if (x.length != 32 || y.length != 32) {
            throw new IllegalArgumentException("Recipient epk coordinates must be 32 bytes.");
        }
        try {
            PublicKey publicKey = KeyFactory.getInstance("EC").generatePublic(new ECPublicKeySpec(
                    new ECPoint(new BigInteger(1, x), new BigInteger(1, y)),
                    parameters));
            if (!"P-256".equals(EcKeyUtils.curveName(publicKey))) {
                throw new IllegalArgumentException("Recipient epk must use P-256.");
            }
            return publicKey;
        } catch (GeneralSecurityException | IllegalArgumentException exception) {
            throw new IllegalArgumentException("Recipient epk is not a valid P-256 public key.", exception);
        }
    }

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
        if (HYBRID_KEM_ALGORITHM.equals(algorithm)) {
            validateEphemeralPublicKey(header.get("epk"));
        } else if (header.containsKey("epk")) {
            throw new IllegalArgumentException("Pure ML-KEM recipients must not contain epk.");
        }
        return recipient;
    }

    private static void validateEphemeralPublicKey(Object value) {
        Map<String, Object> epk = mapValue(value, "Hybrid recipient epk");
        if (!"EC".equals(epk.get("kty")) || !"P-256".equals(epk.get("crv"))) {
            throw new IllegalArgumentException("Hybrid recipient epk must be a P-256 EC JWK.");
        }
        if (epk.containsKey("d")) {
            throw new IllegalArgumentException("Recipient epk must not contain private key material.");
        }
        byte[] x = decodeBase64(stringValue(epk.get("x"), "recipient epk.x"), "recipient epk.x", false);
        byte[] y = decodeBase64(stringValue(epk.get("y"), "recipient epk.y"), "recipient epk.y", false);
        if (x.length != 32 || y.length != 32) {
            throw new IllegalArgumentException("Recipient epk coordinates must be 32 bytes.");
        }
    }

    private static void validateTopLevel(Map<String, ?> envelope) {
        if (envelope == null || !new HashSet<>(envelope.keySet()).equals(JWE_MEMBERS)) {
            throw new IllegalArgumentException(
                    "Version-2 JWE must contain only standard general JSON members.");
        }
    }

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

    private static CryptoSuite suiteForHeader(Map<String, ?> header) {
        try {
            return CryptoSuite.fromId((String) header.get("cryptoSuite"));
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException("Version-2 protected header has an invalid crypto suite.", exception);
        }
    }

    private static String algorithmForSuite(CryptoSuite suite) {
        if (suite.getExchangeConfigVersion() != EXCHANGE_V2_VERSION) {
            throw new IllegalArgumentException(
                    "Suite '" + suite.getSuiteId() + "' does not use exchange configuration version 2.");
        }
        if (CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768.equals(suite.getExchangeKeyAgreement())) {
            return PURE_KEM_ALGORITHM;
        }
        if (CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768.equals(suite.getExchangeKeyAgreement())) {
            return HYBRID_KEM_ALGORITHM;
        }
        throw new IllegalArgumentException(
                "Unsupported version-2 exchange agreement '" + suite.getExchangeKeyAgreement() + "'.");
    }

    private static Map<String, Object> decodeJsonObject(byte[] json, String fieldName) {
        try {
            return JsonSupport.readObject(json);
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(fieldName + " is not valid JSON.", exception);
        }
    }

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

    private static String stringValue(Object value, String fieldName) {
        if (!(value instanceof String string) || string.isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must be a non-empty string.");
        }
        return string;
    }

    private static String stringValueAllowEmpty(Object value, String fieldName) {
        if (!(value instanceof String string)) {
            throw new IllegalArgumentException(fieldName + " must be a string.");
        }
        return string;
    }

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

    private static String encodeBase64(byte[] value) {
        return CryptoEncoding.encodeBase64Url(value);
    }

    private static byte[] randomBytes(int length) {
        byte[] value = new byte[length];
        RANDOM.nextBytes(value);
        return value;
    }

    private static byte[] toFixedLength(BigInteger value, int length, String fieldName) {
        byte[] encoded = value.toByteArray();
        int offset = encoded.length > 1 && encoded[0] == 0 ? 1 : 0;
        if (encoded.length - offset > length) {
            throw new IllegalArgumentException(fieldName + " does not fit in " + length + " bytes.");
        }
        byte[] result = new byte[length];
        System.arraycopy(encoded, offset, result, length - (encoded.length - offset), encoded.length - offset);
        return result;
    }

    private static byte[] concatenate(byte[] first, byte[] second) {
        byte[] result = new byte[first.length + second.length];
        System.arraycopy(first, 0, result, 0, first.length);
        System.arraycopy(second, 0, result, first.length, second.length);
        return result;
    }

    static final class Decryption {
        private final byte[] plaintext;
        private final byte[] transportKey;
        private final byte[] cek;
        private final Map<String, Object> protectedHeader;

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

        byte[] plaintext() {
            return Arrays.copyOf(plaintext, plaintext.length);
        }

        byte[] transportKey() {
            return Arrays.copyOf(transportKey, transportKey.length);
        }

        byte[] cek() {
            return Arrays.copyOf(cek, cek.length);
        }

        Map<String, Object> protectedHeader() {
            return new LinkedHashMap<>(protectedHeader);
        }
    }

    private record Encapsulation(byte[] sharedSecret, byte[] ciphertext, Map<String, Object> epk) {
    }
}
