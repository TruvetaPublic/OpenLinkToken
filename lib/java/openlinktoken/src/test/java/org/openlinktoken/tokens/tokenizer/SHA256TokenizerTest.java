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
import org.openlinktoken.tokentransformer.EncryptTokenTransformer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

/** Tests SHA-256 token generation, transformer ordering, and error propagation. */
class SHA256TokenizerTest {
    private TokenTransformer hashTransformerMock;
    private TokenTransformer encryptTransformerMock;
    private SHA256Tokenizer tokenizer;

    /** Creates a tokenizer with mocked hash and encryption transformers. */
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

    /** Verifies null, empty, and whitespace-only input produces the blank token. */
    @Test
    void testTokenize_NullOrEmptyInput_ReturnsEmptyString() throws Exception {
        String resultNull = tokenizer.tokenize(null); // Test for null input
        assertEquals(Token.BLANK, resultNull);

        String resultEmpty = tokenizer.tokenize(""); // Test for empty string input
        assertEquals(Token.BLANK, resultEmpty);

        String resultBlank = tokenizer.tokenize("   "); // Test for input with only whitespace
        assertEquals(Token.BLANK, resultBlank);
    }

    /** Verifies the SHA-256 digest is passed through the configured transformers. */
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

    /** Verifies a tokenizer without transformers returns the raw SHA-256 digest. */
    @Test
    void testTokenize_ValidInput_NoTransformers_ReturnsRawHash() throws Exception {
        String inputValue = "test-input";

        tokenizer = new SHA256Tokenizer(new ArrayList<>()); // Recreate tokenizer with no transformers
        String expectedHash = calculateSHA256(inputValue); // Expected SHA-256 hash (in hex format) for "test-input"

        String result = tokenizer.tokenize(inputValue); // Call the tokenize method

        assertEquals(expectedHash, result); // Verify that the result is just the raw SHA-256 hash (no transformations
                                            // applied)
    }

    /** Verifies an exception from a transformer propagates from tokenization. */
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
     * Calculates the hexadecimal SHA-256 digest of an input string.
     *
     * @param input text to hash
     * @return the digest encoded as lowercase hexadecimal
     * @throws NoSuchAlgorithmException if SHA-256 is unavailable
     */
    private String calculateSHA256(String input) throws NoSuchAlgorithmException {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
        return Hex.encodeHexString(hash);
    }
}
