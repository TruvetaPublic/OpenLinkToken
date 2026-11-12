/* SPDX-License-Identifier: MIT */
package org.openlinktoken.crypto;

import java.io.InvalidObjectException;
import java.io.Serializable;
import java.util.List;
import java.util.Map;

/**
 * Immutable contract for token primitives and exchange key establishment.
 */
public final class CryptoSuite implements Serializable {
    private static final long serialVersionUID = 1L;

    /** SHA-256 token digest identifier. */
    public static final String TOKEN_DIGEST_SHA256 = "SHA-256";

    /** SHA3-256 token digest identifier. */
    public static final String TOKEN_DIGEST_SHA3_256 = "SHA3-256";

    /** SHAKE256-256 token digest identifier. */
    public static final String TOKEN_DIGEST_SHAKE256_256 = "SHAKE256-256";

    /** HMAC-SHA256 token MAC identifier. */
    public static final String TOKEN_MAC_HS256 = "HS256";

    /** HMAC-SHA3-256 token MAC identifier. */
    public static final String TOKEN_MAC_HS3_256 = "HS3-256";

    /** KMAC256-256 token MAC identifier. */
    public static final String TOKEN_MAC_KMAC256_256 = "KMAC256-256";

    /** KMAC256 token MAC family prefix. */
    public static final String TOKEN_MAC_KMAC256_PREFIX = "KMAC256";

    /** AES-256-GCM token content-encryption identifier. */
    public static final String TOKEN_CONTENT_ENCRYPTION_A256GCM = "A256GCM";

    /** ECDH exchange key-agreement identifier. */
    public static final String EXCHANGE_KEY_AGREEMENT_ECDH = "ECDH";

    /** ML-KEM-768 exchange key-agreement identifier. */
    public static final String EXCHANGE_KEY_AGREEMENT_MLKEM768 = "ML-KEM-768";

    /** ML-KEM exchange key-agreement family prefix. */
    public static final String EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX = "ML-KEM";

    /** The SHA-256 and ECDH crypto suite. */
    public static final CryptoSuite ECDH_SHA256 =
            new CryptoSuite(
                    "ecdh-sha256",
                    TOKEN_DIGEST_SHA256,
                    TOKEN_MAC_HS256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_ECDH,
                    1);

    /** The SHA-3-256 and ECDH crypto suite. */
    public static final CryptoSuite ECDH_SHA3_256 =
            new CryptoSuite(
                    "ecdh-sha3-256",
                    TOKEN_DIGEST_SHA3_256,
                    TOKEN_MAC_HS3_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_ECDH,
                    1);

    /** The SHAKE256 and ML-KEM-768 crypto suite. */
    public static final CryptoSuite MLKEM768_SHAKE256 =
            new CryptoSuite(
                    "mlkem768-shake256",
                    TOKEN_DIGEST_SHAKE256_256,
                    TOKEN_MAC_KMAC256_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_MLKEM768,
                    2);

    /** The SHA-3-256 and ML-KEM-768 crypto suite. */
    public static final CryptoSuite MLKEM768_SHA3_256 =
            new CryptoSuite(
                    "mlkem768-sha3-256",
                    TOKEN_DIGEST_SHA3_256,
                    TOKEN_MAC_HS3_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_MLKEM768,
                    2);

    private static final Map<String, CryptoSuite> REGISTRY = Map.of(
            ECDH_SHA256.getSuiteId(),
            ECDH_SHA256,
            ECDH_SHA3_256.getSuiteId(),
            ECDH_SHA3_256,
            MLKEM768_SHAKE256.getSuiteId(),
            MLKEM768_SHAKE256,
            MLKEM768_SHA3_256.getSuiteId(),
            MLKEM768_SHA3_256);

    private final String suiteId;
    private final String tokenDigestAlgorithm;
    private final String tokenMacAlgorithm;
    private final String tokenContentEncryption;
    private final String exchangeKeyAgreement;
    private final int exchangeConfigVersion;

    /**
     * Creates an immutable crypto suite definition.
     *
     * @param suiteId the stable suite identifier
     * @param tokenDigestAlgorithm the digest algorithm used for tokenization
     * @param tokenMacAlgorithm the keyed MAC algorithm used for token transformation
     * @param tokenContentEncryption the content-encryption algorithm used for match tokens
     * @param exchangeKeyAgreement the key-agreement mechanism used for exchanges
     * @param exchangeConfigVersion the exchange configuration version
     */
    CryptoSuite(
            String suiteId,
            String tokenDigestAlgorithm,
            String tokenMacAlgorithm,
            String tokenContentEncryption,
            String exchangeKeyAgreement,
            int exchangeConfigVersion) {
        this.suiteId = suiteId;
        this.tokenDigestAlgorithm = tokenDigestAlgorithm;
        this.tokenMacAlgorithm = tokenMacAlgorithm;
        this.tokenContentEncryption = tokenContentEncryption;
        this.exchangeKeyAgreement = exchangeKeyAgreement;
        this.exchangeConfigVersion = exchangeConfigVersion;
        validate();
    }

