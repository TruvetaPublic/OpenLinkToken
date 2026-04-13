/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.truveta.openlinktoken.attributes.Attribute;
import com.truveta.openlinktoken.attributes.general.RecordIdAttribute;
import com.truveta.openlinktoken.attributes.person.FirstNameAttribute;
import com.truveta.openlinktoken.attributes.person.LastNameAttribute;
import com.truveta.openlinktoken.attributes.person.SexAttribute;
import com.truveta.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import com.truveta.openlinktoken.attributes.person.BirthDateAttribute;
import com.truveta.openlinktoken.attributes.person.PostalCodeAttribute;
import com.truveta.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import com.truveta.openlinktoken.tokentransformer.NoOperationTokenTransformer;

class TokenGeneratorBlankTokensTest {

    private TokenGenerator tokenGenerator;

    @BeforeEach
    void setUp() {
        tokenGenerator = new TokenGenerator(new TokenDefinition(),
                new SHA256Tokenizer(
                        java.util.Collections.singletonList(new NoOperationTokenTransformer())));
    }

    @Test
    void testBlankTokensTracking_WithInvalidAttributes() {
        // Create person attributes with missing postal code (required for T2)
        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(RecordIdAttribute.class, "123");
        personAttributes.put(FirstNameAttribute.class, "John");
        personAttributes.put(LastNameAttribute.class, "Doe");
        personAttributes.put(SexAttribute.class, "Male");
        personAttributes.put(BirthDateAttribute.class, "1990-01-01");
        personAttributes.put(SocialSecurityNumberAttribute.class, "123456789");
        // Missing PostalCodeAttribute intentionally to force T2 to generate blank token

        TokenGeneratorResult result = tokenGenerator.getAllTokens(personAttributes);

        // Verify that tokens were generated
        assertFalse(result.getTokens().isEmpty());

        // T2 should generate a blank token due to missing postal code
        Set<String> blankTokensByRule = result.getBlankTokensByRule();
        assertTrue(blankTokensByRule.contains("T2"), "T2 should generate blank token due to missing postal code");

        // Verify that the blank token is the expected BLANK value
        assertEquals(Token.BLANK, result.getTokens().get("T2"));
    }

    @Test
    void testBlankTokensTracking_WithInvalidSSN() {
        // Create person attributes with invalid SSN (required for T4)
        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(RecordIdAttribute.class, "123");
        personAttributes.put(FirstNameAttribute.class, "John");
        personAttributes.put(LastNameAttribute.class, "Doe");
        personAttributes.put(SexAttribute.class, "Male");
        personAttributes.put(BirthDateAttribute.class, "1990-01-01");
        personAttributes.put(SocialSecurityNumberAttribute.class, "111-11-1111"); // Invalid SSN from the INVALID_SSNS set
        personAttributes.put(PostalCodeAttribute.class, "12345");

        TokenGeneratorResult result = tokenGenerator.getAllTokens(personAttributes);

        // Verify that tokens were generated
        assertFalse(result.getTokens().isEmpty());

        // T4 should generate a blank token due to invalid SSN
        Set<String> blankTokensByRule = result.getBlankTokensByRule();
        assertTrue(blankTokensByRule.contains("T4"), "T4 should generate blank token due to invalid SSN");

        // Verify that the blank token is the expected BLANK value
        assertEquals(Token.BLANK, result.getTokens().get("T4"));
    }

    @Test
    void testBlankTokensTracking_WithValidAttributes() {
        // Create person attributes with all valid data
        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(RecordIdAttribute.class, "123");
        personAttributes.put(FirstNameAttribute.class, "John");
        personAttributes.put(LastNameAttribute.class, "Doe");
        personAttributes.put(SexAttribute.class, "Male");
        personAttributes.put(BirthDateAttribute.class, "1990-01-01");
        personAttributes.put(SocialSecurityNumberAttribute.class, "223-45-6789");
        personAttributes.put(PostalCodeAttribute.class, "22345");

        TokenGeneratorResult result = tokenGenerator.getAllTokens(personAttributes);

        // Verify that tokens were generated
        assertFalse(result.getTokens().isEmpty());

        // No blank tokens should be generated with valid data
        Set<String> blankTokensByRule = result.getBlankTokensByRule();
        assertTrue(blankTokensByRule.isEmpty(), "No blank tokens should be generated with valid data");

        // Verify that no tokens have the BLANK value
        for (String token : result.getTokens().values()) {
            assertNotEquals(Token.BLANK, token, "No token should be empty with valid data");
        }
    }

    @Test
    void testBlankTokensTracking_InitialState() {
        TokenGeneratorResult result = new TokenGeneratorResult();

        // Initially, blank tokens set should be empty
        Set<String> blankTokensByRule = result.getBlankTokensByRule();
        assertTrue(blankTokensByRule.isEmpty(), "Initial blank tokens set should be empty");
    }
}
