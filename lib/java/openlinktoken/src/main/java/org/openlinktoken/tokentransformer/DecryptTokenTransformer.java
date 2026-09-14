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
 * Transforms the token using AES-256 symmetric decryption.
 *
 * @see <a href=https://datatracker.ietf.org/doc/html/rfc3826>AES</a>
 */
public class DecryptTokenTransformer implements TokenTransformer {
    private static final long serialVersionUID = 1L;

    private static final Logger logger = LoggerFactory.getLogger(DecryptTokenTransformer.class);

    private final SecretKeySpec secretKey;

    /**
     * Initializes the underlying cipher (AES) with the decryption secret.
     *
     * @param encryptionKey the encryption key. The UTF-8 encoded key material must be exactly 32 bytes long.
     *
     * @throws InvalidKeyException                invalid encryption key
     * @throws InvalidAlgorithmParameterException invalid encryption algorithm
     *                                             parameters
     */
    public DecryptTokenTransformer(String encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this(toValidatedKeyBytes(encryptionKey));
    }

    /**
     * Initializes the underlying cipher (AES) with raw decryption key material.
     *
     * @param encryptionKey the raw encryption key bytes. The key must be exactly 32 bytes long.
     * @throws InvalidKeyException                invalid encryption key
     * @throws InvalidAlgorithmParameterException invalid encryption algorithm
     *                                             parameters
     */
    public DecryptTokenTransformer(byte[] encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this.secretKey = new SecretKeySpec(toValidatedKeyBytes(encryptionKey), EncryptionConstants.AES);
    }

    /**
     * Converts a string key to UTF-8 bytes and validates its length.
     *
     * @param encryptionKey the string encryption key
     * @return a defensive copy of the validated key bytes
     * @throws InvalidKeyException if the key is not exactly 32 bytes long
     */
    private static byte[] toValidatedKeyBytes(String encryptionKey) throws InvalidKeyException {
        return toValidatedKeyBytes(encryptionKey == null ? null : encryptionKey.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Validates and copies raw encryption key material.
     *
     * @param encryptionKey the raw encryption key bytes
     * @return a defensive copy of the validated key bytes
     * @throws InvalidKeyException if the key is not exactly 32 bytes long
     */
    private static byte[] toValidatedKeyBytes(byte[] encryptionKey) throws InvalidKeyException {
        if (encryptionKey == null || encryptionKey.length != EncryptionConstants.KEY_BYTE_LENGTH) {
            logger.error("Invalid Argument. Key must be {} bytes long", EncryptionConstants.KEY_BYTE_LENGTH);
            throw new InvalidKeyException(String.format("Key must be %s bytes long", EncryptionConstants.KEY_BYTE_LENGTH));
        }
        return Arrays.copyOf(encryptionKey, encryptionKey.length);
    }

    /**
     * Decryption token transformer.
     * <p>
     * Decrypts the token using AES-256 symmetric decryption algorithm.
     *
     * @return the decrypted token string.
     * @param token the encrypted token in base64 format.
     * @throws IllegalArgumentException        if the token does not contain the
     *                                         required IV and authentication tag
     * @throws IllegalStateException        if the underlying cipher is in an
     *                                      invalid state
     * @throws IllegalBlockSizeException    if the encrypted input cannot be
     *                                      processed as a complete block
     * @throws BadPaddingException          if the encrypted input has invalid
     *                                      padding or authentication data
     * @throws InvalidAlgorithmParameterException if the encryption parameters are
     *                                      invalid
     * @throws InvalidKeyException          if the encryption key is invalid
     * @throws NoSuchAlgorithmException     if the encryption algorithm is not
     *                                      available
     * @throws NoSuchPaddingException       if the encryption padding is not
     *                                      available
     */
    @Override
    public String transform(String token)
            throws IllegalStateException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException,
            InvalidAlgorithmParameterException, NoSuchAlgorithmException, NoSuchPaddingException {
        // Decode the base64-encoded token
        byte[] messageBytes = Base64.getDecoder().decode(token);

        int minimumMessageLength = EncryptionConstants.IV_SIZE + EncryptionConstants.TAG_LENGTH_BITS / Byte.SIZE;
        if (messageBytes.length < minimumMessageLength) {
            throw new IllegalArgumentException(
                    "Encrypted token is missing its initialization vector or authentication tag");
        }

        // Extract IV and ciphertext
        byte[] ivBytes = Arrays.copyOfRange(messageBytes, 0, EncryptionConstants.IV_SIZE);
        byte[] cipherBytes = Arrays.copyOfRange(messageBytes, EncryptionConstants.IV_SIZE, messageBytes.length);

        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(EncryptionConstants.TAG_LENGTH_BITS, ivBytes);

        // Initialize AES cipher in GCM mode with no padding for decryption
        Cipher cipher = Cipher.getInstance(EncryptionConstants.ENCRYPTION_ALGORITHM);
        cipher.init(Cipher.DECRYPT_MODE, this.secretKey, gcmParameterSpec);

        byte[] decryptedBytes = cipher.doFinal(cipherBytes);

        return new String(decryptedBytes, StandardCharsets.UTF_8);
    }
}
