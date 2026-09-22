/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.ArrayList;

import org.junit.jupiter.api.Test;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Verifies the common suite-aware tokenizer pipeline.
 */
class CryptoSuiteTokenizerTest {

    /**
     * Verifies that an omitted suite uses the backward-compatible SHA-256 digest.
     */
    @Test
    void nullSuiteUsesDefaultDigest() throws Exception {
        CryptoSuiteTokenizer tokenizer = new CryptoSuiteTokenizer(new ArrayList<>(), null);

        assertEquals(
                "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                tokenizer.tokenize("test"));
    }

    /**
     * Verifies SHA-3 digest selection and hexadecimal serialization.
     *
     * @throws Exception if tokenization fails
     */
    @Test
    void tokenizeUsesSuiteDigestAndHexEncoding() throws Exception {
        CryptoSuiteTokenizer tokenizer = new CryptoSuiteTokenizer(
                new ArrayList<>(),
                CryptoSuite.fromId("suite-sha3-v1"));

        assertEquals(
                "ab96273f069fc38264bf16cc2287218779c5eed6c0fee89490b990ffc35a2af5",
                tokenizer.tokenize("test-input"));
    }
}