    /**
     * Validates supported token algorithms and the exchange-version contract.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return this validated suite
     * @throws IllegalArgumentException if a token algorithm or exchange version is unsupported
     */
    public CryptoSuite validate() {
        if (!TOKEN_DIGEST_SHA256.equals(tokenDigestAlgorithm)
                && !TOKEN_DIGEST_SHA3_256.equals(tokenDigestAlgorithm)
                && !TOKEN_DIGEST_SHAKE256_256.equals(tokenDigestAlgorithm)) {
            throw new IllegalArgumentException(
                    "Unsupported token digest algorithm '" + tokenDigestAlgorithm + "'.");
        }
        if (!TOKEN_MAC_HS256.equals(tokenMacAlgorithm)
                && !TOKEN_MAC_HS3_256.equals(tokenMacAlgorithm)
                && !TOKEN_MAC_KMAC256_256.equals(tokenMacAlgorithm)) {
            throw new IllegalArgumentException("Unsupported token MAC algorithm '" + tokenMacAlgorithm + "'.");
        }
        if (!TOKEN_CONTENT_ENCRYPTION_A256GCM.equals(tokenContentEncryption)) {
            throw new IllegalArgumentException(
                    "Unsupported token content encryption '" + tokenContentEncryption + "'.");
        }
        if (exchangeConfigVersion == 1 && !EXCHANGE_KEY_AGREEMENT_ECDH.equals(exchangeKeyAgreement)) {
            throw new IllegalArgumentException("Exchange configuration version 1 only supports ECDH.");
        }
        if (exchangeConfigVersion == 2 && !EXCHANGE_KEY_AGREEMENT_MLKEM768.equals(exchangeKeyAgreement)) {
            throw new IllegalArgumentException(
                    "Exchange configuration version 2 only supports ML-KEM-768.");
        }
        if (exchangeConfigVersion != 1 && exchangeConfigVersion != 2) {
            throw new IllegalArgumentException(
                    "Unsupported exchange configuration version '" + exchangeConfigVersion + "'.");
        }
        return this;
    }

    /**
     * Resolve a registered suite identifier.
     *
     * @param suiteId the suite identifier
     * @return the immutable suite definition
     */
    public static CryptoSuite fromId(String suiteId) {
        if (suiteId == null || suiteId.isBlank()) {
            throw new IllegalArgumentException("Crypto suite ID must be a non-empty string.");
        }
        CryptoSuite suite = REGISTRY.get(suiteId);
        if (suite == null) {
            throw new IllegalArgumentException("Unknown crypto suite '" + suiteId + "'. Supported suites: "
                    + String.join(", ", REGISTRY.keySet()) + ".");
        }
        return suite;
    }

    /**
     * Replaces a deserialized suite with its canonical registered instance.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the registered suite matching this instance's identifier
     * @throws InvalidObjectException if this instance's identifier is not registered
     */
    private Object readResolve() throws InvalidObjectException {
        try {
            return fromId(suiteId);
        } catch (IllegalArgumentException exception) {
            InvalidObjectException invalidObjectException = new InvalidObjectException(exception.getMessage());
            invalidObjectException.initCause(exception);
            throw invalidObjectException;
        }
    }

    /**
     * Returns the backward-compatible default suite.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the default suite
     */
    public static CryptoSuite defaultSuite() {
        return ECDH_SHA256;
    }

    /**
     * Returns all registered suites.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return an immutable list of suites
     */
    public static List<CryptoSuite> all() {
        return List.copyOf(REGISTRY.values());
    }

    /**
     * Returns the stable identifier for this suite.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the suite identifier
     */
    public String getSuiteId() {
        return suiteId;
    }

    /**
     * Returns the digest algorithm used to tokenize values.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the token digest algorithm
     */
    public String getTokenDigestAlgorithm() {
        return tokenDigestAlgorithm;
    }

    /**
     * Returns the keyed MAC algorithm used to transform tokens.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the token MAC algorithm
     */
    public String getTokenMacAlgorithm() {
        return tokenMacAlgorithm;
    }

    /**
     * Returns the content-encryption algorithm used for match tokens.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the token content-encryption algorithm
     */
    public String getTokenContentEncryption() {
        return tokenContentEncryption;
    }

    /**
     * Returns the key-agreement mechanism used for exchanges.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the exchange key-agreement mechanism
     */
    public String getExchangeKeyAgreement() {
        return exchangeKeyAgreement;
    }

    /**
     * Returns the exchange configuration version required by this suite.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return the exchange configuration version
     */
    public int getExchangeConfigVersion() {
        return exchangeConfigVersion;
    }

    /**
     * Indicates whether this suite uses a post-quantum key-agreement mechanism.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return {@code true} when the suite uses ML-KEM
     */
    public boolean isPostQuantum() {
        return exchangeKeyAgreement.contains(EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX);
    }
}
