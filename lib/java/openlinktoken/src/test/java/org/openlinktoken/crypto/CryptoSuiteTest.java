/* SPDX-License-Identifier: MIT */
package org.openlinktoken.crypto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class CryptoSuiteTest {
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
        assertFalse(!hybrid.isPostQuantum());

        CryptoSuite shake = CryptoSuite.fromId("suite-shake-v1");
        assertEquals("SHAKE256-256", shake.getTokenDigestAlgorithm());
        assertEquals("KMAC256-256", shake.getTokenMacAlgorithm());
        assertEquals("ECDH", shake.getExchangeKeyAgreement());
        assertEquals(1, shake.getExchangeConfigVersion());
    }

    @Test
    void unknownSuiteIdsFailClosed() {
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId("unknown"));
        assertThrows(IllegalArgumentException.class, () -> CryptoSuite.fromId(""));
    }
}
