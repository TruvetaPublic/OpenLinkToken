/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.apache.commons.lang3.SerializationUtils;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Tests AES-GCM encryption key validation, serialization, and token round trips. */
class EncryptTokenTransformerTest {
    private EncryptTokenTransformer transformer;
    private static final String VALID_KEY = "12345678901234567890123456789012"; // 32-byte key
    private static final String INVALID_KEY = "short-key"; // Invalid short key

    /** Creates an encryptor with a valid 32-byte key for each test. */
    @BeforeEach
    void setUp() throws Exception {
        transformer = new EncryptTokenTransformer(VALID_KEY);
    }

    /** Verifies a serialized encryptor can still produce a Base64-encoded token. */
    @Test
    void testSerializable() throws Exception {
        TokenTransformer encryptTokenTransformer = new EncryptTokenTransformer(VALID_KEY);
        byte[] serialized = SerializationUtils.serialize(encryptTokenTransformer);
        TokenTransformer deserialized = SerializationUtils.deserialize(serialized);

        String token = "mySecretToken";
        String encryptedToken = deserialized.transform(token);

        // Ensure the encrypted token is not null or empty
        Assertions.assertNotNull(encryptedToken);
        Assertions.assertFalse(encryptedToken.isEmpty());

        // check if the token is base64-encoded by decoding it
        byte[] decodedBytes = Base64.getDecoder().decode(encryptedToken);
        Assertions.assertNotNull(decodedBytes);
    }

    /** Verifies construction accepts a valid string key. */
    @Test
    void testConstructor_ValidKey_Success() throws Exception {
        EncryptTokenTransformer validTransformer = new EncryptTokenTransformer(VALID_KEY);
        Assertions.assertNotNull(validTransformer);
    }

    /** Verifies construction accepts a raw 32-byte key. */
    @Test
    void testConstructor_Raw32ByteKey_Success() throws Exception {
        EncryptTokenTransformer validTransformer = new EncryptTokenTransformer(VALID_KEY.getBytes(StandardCharsets.UTF_8));
        Assertions.assertNotNull(validTransformer);
    }

    /** Verifies a short key is rejected with an invalid-key error. */
    @Test
    void testConstructor_InvalidKeyLength_ThrowsIllegalArgumentException() {
        Exception exception = Assertions.assertThrows(InvalidKeyException.class, () -> {
            new EncryptTokenTransformer(INVALID_KEY); // Key is too short
        });
        Assertions.assertEquals("Key must be 32 bytes long", exception.getMessage());
    }

    /** Verifies a 32-character non-ASCII key is rejected when its UTF-8 length is not 32 bytes. */
    @Test
    void testConstructor_NonAscii32CharacterKey_ThrowsInvalidKeyException() {
        String invalidUtf8LengthKey = "é".repeat(32);

        Exception exception = Assertions.assertThrows(InvalidKeyException.class, () -> {
            new EncryptTokenTransformer(invalidUtf8LengthKey);
        });
        Assertions.assertEquals("Key must be 32 bytes long", exception.getMessage());
    }

    /** Verifies a valid token is encrypted to a nonempty Base64 value. */
    @Test
    void testTransform_ValidToken_ReturnsEncryptedToken() throws Exception {
        String token = "mySecretToken";
        String encryptedToken = transformer.transform(token);

        // Ensure the encrypted token is not null or empty
        Assertions.assertNotNull(encryptedToken);
        Assertions.assertFalse(encryptedToken.isEmpty());

        // check if the token is base64-encoded by decoding it
        byte[] decodedBytes = Base64.getDecoder().decode(encryptedToken);
        Assertions.assertNotNull(decodedBytes);
    }

    /** Verifies an encrypted token can be decrypted with the matching AES-GCM parameters. */
    @Test
    void testTransform_ReversibleEncryption() throws Exception {
        // Testing if encryption followed by decryption will give back the original
        // token.
        String token = "mySecretToken";

        String encryptedToken = transformer.transform(token); // Encrypt the token

        byte[] messageBytes = Base64.getDecoder().decode(encryptedToken);
        byte[] iv = new byte[12];
        byte[] cipherBytes = new byte[messageBytes.length - 12];

        System.arraycopy(messageBytes, 0, iv, 0, 12);
        System.arraycopy(messageBytes, 12, cipherBytes, 0, cipherBytes.length);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding"); // Decrypt the token using the same settings
        SecretKeySpec secretKey = new SecretKeySpec(VALID_KEY.getBytes(StandardCharsets.UTF_8), "AES");
        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(128, iv);
        cipher.init(Cipher.DECRYPT_MODE, secretKey, gcmParameterSpec);

        byte[] decryptedBytes = cipher.doFinal(cipherBytes);
        String decryptedToken = new String(decryptedBytes, StandardCharsets.UTF_8);

        Assertions.assertEquals(token, decryptedToken); // Ensure the decrypted token matches the original token
    }
}
