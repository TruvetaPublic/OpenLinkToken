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
            "suite-shake-v1",
            new CryptoSuite("suite-shake-v1", "SHAKE256-256", "KMAC256-256", "A256GCM", "ECDH", 1),
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

    public String getSuiteId() {
        return suiteId;
    }

    public String getTokenDigestAlgorithm() {
        return tokenDigestAlgorithm;
    }

    public String getTokenMacAlgorithm() {
        return tokenMacAlgorithm;
    }

    public String getTokenContentEncryption() {
        return tokenContentEncryption;
    }

    public String getExchangeKeyAgreement() {
        return exchangeKeyAgreement;
    }

    public int getExchangeConfigVersion() {
        return exchangeConfigVersion;
    }

    public boolean isPostQuantum() {
        return exchangeKeyAgreement.contains("ML-KEM");
    }
}
