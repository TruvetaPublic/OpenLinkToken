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
     * @throws java.security.InvalidKeyException                invalid encryption
     *                                                          key.
     * @throws java.security.InvalidAlgorithmParameterException invalid encryption
     *                                                          algorithm
     *                                                          parameters.
     */
    public DecryptTokenTransformer(String encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this(toValidatedKeyBytes(encryptionKey));
    }

    /**
     * Initializes the underlying cipher (AES) with raw decryption key material.
     *
     * @param encryptionKey the raw encryption key bytes. The key must be exactly 32 bytes long.
     * @throws java.security.InvalidKeyException                invalid encryption key.
     * @throws java.security.InvalidAlgorithmParameterException invalid encryption algorithm parameters.
     */
    public DecryptTokenTransformer(byte[] encryptionKey)
            throws InvalidKeyException, InvalidAlgorithmParameterException {
        this.secretKey = new SecretKeySpec(toValidatedKeyBytes(encryptionKey), EncryptionConstants.AES);
    }

    private static byte[] toValidatedKeyBytes(String encryptionKey) throws InvalidKeyException {
        return toValidatedKeyBytes(encryptionKey == null ? null : encryptionKey.getBytes(StandardCharsets.UTF_8));
    }

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
     * @throws java.lang.IllegalStateException        the underlying cipher
     *                                                is in a wrong state.
     * @throws javax.crypto.IllegalBlockSizeException if this cipher is a block
     *                                                cipher,
     *                                                no padding has been requested
     *                                                (only in encryption mode), and
     *                                                the total
     *                                                input length of the data
     *                                                processed by this cipher is
     *                                                not a multiple of
     *                                                block size; or if this
     *                                                encryption algorithm is unable
     *                                                to
     *                                                process the input data
     *                                                provided.
     * @throws javax.crypto.BadPaddingException       invalid padding size.
     * @throws InvalidAlgorithmParameterException     invalid encryption
     * @throws InvalidKeyException                    invalid encryption key.
     * @throws java.security.NoSuchAlgorithmException invalid encryption
     *                                                algorithm/mode.
     * @throws javax.crypto.NoSuchPaddingException    invalid encryption
     *                                                algorithm padding.
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
