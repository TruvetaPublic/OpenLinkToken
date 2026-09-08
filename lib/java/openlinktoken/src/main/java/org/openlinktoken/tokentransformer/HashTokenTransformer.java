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
import org.bouncycastle.crypto.macs.KMAC;
import org.bouncycastle.crypto.params.KeyParameter;

import org.openlinktoken.crypto.CryptoSuite;

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
    private String macAlgorithm;

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
        this(hashingSecret == null ? null : hashingSecret.getBytes(StandardCharsets.UTF_8), CryptoSuite.defaultSuite());
    }

    /**
     * Initializes the underlying MAC with raw key bytes.
     *
     * @param hashingSecret the cryptographic secret key bytes.
     * @throws java.security.NoSuchAlgorithmException invalid HMAC algorithm.
     * @throws java.security.InvalidKeyException      if the given key is inappropriate for initializing this HMAC.
     */
    public HashTokenTransformer(byte[] hashingSecret) throws NoSuchAlgorithmException, InvalidKeyException {
        this(hashingSecret, CryptoSuite.defaultSuite());
    }

    /**
     * Initializes the underlying MAC using an explicit crypto suite.
     *
     * @param hashingSecret the cryptographic secret key bytes
     * @param cryptoSuite the suite selecting the keyed MAC
     * @throws NoSuchAlgorithmException invalid HMAC algorithm
     * @throws InvalidKeyException if the given key is inappropriate for initializing this HMAC
     */
    public HashTokenTransformer(byte[] hashingSecret, CryptoSuite cryptoSuite)
            throws NoSuchAlgorithmException, InvalidKeyException {
        this.hashingSecret = hashingSecret == null ? null : Arrays.copyOf(hashingSecret, hashingSecret.length);
        this.macAlgorithm = macAlgorithm(cryptoSuite);
        rebuildMac();
    }

    /**
     * Hash token transformer.
     * <p>
     * The token is transformed using HMAC SHA256 algorithm.
     *
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

        synchronized (this) {
            if ("KMAC256".equals(this.macAlgorithm)) {
                KMAC kmac = new KMAC(256, new byte[0]);
                kmac.init(new KeyParameter(this.hashingSecret));
                byte[] dataAsBytes = token.getBytes(StandardCharsets.UTF_8);
                kmac.update(dataAsBytes, 0, dataAsBytes.length);
                byte[] output = new byte[32];
                kmac.doFinal(output, 0, output.length);
                return this.encoder.encodeToString(output);
            }

            byte[] dataAsBytes = token.getBytes(StandardCharsets.UTF_8);
            byte[] sha = this.mac.doFinal(dataAsBytes);
            return this.encoder.encodeToString(sha);
        }
    }

    private void writeObject(ObjectOutputStream oos) throws IOException {
        oos.defaultWriteObject(); // Serializes hashingSecret
    }

    // Custom deserialization
    private void readObject(ObjectInputStream ois)
            throws IOException, ClassNotFoundException {
        ois.defaultReadObject(); // Deserializes hashingSecret
        try {
            rebuildMac();
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new IOException("Failed to reconstruct MAC", e);
        }
    }

    private void rebuildMac() throws NoSuchAlgorithmException, InvalidKeyException {
        if (this.hashingSecret == null || this.hashingSecret.length == 0) {
            this.mac = null;
            this.encoder = null;
            return;
        }
        if ("KMAC256".equals(this.macAlgorithm)) {
            if (this.hashingSecret.length < 32) {
                throw new InvalidKeyException("KMAC256 requires a hashing secret of at least 32 bytes.");
            }
            this.mac = null;
        } else {
            this.mac = Mac.getInstance(macAlgorithm);
            this.mac.init(new SecretKeySpec(this.hashingSecret, macAlgorithm));
        }
        this.encoder = Base64.getEncoder();
    }

    private static String macAlgorithm(CryptoSuite cryptoSuite) throws NoSuchAlgorithmException {
        return switch (cryptoSuite.getTokenMacAlgorithm()) {
            case "HS256" -> "HmacSHA256";
            case "HS3-256" -> "HmacSHA3-256";
            case "KMAC256-256" -> "KMAC256";
            default -> throw new NoSuchAlgorithmException(
                    "Unsupported token MAC algorithm: " + cryptoSuite.getTokenMacAlgorithm());
        };
    }

}
