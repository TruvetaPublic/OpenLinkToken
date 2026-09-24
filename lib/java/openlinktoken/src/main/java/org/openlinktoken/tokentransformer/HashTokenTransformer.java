/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Base64;
import java.util.Base64.Encoder;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Transforms the token using a cryptographic hash function with
 * a secret key.
 *
 * @see <a href=https://datatracker.ietf.org/doc/html/rfc4868>HMACSHA256</a>
 */
public class HashTokenTransformer implements TokenTransformer {
    private static final long serialVersionUID = 1L;
    private static final Logger logger = LoggerFactory.getLogger(HashTokenTransformer.class);

    private transient Mac mac;
    private transient Encoder encoder;
    private final byte[] hashingSecret;

    /**
     * Initializes the underlying MAC with the secret key.
     *
     * @param hashingSecret the cryptographic secret key.
     *
     * @throws java.security.NoSuchAlgorithmException invalid HMAC algorithm.
     * @throws java.security.InvalidKeyException      if the given key is
     *                                                inappropriate for
     *                                                initializing this HMAC.
     */
    public HashTokenTransformer(String hashingSecret) throws NoSuchAlgorithmException, InvalidKeyException {
        this(hashingSecret == null ? null : hashingSecret.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Initializes the underlying MAC with raw key bytes.
     *
     * @param hashingSecret the cryptographic secret key bytes.
     * @throws java.security.NoSuchAlgorithmException invalid HMAC algorithm.
     * @throws java.security.InvalidKeyException      if the given key is inappropriate for initializing this HMAC.
     */
    public HashTokenTransformer(byte[] hashingSecret) throws NoSuchAlgorithmException, InvalidKeyException {
        this.hashingSecret = hashingSecret == null ? null : Arrays.copyOf(hashingSecret, hashingSecret.length);
        rebuildMac();
    }

    /**
     * Hash token transformer.
     * <p>
     * The token is transformed using HMAC SHA256 algorithm.
     *
     * @param token the token to hash
     * @return hashed token in <code>base64</code> format.
     *
     * @throws java.lang.IllegalArgumentException <code>null</code> or blank token
     *                                            provided.
     * @throws java.lang.IllegalStateException    if the HMAC is not initialized
     *                                            properly.
     */
    @Override
    public String transform(String token) throws IllegalArgumentException, IllegalStateException {
        if (token == null || token.isBlank()) {
            logger.error("Invalid Argument. Token can't be Null.");
            throw new IllegalArgumentException("Invalid Argument. Token can't be Null.");
        }

        synchronized (this.mac) {
            byte[] dataAsBytes = token.getBytes(StandardCharsets.UTF_8);
            byte[] sha = this.mac.doFinal(dataAsBytes);
            return this.encoder.encodeToString(sha);
        }
    }

    /**
     * Writes the persistent hashing secret used to rebuild the transient MAC after deserialization.
     *
     * @param oos the object output stream
     * @throws IOException if serialization fails
     */
    private void writeObject(ObjectOutputStream oos) throws IOException {
        oos.defaultWriteObject(); // Serializes hashingSecret
    }

    // Custom deserialization
    /**
     * Restores the hashing secret and reconstructs the transient MAC state.
     *
     * @param ois the object input stream
     * @throws IOException if deserialization or MAC reconstruction fails
     * @throws ClassNotFoundException if a serialized class cannot be found
     */
    private void readObject(ObjectInputStream ois)
            throws IOException, ClassNotFoundException {
        ois.defaultReadObject(); // Deserializes hashingSecret
        try {
            rebuildMac();
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new IOException("Failed to reconstruct MAC", e);
        }
    }

    /**
     * Initializes the HMAC and Base64 encoder, or clears them when no secret is configured.
     *
     * @throws NoSuchAlgorithmException if HMAC-SHA256 is unavailable
     * @throws InvalidKeyException if the configured secret cannot initialize the MAC
     */
    private void rebuildMac() throws NoSuchAlgorithmException, InvalidKeyException {
        if (this.hashingSecret == null || this.hashingSecret.length == 0) {
            this.mac = null;
            this.encoder = null;
            return;
        }
        this.mac = Mac.getInstance("HmacSHA256");
        this.mac.init(new SecretKeySpec(this.hashingSecret, "HmacSHA256"));
        this.encoder = Base64.getEncoder();
    }

}
