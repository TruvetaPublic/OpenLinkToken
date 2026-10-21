/* SPDX-License-Identifier: MIT */
package org.openlinktoken.crypto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.Constructor;
import java.lang.reflect.Modifier;
import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Tests the registered crypto suite contracts and lookup validation.
 */
class CryptoSuiteTest {
    /**
     * Verifies that each registered suite is exposed as a canonical public constant.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void publicConstantsAreRegisteredSuites() {
        assertSame(CryptoSuite.ECDH_SHA256, CryptoSuite.fromId("ecdh-sha256"));
        assertSame(CryptoSuite.ECDH_SHA3_256, CryptoSuite.fromId("ecdh-sha3-256"));
        assertSame(CryptoSuite.MLKEM768_SHAKE256, CryptoSuite.fromId("mlkem768-shake256"));
        assertSame(CryptoSuite.MLKEM768_SHA3_256, CryptoSuite.fromId("mlkem768-sha3-256"));
        assertEquals(4, CryptoSuite.all().size());
    }

    /**
     * Verifies that suite definitions are not exposed through a public constructor.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
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
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void registeredSuitesValidateTheirContracts() {
        CryptoSuite.all().forEach(suite -> assertSame(suite, suite.validate()));
    }

    /**
     * Verifies the algorithms and versions declared by the registered suites.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void registeredSuitesHaveExpectedContracts() {
        assertEquals("ecdh-sha256", CryptoSuite.defaultSuite().getSuiteId());
        assertEquals("SHA-256", CryptoSuite.defaultSuite().getTokenDigestAlgorithm());
        assertEquals("HS256", CryptoSuite.defaultSuite().getTokenMacAlgorithm());
        assertEquals("ECDH", CryptoSuite.defaultSuite().getExchangeKeyAgreement());
        assertEquals(1, CryptoSuite.defaultSuite().getExchangeConfigVersion());

        CryptoSuite pq = CryptoSuite.fromId("mlkem768-sha3-256");
        assertEquals("ML-KEM-768", pq.getExchangeKeyAgreement());
        assertEquals(2, pq.getExchangeConfigVersion());
        assertEquals("HS3-256", pq.getTokenMacAlgorithm());
        assertEquals("SHA3-256", pq.getTokenDigestAlgorithm());
        assertTrue(pq.isPostQuantum());

        CryptoSuite pqShake = CryptoSuite.fromId("mlkem768-shake256");
        assertEquals("SHAKE256-256", pqShake.getTokenDigestAlgorithm());
        assertEquals("KMAC256-256", pqShake.getTokenMacAlgorithm());
        assertEquals("ML-KEM-768", pqShake.getExchangeKeyAgreement());
        assertEquals(2, pqShake.getExchangeConfigVersion());
        assertTrue(pqShake.isPostQuantum());
    }

    /**
     * Verifies that suite algorithm identifiers are exposed as stable constants.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
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
        assertEquals("ML-KEM", CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX);
    }

    /**
     * Verifies that unknown or blank suite identifiers are rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void unknownSuiteIdsFailClosed() {
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId("unknown"));
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId(""));
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId("suite-shake-v1"));
        for (String removedId : List.of(
                "suite-sha256", "suite-sha3", "suite-pq", "suite-pq-shake",
                "suite-sha256-v1", "suite-sha3-v1", "suite-pq-v1",
                "suite-pq-shake-v1", "suite-pq-hybrid-v1", "suite-pq-hybrid")) {
            assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId(removedId));
        }
    }

    /**
     * Verifies that invalid algorithm and exchange-version combinations fail during construction.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
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
                "Exchange configuration version 2 only supports ML-KEM-768.");
        assertInvalidSuite(
                "A256GCM",
                "ECDH+ML-KEM-768",
                2,
                "Exchange configuration version 2 only supports ML-KEM-768.");
        assertInvalidSuite(
                "A256GCM",
                "ML-KEM-768",
                3,
                "Unsupported exchange configuration version '3'.");
    }

    /**
     * Verifies unsupported token-digest identifiers fail during suite construction.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void unsupportedTokenDigestFailsDuringSuiteValidation() {
        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> new CryptoSuite(
                        "unsupported-digest-suite",
                        "UNKNOWN-DIGEST",
                        CryptoSuite.TOKEN_MAC_HS256,
                        CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
                        CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH,
                        1));

        assertEquals("Unsupported token digest algorithm 'UNKNOWN-DIGEST'.", exception.getMessage());
    }

    /**
     * Verifies unsupported token-MAC identifiers fail during suite construction.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void unsupportedTokenMacFailsDuringSuiteValidation() {
        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> new CryptoSuite(
                        "unsupported-mac-suite",
                        CryptoSuite.TOKEN_DIGEST_SHA256,
                        "UNKNOWN-MAC",
                        CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
                        CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH,
                        1));

        assertEquals("Unsupported token MAC algorithm 'UNKNOWN-MAC'.", exception.getMessage());
    }

    /**
     * Asserts that invalid suite components fail validation with the expected message.
     *
     * <p>This method returns no value.</p>
     *
     * @param tokenContentEncryption token content-encryption algorithm
     * @param exchangeKeyAgreement exchange key-agreement mechanism
     * @param exchangeConfigVersion exchange configuration version
     * @param expectedMessage expected validation message
     */
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
