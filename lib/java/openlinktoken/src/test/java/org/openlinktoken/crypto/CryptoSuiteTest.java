/* SPDX-License-Identifier: MIT */
package org.openlinktoken.crypto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.Constructor;
import java.lang.reflect.Modifier;

import org.junit.jupiter.api.Test;

/**
 * Tests the registered crypto suite contracts and lookup validation.
 */
class CryptoSuiteTest {
    /**
     * Verifies that each registered suite is exposed as a canonical public constant.
     */
    @Test
    void publicConstantsAreRegisteredSuites() {
        assertSame(CryptoSuite.SUITE_SHA256_V1, CryptoSuite.fromId("suite-sha256-v1"));
        assertSame(CryptoSuite.SUITE_SHA3_V1, CryptoSuite.fromId("suite-sha3-v1"));
        assertSame(CryptoSuite.SUITE_PQ_SHAKE_V1, CryptoSuite.fromId("suite-pq-shake-v1"));
        assertSame(CryptoSuite.SUITE_PQ_V1, CryptoSuite.fromId("suite-pq-v1"));
        assertSame(CryptoSuite.SUITE_PQ_HYBRID_V1, CryptoSuite.fromId("suite-pq-hybrid-v1"));
    }

    /**
     * Verifies that suite definitions are not exposed through a public constructor.
     *
     * @throws NoSuchMethodException if the suite constructor is missing
     */
    @Test
    void constructorIsNotPublic() throws NoSuchMethodException {
        Constructor<CryptoSuite> constructor = CryptoSuite.class.getDeclaredConstructor(
                String.class,
                String.class,
                String.class,
                String.class,
                String.class,
                int.class);

        assertFalse(Modifier.isPublic(constructor.getModifiers()));
    }

    /**
     * Verifies that every registered suite satisfies its internal contract.
     */
    @Test
    void registeredSuitesValidateTheirContracts() {
        CryptoSuite.all().forEach(suite -> assertSame(suite, suite.validate()));
    }

    /**
     * Verifies the algorithms and versions declared by the registered suites.
     */
    @Test
    void registeredSuitesHaveExpectedContracts() {
        assertEquals("suite-sha256-v1", CryptoSuite.defaultSuite().getSuiteId());
        assertEquals("SHA-256", CryptoSuite.defaultSuite().getTokenDigestAlgorithm());
        assertEquals("HS256", CryptoSuite.defaultSuite().getTokenMacAlgorithm());
        assertEquals("ECDH", CryptoSuite.defaultSuite().getExchangeKeyAgreement());
        assertEquals(1, CryptoSuite.defaultSuite().getExchangeConfigVersion());

        CryptoSuite hybrid = CryptoSuite.fromId("suite-pq-hybrid-v1");
        assertEquals("ECDH+ML-KEM-768", hybrid.getExchangeKeyAgreement());
        assertEquals(2, hybrid.getExchangeConfigVersion());
        assertEquals("HS3-256", hybrid.getTokenMacAlgorithm());
        assertEquals("SHA3-256", hybrid.getTokenDigestAlgorithm());
        assertTrue(hybrid.isPostQuantum());

        CryptoSuite pqShake = CryptoSuite.fromId("suite-pq-shake-v1");
        assertEquals("SHAKE256-256", pqShake.getTokenDigestAlgorithm());
        assertEquals("KMAC256-256", pqShake.getTokenMacAlgorithm());
        assertEquals("ML-KEM-768", pqShake.getExchangeKeyAgreement());
        assertEquals(2, pqShake.getExchangeConfigVersion());
        assertTrue(pqShake.isPostQuantum());
    }

    /**
     * Verifies that suite algorithm identifiers are exposed as stable constants.
     */
    @Test
    void algorithmIdentifiersAreStableConstants() {
        assertEquals("SHA-256", CryptoSuite.TOKEN_DIGEST_SHA256);
        assertEquals("SHA3-256", CryptoSuite.TOKEN_DIGEST_SHA3_256);
        assertEquals("SHAKE256-256", CryptoSuite.TOKEN_DIGEST_SHAKE256_256);
        assertEquals("HS256", CryptoSuite.TOKEN_MAC_HS256);
        assertEquals("HS3-256", CryptoSuite.TOKEN_MAC_HS3_256);
        assertEquals("KMAC256-256", CryptoSuite.TOKEN_MAC_KMAC256_256);
        assertEquals("KMAC256", CryptoSuite.TOKEN_MAC_KMAC256_PREFIX);
        assertEquals("A256GCM", CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM);
        assertEquals("ECDH", CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH);
        assertEquals("ML-KEM-768", CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768);
        assertEquals("ECDH+ML-KEM-768", CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768);
        assertEquals("ML-KEM", CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX);
    }

    /**
     * Verifies that unknown or blank suite identifiers are rejected.
     */
    @Test
    void unknownSuiteIdsFailClosed() {
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId("unknown"));
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId(""));
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId("suite-shake-v1"));
    }

    /**
     * Verifies that invalid algorithm and exchange-version combinations fail during construction.
     */
    @Test
    void invalidSuiteContractsFailDuringConstruction() {
        assertInvalidSuite(
                "A128GCM",
                "ECDH",
                1,
                "Unsupported token content encryption 'A128GCM'.");
        assertInvalidSuite(
                "A256GCM",
                "ML-KEM-768",
                1,
                "Exchange configuration version 1 only supports ECDH.");
        assertInvalidSuite(
                "A256GCM",
                "ECDH",
                2,
                "Exchange configuration version 2 requires a non-ECDH key agreement.");
        assertInvalidSuite(
                "A256GCM",
                "ML-KEM-768",
                3,
                "Unsupported exchange configuration version '3'.");
    }

    private static void assertInvalidSuite(
            String tokenContentEncryption,
            String exchangeKeyAgreement,
            int exchangeConfigVersion,
            String expectedMessage) {
        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> new CryptoSuite(
                        "test-suite",
                        "SHA-256",
                        "HS256",
                        tokenContentEncryption,
                        exchangeKeyAgreement,
                        exchangeConfigVersion));

        assertEquals(expectedMessage, exception.getMessage());
    }
}
