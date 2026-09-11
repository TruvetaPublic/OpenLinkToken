/* SPDX-License-Identifier: MIT */
package org.openlinktoken.crypto;

import java.util.List;
import java.util.Map;

/**
 * Immutable contract for token primitives and exchange key establishment.
 */
public final class CryptoSuite {
    private static final Map<String, CryptoSuite> REGISTRY = Map.of(
            "suite-sha256-v1",
            new CryptoSuite("suite-sha256-v1", "SHA-256", "HS256", "A256GCM", "ECDH", 1),
            "suite-sha3-v1",
            new CryptoSuite("suite-sha3-v1", "SHA3-256", "HS3-256", "A256GCM", "ECDH", 1),
            "suite-pq-shake-v1",
            new CryptoSuite("suite-pq-shake-v1", "SHAKE256-256", "KMAC256-256", "A256GCM", "ML-KEM-768", 2),
            "suite-pq-v1",
            new CryptoSuite("suite-pq-v1", "SHA3-256", "HS3-256", "A256GCM", "ML-KEM-768", 2),
            "suite-pq-hybrid-v1",
            new CryptoSuite("suite-pq-hybrid-v1", "SHA3-256", "HS3-256", "A256GCM", "ECDH+ML-KEM-768", 2));

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
    private CryptoSuite(
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
     * Return the backward-compatible default suite.
     *
     * @return the default suite
     */
    public static CryptoSuite defaultSuite() {
        return REGISTRY.get("suite-sha256-v1");
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
        return exchangeKeyAgreement.contains("ML-KEM");
    }
}
