/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import java.nio.charset.StandardCharsets;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.security.SecureRandom;
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
 * Encrypts tokens with AES-256 GCM.
 *
 * @see <a href=https://datatracker.ietf.org/doc/html/rfc3826>AES</a>
 */
public class EncryptTokenTransformer implements TokenTransformer {
    private static final long serialVersionUID = 1L;

    private static final Logger logger = LoggerFactory.getLogger(EncryptTokenTransformer.class);

    private final SecretKeySpec secretKey;

    private final SecureRandom secureRandom;

    /**
     * Stores an AES-256 encryption key encoded as UTF-8.
     *
     * @param encryptionKey key text whose UTF-8 encoding is exactly 32 bytes
     * @throws InvalidKeyException if the key is {@code null} or its UTF-8 encoding is not 32 bytes
     */
    public EncryptTokenTransformer(String encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this(toValidatedKeyBytes(encryptionKey));
    }

    /**
     * Stores validated raw AES-256 encryption key material.
     *
     * @param encryptionKey raw key material that must be exactly 32 bytes
     * @throws InvalidKeyException if the key is {@code null} or not 32 bytes long
     */
    public EncryptTokenTransformer(byte[] encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        secureRandom = new SecureRandom();
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
     * Encrypts UTF-8 plaintext with AES-256 GCM and Base64-encodes the IV and ciphertext.
     *
     * @param token the plaintext token
     * @return Base64 encoding of the generated IV and ciphertext
     * @throws NullPointerException if {@code token} is {@code null}
     * @throws IllegalStateException if the cipher cannot process the input in its current state
     * @throws IllegalBlockSizeException if the cipher cannot process the plaintext
     * @throws BadPaddingException if the cipher cannot finalize encryption
     * @throws InvalidKeyException if the configured key is invalid
     * @throws InvalidAlgorithmParameterException if the initialization vector cannot initialize GCM
     * @throws NoSuchAlgorithmException if AES/GCM is unavailable
     * @throws NoSuchPaddingException if the cipher transformation is unavailable
     */
    @Override
    public String transform(String token)
            throws IllegalStateException, IllegalBlockSizeException, BadPaddingException, InvalidKeyException,
            InvalidAlgorithmParameterException, NoSuchAlgorithmException, NoSuchPaddingException {
        // Generate random IV (for AES block size)
        byte[] ivBytes = new byte[EncryptionConstants.IV_SIZE];
        secureRandom.nextBytes(ivBytes);

        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(EncryptionConstants.TAG_LENGTH_BITS, ivBytes);

        // Initialize AES cipher in GCM mode with no padding for encryption
        Cipher cipher = Cipher.getInstance(EncryptionConstants.ENCRYPTION_ALGORITHM);
        // Initialize the cipher for encryption
        cipher.init(Cipher.ENCRYPT_MODE, this.secretKey, gcmParameterSpec);

        byte[] encryptedBytes = cipher.doFinal(token.getBytes(StandardCharsets.UTF_8));

        byte[] messageBytes = new byte[EncryptionConstants.IV_SIZE + encryptedBytes.length];

        System.arraycopy(ivBytes, 0, messageBytes, 0, EncryptionConstants.IV_SIZE);
        System.arraycopy(encryptedBytes, 0, messageBytes, EncryptionConstants.IV_SIZE, encryptedBytes.length);

        return Base64.getEncoder().encodeToString(messageBytes);
    }
}
