/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokens.tokenizer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import com.truveta.openlinktoken.tokens.Token;
import com.truveta.openlinktoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.openlinktoken.tokentransformer.HashTokenTransformer;
import com.truveta.openlinktoken.tokentransformer.TokenTransformer;

class PassthroughTokenizerTest {
    private TokenTransformer hashTransformerMock;
    private TokenTransformer encryptTransformerMock;
    private PassthroughTokenizer tokenizer;

    @BeforeEach
    void setUp() {
        // Mocking TokenTransformer implementations (Hash and Encrypt)
        hashTransformerMock = Mockito.mock(HashTokenTransformer.class);
        encryptTransformerMock = Mockito.mock(EncryptTokenTransformer.class);

        // List of transformers to pass to PassthroughTokenizer
        List<TokenTransformer> transformers = new ArrayList<>();
        transformers.add(hashTransformerMock);
        transformers.add(encryptTransformerMock);

        // Instantiate the tokenizer with mocked transformers
        tokenizer = new PassthroughTokenizer(transformers);
    }

    @Test
    void testTokenize_NullOrEmptyInput_ReturnsEmptyString() throws Exception {
        String resultNull = tokenizer.tokenize(null); // Test for null input
        assertEquals(Token.BLANK, resultNull);

        String resultEmpty = tokenizer.tokenize(""); // Test for empty string input
        assertEquals(Token.BLANK, resultEmpty);

        String resultBlank = tokenizer.tokenize("   "); // Test for input with only whitespace
        assertEquals(Token.BLANK, resultBlank);
    }

    @Test
    void testTokenize_ValidInput_ReturnsUnchangedValue() throws Exception {
        String inputValue = "test-input";

        // Mock the transformations to simulate behavior of TokenTransformers
        when(hashTransformerMock.transform(anyString())).thenReturn(inputValue);
        when(encryptTransformerMock.transform(inputValue)).thenReturn("encrypted-token");

        String result = tokenizer.tokenize(inputValue); // Call the tokenize method

        // Verify the transformers were called with the original input value
        verify(hashTransformerMock).transform(inputValue);
        verify(encryptTransformerMock).transform(inputValue);

        assertEquals("encrypted-token", result); // Check the final result after applying the transformers
    }

    @Test
    void testTokenize_ValidInput_NoTransformers_ReturnsOriginalValue() throws Exception {
        String inputValue = "test-input";

        tokenizer = new PassthroughTokenizer(new ArrayList<>()); // Recreate tokenizer with no transformers

        String result = tokenizer.tokenize(inputValue); // Call the tokenize method

        assertEquals(inputValue, result); // Verify that the result is the original value unchanged
    }

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

    @Test
    void testTokenize_MultipleTransformers_AppliesInOrder() throws Exception {
        String inputValue = "original-value";
        String afterFirstTransform = "after-first";
        String afterSecondTransform = "after-second";

        // Mock the transformers to apply sequential transformations
        when(hashTransformerMock.transform(inputValue)).thenReturn(afterFirstTransform);
        when(encryptTransformerMock.transform(afterFirstTransform)).thenReturn(afterSecondTransform);

        String result = tokenizer.tokenize(inputValue);

        // Verify transformers were called in order
        verify(hashTransformerMock).transform(inputValue);
        verify(encryptTransformerMock).transform(afterFirstTransform);

        assertEquals(afterSecondTransform, result);
    }

    @Test
    void testTokenize_SpecialCharacters_ReturnsUnchanged() throws Exception {
        String inputValue = "special!@#$%^&*()_+-=[]{}|;':\",./<>?";

        tokenizer = new PassthroughTokenizer(new ArrayList<>()); // No transformers

        String result = tokenizer.tokenize(inputValue);

        assertEquals(inputValue, result); // Special characters should pass through unchanged
    }

    @Test
    void testTokenize_UnicodeCharacters_ReturnsUnchanged() throws Exception {
        String inputValue = "Hello 世界 🌍";

        tokenizer = new PassthroughTokenizer(new ArrayList<>()); // No transformers

        String result = tokenizer.tokenize(inputValue);

        assertEquals(inputValue, result); // Unicode characters should pass through unchanged
    }
}
