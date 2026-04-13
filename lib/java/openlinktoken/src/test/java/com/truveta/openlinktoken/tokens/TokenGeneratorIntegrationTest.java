/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;

import com.truveta.openlinktoken.attributes.Attribute;
import com.truveta.openlinktoken.attributes.person.BirthDateAttribute;
import com.truveta.openlinktoken.attributes.person.FirstNameAttribute;
import com.truveta.openlinktoken.attributes.person.LastNameAttribute;
import com.truveta.openlinktoken.attributes.person.SexAttribute;
import com.truveta.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import com.truveta.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import com.truveta.openlinktoken.tokentransformer.TokenTransformer;

class TokenGeneratorIntegrationTest {

    @Mock
    private List<TokenTransformer> tokenTransformerList;

    @Mock
    private BaseTokenDefinition tokenDefinition;

    @InjectMocks
    private TokenGenerator tokenGenerator;

    @BeforeEach
    void setUp() throws Exception {
        // Setup real TokenDefinition and TokenTransformers for integration testing
        tokenDefinition = new TokenDefinition();
        tokenTransformerList = new ArrayList<TokenTransformer>();

        tokenGenerator = new TokenGenerator(tokenDefinition, new SHA256Tokenizer(tokenTransformerList));
    }

    @Test
    void testGetAllTokens_validPersonAttributes_generatesTokens() {
        // Define token identifiers and attribute expressions
        tokenDefinition = new TokenDefinition();

        // Person attributes to be used for token generation
        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "Alice");
        personAttributes.put(LastNameAttribute.class, "Wonderland");
        personAttributes.put(SocialSecurityNumberAttribute.class, "345-54-6795");
        personAttributes.put(SexAttribute.class, "F");
        personAttributes.put(BirthDateAttribute.class, "1993-08-10");

        // Generate all tokens
        Map<String, String> tokens = tokenGenerator.getAllTokens(personAttributes).getTokens();

        // Validate the tokens
        assertNotNull(tokens);
        assertEquals(5, tokens.size(), "Expected 5 tokens to be generated");

        // Validate the actual tokens generated
        assertTrue(tokens.containsKey("T1"));
        assertTrue(tokens.containsKey("T2"));
        assertTrue(tokens.containsKey("T3"));
        assertTrue(tokens.containsKey("T4"));
        assertTrue(tokens.containsKey("T5"));

        assertEquals("02292af14559b4c2a28a772536b81760ad7b8ebac8ce49e8450ca0fa5044e37f", tokens.get("T1"));
        assertEquals("0000000000000000000000000000000000000000000000000000000000000000", tokens.get("T2"));
        assertEquals("a76c3bff664bec8d0f77b4b47ad555d212dc671949ed3cf1c1edef68733835b2", tokens.get("T3"));
        assertEquals("21c3cf1fdb4fd45197e5def14d0228d26c56bcec1b8641079f9b9ec24f9a6a0b", tokens.get("T4"));
        assertEquals("3756556f2323148cb57e1e13b1abcd457e1c1706a84ae83d522a3fc0ad43506d", tokens.get("T5"));
    }
}
