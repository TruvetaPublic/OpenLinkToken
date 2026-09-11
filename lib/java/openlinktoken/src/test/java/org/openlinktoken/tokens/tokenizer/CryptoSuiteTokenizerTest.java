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
