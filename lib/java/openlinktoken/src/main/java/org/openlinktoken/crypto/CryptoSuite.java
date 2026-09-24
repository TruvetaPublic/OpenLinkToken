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

    /** ECDH and ML-KEM-768 hybrid exchange key-agreement identifier. */
    public static final String EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768 = "ECDH+ML-KEM-768";

    /** ML-KEM exchange key-agreement family prefix. */
    public static final String EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX = "ML-KEM";

    /** The SHA-256 and ECDH crypto suite. */
    public static final CryptoSuite SUITE_SHA256_V1 =
            new CryptoSuite(
                    "suite-sha256-v1",
                    TOKEN_DIGEST_SHA256,
                    TOKEN_MAC_HS256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_ECDH,
                    1);

    /** The SHA-3-256 and ECDH crypto suite. */
    public static final CryptoSuite SUITE_SHA3_V1 =
            new CryptoSuite(
                    "suite-sha3-v1",
                    TOKEN_DIGEST_SHA3_256,
                    TOKEN_MAC_HS3_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_ECDH,
                    1);

    /** The SHAKE256 and ML-KEM-768 crypto suite. */
    public static final CryptoSuite SUITE_PQ_SHAKE_V1 =
            new CryptoSuite(
                    "suite-pq-shake-v1",
                    TOKEN_DIGEST_SHAKE256_256,
                    TOKEN_MAC_KMAC256_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_MLKEM768,
                    2);

    /** The SHA-3-256 and ML-KEM-768 crypto suite. */
    public static final CryptoSuite SUITE_PQ_V1 =
            new CryptoSuite(
                    "suite-pq-v1",
                    TOKEN_DIGEST_SHA3_256,
                    TOKEN_MAC_HS3_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_MLKEM768,
                    2);

    /** The SHA-3-256, ECDH, and ML-KEM-768 hybrid crypto suite. */
    public static final CryptoSuite SUITE_PQ_HYBRID_V1 =
            new CryptoSuite(
                    "suite-pq-hybrid-v1",
                    TOKEN_DIGEST_SHA3_256,
                    TOKEN_MAC_HS3_256,
                    TOKEN_CONTENT_ENCRYPTION_A256GCM,
                    EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768,
                    2);

    private static final Map<String, CryptoSuite> REGISTRY = Map.of(
            SUITE_SHA256_V1.getSuiteId(),
            SUITE_SHA256_V1,
            SUITE_SHA3_V1.getSuiteId(),
            SUITE_SHA3_V1,
            SUITE_PQ_SHAKE_V1.getSuiteId(),
            SUITE_PQ_SHAKE_V1,
            SUITE_PQ_V1.getSuiteId(),
            SUITE_PQ_V1,
            SUITE_PQ_HYBRID_V1.getSuiteId(),
            SUITE_PQ_HYBRID_V1);

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
     * Validate the internal algorithm and exchange-version contract.
     *
     * @return this validated suite
     */
    public CryptoSuite validate() {
        if (!TOKEN_CONTENT_ENCRYPTION_A256GCM.equals(tokenContentEncryption)) {
            throw new IllegalArgumentException(
                    "Unsupported token content encryption '" + tokenContentEncryption + "'.");
        }
        if (exchangeConfigVersion == 1 && !EXCHANGE_KEY_AGREEMENT_ECDH.equals(exchangeKeyAgreement)) {
            throw new IllegalArgumentException("Exchange configuration version 1 only supports ECDH.");
        }
        if (exchangeConfigVersion == 2 && EXCHANGE_KEY_AGREEMENT_ECDH.equals(exchangeKeyAgreement)) {
            throw new IllegalArgumentException(
                    "Exchange configuration version 2 requires a non-ECDH key agreement.");
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
     * Return the backward-compatible default suite.
     *
     * @return the default suite
     */
    public static CryptoSuite defaultSuite() {
        return SUITE_SHA256_V1;
    }

    /**
     * Return all registered suites.
     *
     * @return an immutable list of suites
     */
    public static List<CryptoSuite> all() {
        return List.copyOf(REGISTRY.values());
    }

    /**
     * Returns the stable identifier for this suite.
     *
     * @return the suite identifier
     */
    public String getSuiteId() {
        return suiteId;
    }

    /**
     * Returns the digest algorithm used to tokenize values.
     *
     * @return the token digest algorithm
     */
    public String getTokenDigestAlgorithm() {
        return tokenDigestAlgorithm;
    }

    /**
     * Returns the keyed MAC algorithm used to transform tokens.
     *
     * @return the token MAC algorithm
     */
    public String getTokenMacAlgorithm() {
        return tokenMacAlgorithm;
    }

    /**
     * Returns the content-encryption algorithm used for match tokens.
     *
     * @return the token content-encryption algorithm
     */
    public String getTokenContentEncryption() {
        return tokenContentEncryption;
    }

    /**
     * Returns the key-agreement mechanism used for exchanges.
     *
     * @return the exchange key-agreement mechanism
     */
    public String getExchangeKeyAgreement() {
        return exchangeKeyAgreement;
    }

    /**
     * Returns the exchange configuration version required by this suite.
     *
     * @return the exchange configuration version
     */
    public int getExchangeConfigVersion() {
        return exchangeConfigVersion;
    }

    /**
     * Indicates whether this suite uses a post-quantum key-agreement mechanism.
     *
     * @return {@code true} when the suite uses ML-KEM
     */
    public boolean isPostQuantum() {
        return exchangeKeyAgreement.contains(EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX);
    }
}
