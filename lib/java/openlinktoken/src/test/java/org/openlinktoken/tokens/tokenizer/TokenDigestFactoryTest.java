/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import org.junit.jupiter.api.Test;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Verifies suite-selected digest implementations and factory validation.
 */
class TokenDigestFactoryTest {

    /**
     * Verifies each registered digest suite selects its dedicated implementation.
     */
    @Test
    void factorySelectsDigestImplementationForEachSuite() {
        assertInstanceOf(
                SHA256TokenDigest.class,
                TokenDigestFactory.forSuite(CryptoSuite.fromId("suite-sha256-v1")));
        assertInstanceOf(
                SHA3TokenDigest.class,
                TokenDigestFactory.forSuite(CryptoSuite.fromId("suite-sha3-v1")));
        assertInstanceOf(
                SHAKE256TokenDigest.class,
                TokenDigestFactory.forSuite(CryptoSuite.fromId("suite-pq-shake-v1")));
    }

    /**
     * Verifies the dedicated implementations against standard digest vectors.
     *
     * @throws Exception if a standard digest is unavailable
     */
    @Test
    void digestImplementationsMatchStandardVectors() throws Exception {
        byte[] value = "test-input".getBytes(StandardCharsets.UTF_8);

        assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(value), new SHA256TokenDigest().digest(value));
        assertArrayEquals(MessageDigest.getInstance("SHA3-256").digest(value), new SHA3TokenDigest().digest(value));
        assertArrayEquals(
                new byte[] {
                    0x08, 0x3e, 0x21, (byte) 0x85, (byte) 0xf5, 0x29, 0x46, (byte) 0xfb,
                    0x45, (byte) 0xe4, 0x59, 0x79, 0x44, 0x09, (byte) 0xb2, (byte) 0xea,
                    0x56, (byte) 0xe6, 0x42, 0x41, (byte) 0xba, 0x22, (byte) 0xa2, (byte) 0x90,
                    0x72, (byte) 0xad, 0x25, (byte) 0xb5, (byte) 0x94, 0x7c, 0x02, 0x3a
                },
                new SHAKE256TokenDigest().digest(value));
    }

    /**
     * Verifies unsupported digest identifiers fail at factory selection.
     */
    @Test
    void factoryRejectsUnsupportedDigestAlgorithm() {
        assertThrows(
                NoSuchAlgorithmException.class,
                () -> TokenDigestFactory.forAlgorithm("UNKNOWN"));
    }
}
