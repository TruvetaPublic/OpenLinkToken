/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import java.nio.charset.StandardCharsets;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Base64;
import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Decrypts tokens produced with AES-256 GCM.
 *
 * @see <a href=https://datatracker.ietf.org/doc/html/rfc3826>AES</a>
 */
public class DecryptTokenTransformer implements TokenTransformer {
    private static final long serialVersionUID = 1L;

    private static final Logger logger = LoggerFactory.getLogger(DecryptTokenTransformer.class);

    private final SecretKeySpec secretKey;

    /**
     * Stores an AES-256 decryption key encoded as UTF-8.
     *
     * @param encryptionKey key text whose UTF-8 encoding is exactly 32 bytes
     * @throws InvalidKeyException if the key is {@code null} or its UTF-8 encoding is not 32 bytes
     */
    public DecryptTokenTransformer(String encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this(toValidatedKeyBytes(encryptionKey));
    }

    /**
     * Stores validated raw AES-256 decryption key material.
     *
     * @param encryptionKey raw key material that must be exactly 32 bytes
     * @throws InvalidKeyException if the key is {@code null} or not 32 bytes long
     */
    public DecryptTokenTransformer(byte[] encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this.secretKey = new SecretKeySpec(toValidatedKeyBytes(encryptionKey), EncryptionConstants.AES);
    }

    /**
     * Converts a string key to UTF-8 bytes before validating its length.
     *
     * @param encryptionKey the encryption key string
     * @return a copy of the encoded key bytes
     * @throws InvalidKeyException if the key is {@code null} or does not encode to 32 bytes
     */
    private static byte[] toValidatedKeyBytes(String encryptionKey) throws InvalidKeyException {
        return toValidatedKeyBytes(encryptionKey == null ? null : encryptionKey.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Validates and copies raw AES-256 key material.
     *
     * @param encryptionKey the raw key bytes
     * @return a defensive copy of the key bytes
     * @throws InvalidKeyException if the key is {@code null} or not 32 bytes long
     */
    private static byte[] toValidatedKeyBytes(byte[] encryptionKey) throws InvalidKeyException {
        if (encryptionKey == null || encryptionKey.length != EncryptionConstants.KEY_BYTE_LENGTH) {
            logger.error("Invalid Argument. Key must be {} bytes long", EncryptionConstants.KEY_BYTE_LENGTH);
            throw new InvalidKeyException(String.format("Key must be %s bytes long", EncryptionConstants.KEY_BYTE_LENGTH));
        }
        return Arrays.copyOf(encryptionKey, encryptionKey.length);
    }

    /**
     * Decrypts a Base64 token containing the GCM initialization vector and ciphertext.
     *
     * @param token Base64 encoding of the initialization vector and ciphertext
     * @return the decrypted token as UTF-8 text
     * @throws NullPointerException if {@code token} is {@code null}
     * @throws IllegalArgumentException if {@code token} is not valid Base64
     * @throws IllegalStateException if the cipher cannot process the input in its current state
     * @throws IllegalBlockSizeException if the cipher cannot process the ciphertext
     * @throws BadPaddingException if GCM authentication fails
     * @throws InvalidKeyException if the configured key is invalid
     * @throws InvalidAlgorithmParameterException if the initialization vector cannot initialize GCM
     * @throws NoSuchAlgorithmException if AES/GCM is unavailable
     * @throws NoSuchPaddingException if the cipher transformation is unavailable
     */
    @Override
    public String transform(String token)
            throws IllegalStateException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException,
            InvalidAlgorithmParameterException, NoSuchAlgorithmException, NoSuchPaddingException {
        // Decode the base64-encoded token
        byte[] messageBytes = Base64.getDecoder().decode(token);

        // Extract IV and ciphertext
        byte[] ivBytes = new byte[EncryptionConstants.IV_SIZE];
        byte[] cipherBytes = new byte[messageBytes.length - EncryptionConstants.IV_SIZE];

        System.arraycopy(messageBytes, 0, ivBytes, 0, EncryptionConstants.IV_SIZE);
        System.arraycopy(messageBytes, EncryptionConstants.IV_SIZE, cipherBytes, 0, cipherBytes.length);

        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(EncryptionConstants.TAG_LENGTH_BITS, ivBytes);

        // Initialize AES cipher in GCM mode with no padding for decryption
        Cipher cipher = Cipher.getInstance(EncryptionConstants.ENCRYPTION_ALGORITHM);
        cipher.init(Cipher.DECRYPT_MODE, this.secretKey, gcmParameterSpec);

        byte[] decryptedBytes = cipher.doFinal(cipherBytes);

        return new String(decryptedBytes, StandardCharsets.UTF_8);
    }
}
