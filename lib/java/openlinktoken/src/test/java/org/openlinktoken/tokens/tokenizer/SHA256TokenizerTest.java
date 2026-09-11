/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

import org.apache.commons.codec.binary.Hex;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import org.openlinktoken.tokens.Token;
import org.openlinktoken.crypto.CryptoSuite;
import org.openlinktoken.tokentransformer.EncryptTokenTransformer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Tests digest selection and transformer application in {@link SHA256Tokenizer}.
 */
class SHA256TokenizerTest {
    private TokenTransformer hashTransformerMock;
    private TokenTransformer encryptTransformerMock;
    private SHA256Tokenizer tokenizer;

    /**
     * Creates a tokenizer with mocked transformers for each test.
     */
    @BeforeEach
    void setUp() {
        // Mocking TokenTransformer implementations (Hash and Encrypt)
        hashTransformerMock = Mockito.mock(HashTokenTransformer.class);
        encryptTransformerMock = Mockito.mock(EncryptTokenTransformer.class);

        // List of transformers to pass to SHA256Tokenizer
        List<TokenTransformer> transformers = new ArrayList<>();
        transformers.add(hashTransformerMock);
        transformers.add(encryptTransformerMock);

        // Instantiate the tokenizer with mocked transformers
        tokenizer = new SHA256Tokenizer(transformers);
    }

    /**
     * Verifies that null and blank inputs return the empty token.
     */
    @Test
    void testTokenize_NullOrEmptyInput_ReturnsEmptyString() throws Exception {
        String resultNull = tokenizer.tokenize(null); // Test for null input
        assertEquals(Token.BLANK, resultNull);

        String resultEmpty = tokenizer.tokenize(""); // Test for empty string input
        assertEquals(Token.BLANK, resultEmpty);

        String resultBlank = tokenizer.tokenize("   "); // Test for input with only whitespace
        assertEquals(Token.BLANK, resultBlank);
    }

    /**
     * Verifies that a digest is passed through each configured transformer.
     */
    @Test
    void testTokenize_ValidInput_ReturnsHashedToken() throws Exception {
        String inputValue = "test-input";

        String expectedHash = calculateSHA256(inputValue); // Expected SHA-256 hash (in hex format) for "test-input"

        // Mock the transformations to simulate behavior of TokenTransformers
        when(hashTransformerMock.transform(anyString())).thenReturn(expectedHash);
        when(encryptTransformerMock.transform(expectedHash)).thenReturn("encrypted-token");

        String result = tokenizer.tokenize(inputValue); // Call the tokenize method

        // Verify the transformers were called
        verify(hashTransformerMock).transform(anyString());
        verify(encryptTransformerMock).transform(expectedHash);

        assertEquals("encrypted-token", result); // Check the final result after applying the transformers
    }

    /**
     * Verifies that tokenization returns the raw digest when no transformers exist.
     */
    @Test
    void testTokenize_ValidInput_NoTransformers_ReturnsRawHash() throws Exception {
        String inputValue = "test-input";

        tokenizer = new SHA256Tokenizer(new ArrayList<>()); // Recreate tokenizer with no transformers
        String expectedHash = calculateSHA256(inputValue); // Expected SHA-256 hash (in hex format) for "test-input"

        String result = tokenizer.tokenize(inputValue); // Call the tokenize method

        assertEquals(expectedHash, result); // Verify that the result is just the raw SHA-256 hash (no transformations
                                            // applied)
    }

    /**
     * Verifies that transformer failures are propagated to the caller.
     */
    @Test
    void testTokenize_ValidInput_TransformerThrowsException() throws Exception {
        String inputValue = "test-input";

        // Mock the first transformer to throw an exception
        when(hashTransformerMock.transform(anyString())).thenThrow(new RuntimeException("Transform error"));

        // Call the tokenize method and assert it propagates the exception
        Exception exception = assertThrows(Exception.class, () -> {
            tokenizer.tokenize(inputValue);
        });

        assertEquals("Transform error", exception.getMessage());
    }

    /**
     * Verifies the fixed vector for the SHA-3 suite.
     */
    @Test
    void testTokenize_Sha3Suite_ReturnsFixedVector() throws Exception {
        tokenizer = new SHA256Tokenizer(new ArrayList<>(), CryptoSuite.fromId("suite-sha3-v1"));

        assertEquals(
                "ab96273f069fc38264bf16cc2287218779c5eed6c0fee89490b990ffc35a2af5",
                tokenizer.tokenize("test-input"));
    }

    /**
     * Verifies the fixed vector for the SHAKE suite.
     */
    @Test
    void testTokenize_ShakeSuite_ReturnsFixedVector() throws Exception {
        tokenizer = new SHA256Tokenizer(new ArrayList<>(), CryptoSuite.fromId("suite-pq-shake-v1"));

        assertEquals(
                "083e2185f52946fb45e459794409b2ea56e64241ba22a29072ad25b5947c023a",
                tokenizer.tokenize("test-input"));
    }

    /**
     * Calculates a SHA-256 hexadecimal digest for a test input.
     *
     * @param input the input string
     * @return the hexadecimal SHA-256 digest
     * @throws NoSuchAlgorithmException if SHA-256 is unavailable
     */
    private String calculateSHA256(String input) throws NoSuchAlgorithmException {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
        return Hex.encodeHexString(hash);
    }
}
