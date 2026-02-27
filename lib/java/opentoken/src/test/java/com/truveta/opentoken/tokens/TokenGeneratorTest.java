/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;

import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.attributes.AttributeExpression;
import com.truveta.opentoken.attributes.person.FirstNameAttribute;
import com.truveta.opentoken.attributes.person.LastNameAttribute;
import com.truveta.opentoken.tokens.tokenizer.Tokenizer;

class TokenGeneratorTest {
    @Mock
    private Tokenizer tokenizer;

    @Mock
    private BaseTokenDefinition tokenDefinition;

    @InjectMocks
    private TokenGenerator tokenGenerator;

    @BeforeEach
    void setUp() {
        tokenDefinition = mock(BaseTokenDefinition.class);
        tokenizer = mock(Tokenizer.class);

        tokenGenerator = new TokenGenerator(tokenDefinition, tokenizer);

    }

    @Test
    void testGetAllTokens_validTokensWithExpressions() throws Exception {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("token1",
                "token2"));

        AttributeExpression attrExpr1 = new AttributeExpression(FirstNameAttribute.class, "U");
        AttributeExpression attrExpr2 = new AttributeExpression(LastNameAttribute.class,
                "R('MacDonald','Donald')");

        ArrayList<AttributeExpression> attributeExpressions1 = new ArrayList<>();
        attributeExpressions1.add(attrExpr1);
        ArrayList<AttributeExpression> attributeExpressions2 = new ArrayList<>();
        attributeExpressions2.add(attrExpr2);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions1);
        when(tokenDefinition.getTokenDefinition("token2")).thenReturn(attributeExpressions2);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "John");
        personAttributes.put(LastNameAttribute.class, "Old MacDonald");

        when(tokenizer.tokenize(anyString())).thenReturn("hashedToken");

        Map<String, String> tokens = tokenGenerator.getAllTokens(personAttributes).getTokens();

        assertNotNull(tokens);
        assertEquals(2, tokens.size());
        assertEquals("hashedToken", tokens.get("token1"));
        assertEquals("hashedToken", tokens.get("token2"));
    }

    @Test
    void testGetAllTokens_invalidAttribute_skipsTokenGeneration() {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("token1"));

        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");

        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);
        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>(); // Person attributes (invalid case
                                                                                    // with missing name)
        personAttributes.put(LastNameAttribute.class, "MacDonald");

        Map<String, String> tokens = tokenGenerator.getAllTokens(personAttributes).getTokens();

        // Validate that no tokens are generated
        assertTrue(tokens.isEmpty(), "Expected no tokens to be generated due to validation failure");
    }

    @Test
    void testGetAllTokens_errorInTokenGeneration_logsError() throws Exception {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("token1"));

        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");

        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);
        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "John");

        // Simulate error during tokenization
        when(tokenizer.tokenize(anyString())).thenThrow(new RuntimeException("Tokenization error"));

        Map<String, String> tokens = tokenGenerator.getAllTokens(personAttributes).getTokens();

        // Validate that no tokens are generated due to tokenization error
        assertTrue(tokens.isEmpty(), "Expected no tokens to be generated due to tokenization error");
    }

    @Test
    void testGetTokenSignature_validSignature() {
        AttributeExpression attrExpr1 = new AttributeExpression(FirstNameAttribute.class, "U");
        AttributeExpression attrExpr2 = new AttributeExpression(LastNameAttribute.class, "U");

        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr1);
        attributeExpressions.add(attrExpr2);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "John");
        personAttributes.put(LastNameAttribute.class, "Smith");

        String signature = tokenGenerator.getTokenSignature("token1", personAttributes, new TokenGeneratorResult());

        assertNotNull(signature);
        assertEquals("JOHN|SMITH", signature);
    }

    @Test
    void testGetTokenSignature_nullPersonAttributes() {
        assertThrows(IllegalArgumentException.class, () -> {
            tokenGenerator.getTokenSignature("token1", null, new TokenGeneratorResult());
        });
    }

    @Test
    void testGetTokenSignature_missingRequiredAttribute() {
        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");

        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(LastNameAttribute.class, "Smith");

        String signature = tokenGenerator.getTokenSignature("token1", personAttributes, new TokenGeneratorResult());

        assertNull(signature);
    }

    @Test
    void testGetTokenSignature_invalidAttributeValue() {
        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");

        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, ""); // Invalid empty name

        String signature = tokenGenerator.getTokenSignature("token1", personAttributes, new TokenGeneratorResult());

        assertNull(signature);
    }

    @Test
    void testGetToken_validInput_returnsHashedToken() throws Exception {
        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");
        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);
        when(tokenizer.tokenize(anyString())).thenReturn("hashedToken123");

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "John");

        String token = tokenGenerator.getToken("token1", personAttributes, new TokenGeneratorResult());

        assertNotNull(token);
        assertEquals("hashedToken123", token);
    }

    @Test
    void testGetToken_nullSignature_returnsNull() throws TokenGenerationException {
        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");
        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        // Missing required attribute leads to null signature
        personAttributes.put(LastNameAttribute.class, "Smith");

        String token = tokenGenerator.getToken("token1", personAttributes, new TokenGeneratorResult());

        assertNull(token);
    }

    @Test
    void testGetToken_tokenizationError_throwsException() throws Exception {
        AttributeExpression attrExpr = new AttributeExpression(FirstNameAttribute.class, "U");
        ArrayList<AttributeExpression> attributeExpressions = new ArrayList<>();
        attributeExpressions.add(attrExpr);

        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(attributeExpressions);
        when(tokenizer.tokenize(anyString())).thenThrow(new RuntimeException("Tokenization failed"));

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "John");

        assertThrows(TokenGenerationException.class, () -> {
            tokenGenerator.getToken("token1", personAttributes, new TokenGeneratorResult());
        });
    }
}
