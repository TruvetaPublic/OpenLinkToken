/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
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

    /**
     * Verifies that the default-suite tokenizer rebuilds its digest after serialization.
     */
    @Test
    void defaultSuiteTokenizerRoundTripsThroughSerialization() throws Exception {
        CryptoSuiteTokenizer tokenizer = new CryptoSuiteTokenizer(new ArrayList<>());

        CryptoSuiteTokenizer deserializedTokenizer = serializeAndDeserialize(tokenizer);

        assertEquals(tokenizer.tokenize("test"), deserializedTokenizer.tokenize("test"));
    }

    /**
     * Verifies that an explicit-suite tokenizer rebuilds its digest after serialization.
     */
    @Test
    void explicitSuiteTokenizerRoundTripsThroughSerialization() throws Exception {
        CryptoSuiteTokenizer tokenizer = new CryptoSuiteTokenizer(
                new ArrayList<>(),
                CryptoSuite.fromId("suite-sha3-v1"));

        CryptoSuiteTokenizer deserializedTokenizer = serializeAndDeserialize(tokenizer);

        assertEquals(tokenizer.tokenize("test-input"), deserializedTokenizer.tokenize("test-input"));
    }

    private static CryptoSuiteTokenizer serializeAndDeserialize(CryptoSuiteTokenizer tokenizer)
            throws IOException, ClassNotFoundException {
        ByteArrayOutputStream serializedBytes = new ByteArrayOutputStream();
        try (ObjectOutputStream output = new ObjectOutputStream(serializedBytes)) {
            output.writeObject(tokenizer);
        }

        try (ObjectInputStream input = new ObjectInputStream(
                new ByteArrayInputStream(serializedBytes.toByteArray()))) {
            return CryptoSuiteTokenizer.class.cast(input.readObject());
        }
    }
}
