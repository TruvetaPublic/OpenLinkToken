/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import java.security.InvalidKeyException;

import org.apache.commons.lang3.SerializationUtils;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Tests AES-GCM decryption key validation, serialization, and token round trips. */
class DecryptTokenTransformerTest {
    private DecryptTokenTransformer decryptor;
    private EncryptTokenTransformer encryptor;
    private static final String VALID_KEY = "12345678901234567890123456789012"; // 32-byte key
    private static final String INVALID_KEY = "short-key"; // Invalid short key

    /** Creates matching encryptor and decryptor instances with a valid key. */
    @BeforeEach
    void setUp() throws Exception {
        decryptor = new DecryptTokenTransformer(VALID_KEY);
        encryptor = new EncryptTokenTransformer(VALID_KEY);
    }

    /** Verifies a serialized decryptor can decrypt a token encrypted with the matching key. */
    @Test
    void testSerializable() throws Exception {
        TokenTransformer decryptTokenTransformer = new DecryptTokenTransformer(VALID_KEY);
        byte[] serialized = SerializationUtils.serialize(decryptTokenTransformer);
        TokenTransformer deserialized = SerializationUtils.deserialize(serialized);

        // First encrypt a token
        String token = "mySecretToken";
        String encryptedToken = encryptor.transform(token);

        // Then decrypt using deserialized transformer
        String decryptedToken = deserialized.transform(encryptedToken);

        Assertions.assertEquals(token, decryptedToken);
    }

    /** Verifies construction accepts a valid string key. */
    @Test
    void testConstructor_ValidKey_Success() throws Exception {
        DecryptTokenTransformer validTransformer = new DecryptTokenTransformer(VALID_KEY);
        Assertions.assertNotNull(validTransformer);
    }

    /** Verifies construction accepts a raw 32-byte key. */
    @Test
    void testConstructor_Raw32ByteKey_Success() throws Exception {
        DecryptTokenTransformer validTransformer = new DecryptTokenTransformer(VALID_KEY.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        Assertions.assertNotNull(validTransformer);
    }

    /** Verifies a short key is rejected with an invalid-key error. */
    @Test
    void testConstructor_InvalidKeyLength_ThrowsIllegalArgumentException() {
        Exception exception = Assertions.assertThrows(InvalidKeyException.class, () -> {
            new DecryptTokenTransformer(INVALID_KEY); // Key is too short
        });
        Assertions.assertEquals("Key must be 32 bytes long", exception.getMessage());
    }

    /** Verifies a 32-character non-ASCII key is rejected when its UTF-8 length is not 32 bytes. */
    @Test
    void testConstructor_NonAscii32CharacterKey_ThrowsInvalidKeyException() {
        String invalidUtf8LengthKey = "é".repeat(32);

        Exception exception = Assertions.assertThrows(InvalidKeyException.class, () -> {
            new DecryptTokenTransformer(invalidUtf8LengthKey);
        });
        Assertions.assertEquals("Key must be 32 bytes long", exception.getMessage());
    }

    /** Verifies a valid encrypted token decrypts to its original value. */
    @Test
    void testTransform_ValidEncryptedToken_ReturnsDecryptedToken() throws Exception {
        String originalToken = "mySecretToken";

        // Encrypt the token first
        String encryptedToken = encryptor.transform(originalToken);

        // Now decrypt it
        String decryptedToken = decryptor.transform(encryptedToken);

        Assertions.assertEquals(originalToken, decryptedToken);
    }

    /** Verifies several independently encrypted tokens decrypt to their corresponding inputs. */
    @Test
    void testTransform_MultipleTokens_DecryptsCorrectly() throws Exception {
        String token1 = "firstToken";
        String token2 = "secondToken";
        String token3 = "thirdToken";

        // Encrypt all tokens
        String encrypted1 = encryptor.transform(token1);
        String encrypted2 = encryptor.transform(token2);
        String encrypted3 = encryptor.transform(token3);

        // Decrypt all tokens
        String decrypted1 = decryptor.transform(encrypted1);
        String decrypted2 = decryptor.transform(encrypted2);
        String decrypted3 = decryptor.transform(encrypted3);

        // Verify all decryptions
        Assertions.assertEquals(token1, decrypted1);
        Assertions.assertEquals(token2, decrypted2);
        Assertions.assertEquals(token3, decrypted3);
    }

    /** Verifies separate encryptions of one token remain decryptable despite distinct random IVs. */
    @Test
    void testTransform_SameTokenEncryptedTwice_BothDecryptCorrectly() throws Exception {
        String originalToken = "sameToken";

        // Encrypt the same token twice (should produce different encrypted values due to random IV)
        String encrypted1 = encryptor.transform(originalToken);
        String encrypted2 = encryptor.transform(originalToken);

        // Both encrypted tokens should be different
        Assertions.assertNotEquals(encrypted1, encrypted2);

        // But both should decrypt to the same original token
        String decrypted1 = decryptor.transform(encrypted1);
        String decrypted2 = decryptor.transform(encrypted2);

        Assertions.assertEquals(originalToken, decrypted1);
        Assertions.assertEquals(originalToken, decrypted2);
    }

    /** Verifies tokens containing punctuation and delimiters survive encryption and decryption. */
    @Test
    void testTransform_SpecialCharacters_DecryptsCorrectly() throws Exception {
        String specialToken = "token|with|pipes|and|special!@#$%^&*()_+characters";

        String encrypted = encryptor.transform(specialToken);
        String decrypted = decryptor.transform(encrypted);

        Assertions.assertEquals(specialToken, decrypted);
    }

    /** Verifies Unicode text survives encryption and decryption. */
    @Test
    void testTransform_UnicodeCharacters_DecryptsCorrectly() throws Exception {
        String unicodeToken = "token-with-unicode-你好-мир-🎉";

        String encrypted = encryptor.transform(unicodeToken);
        String decrypted = decryptor.transform(encrypted);

        Assertions.assertEquals(unicodeToken, decrypted);
    }

    /** Verifies decryption with a different key fails authentication. */
    @Test
    void testTransform_WrongKey_ThrowsException() throws Exception {
        String originalToken = "mySecretToken";

        // Encrypt with one key
        String encryptedToken = encryptor.transform(originalToken);

        // Try to decrypt with a different key
        DecryptTokenTransformer wrongDecryptor = new DecryptTokenTransformer("00000000000000000000000000000000");

        // Should throw an exception
        Assertions.assertThrows(Exception.class, () -> {
            wrongDecryptor.transform(encryptedToken);
        });
    }
}
