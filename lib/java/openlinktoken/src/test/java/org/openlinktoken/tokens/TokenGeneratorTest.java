/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.tokens.tokenizer.PassthroughTokenizer;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokens.tokenizer.Tokenizer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

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
    void testGetAllTokensViaFieldId_emptyDefinition_skipsTokenization() throws Exception {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("token1"));
        when(tokenDefinition.getTokenDefinition("token1")).thenReturn(List.of());

        var result = tokenGenerator.getAllTokensViaFieldId(Map.of());

        assertTrue(result.getTokens().isEmpty());
        verify(tokenizer, never()).tokenize(anyString());
    }

    @Test
    void testFieldIdInferenceProviderHandlesEmptyDefinition() {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("ML1"));
        when(tokenDefinition.getTokenDefinition("ML1")).thenReturn(List.of());

        var signatures = tokenGenerator.getAllTokenSignaturesViaFieldId(Map.of("LastName", "Smith"));
        var result = tokenGenerator.getAllTokensViaFieldId(Map.of("LastName", "Smith"));

        assertEquals("Smith-provider", signatures.get("ML1"));
        assertEquals("Smith-provider", result.getTokens().get("ML1"));
        assertTrue(result.getBlankTokensByRule().isEmpty());
    }

    @Test
    void testFieldIdExclusionSkipsInferenceProvider() throws Exception {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("ML1", "token1"));
        when(tokenDefinition.getTokenDefinition("ML1")).thenReturn(List.of());
        when(tokenDefinition.getTokenDefinition("token1"))
                .thenReturn(List.of(new AttributeExpression(FirstNameAttribute.class, "U")));
        when(tokenizer.tokenize(anyString())).thenReturn("ordinary-token");

        var result = tokenGenerator.generateTokensExcludingViaFieldId(
                Map.of("FirstName", "John"),
                Set.of("ML1"));

        assertEquals(Map.of("token1", "ordinary-token"), result.getTokens());
    }

    @Test
    void testFieldIdInferenceProviderTracksBlank() throws Exception {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("ML1"));
        when(tokenDefinition.getTokenDefinition("ML1")).thenReturn(List.of());
        tokenGenerator = new TokenGenerator(
                tokenDefinition,
                new SHA256Tokenizer(List.of(new HashTokenTransformer("secret"))));

        var result = tokenGenerator.getAllTokensViaFieldId(Map.of("LastName", "Smith"));
        assertEquals("Smith-provider", result.getTokens().get("ML1"));
        assertTrue(result.getBlankTokensByRule().isEmpty());

        var blankResult = tokenGenerator.getAllTokensViaFieldId(Map.of());
        assertEquals(Token.BLANK, blankResult.getTokens().get("ML1"));
        assertTrue(blankResult.getBlankTokensByRule().contains("ML1"));
    }

    @Test
    void testDeprecatedClassKeyedInferenceApiAdaptsToFieldIds() {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("ML1"));
        when(tokenDefinition.getTokenDefinition("ML1")).thenReturn(List.of());

        var signatures = tokenGenerator.getAllTokenSignatures(
                Map.of(LastNameAttribute.class, "Smith"));

        assertEquals("Smith-provider", signatures.get("ML1"));
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

    /**
     * Verifies non-hash transformers receive and transform raw token values using a passthrough tokenizer.
     *
     * @throws Exception if the token generator encounters a checked transformation failure
     */
    @Test
    void storeRawToken_appliesNonHashTransformersWithPassthroughTokenizer() throws Exception {
        TokenTransformer encryptTransformer = token -> "encrypted:" + token;
        tokenGenerator = new TokenGenerator(
                tokenDefinition,
                new PassthroughTokenizer(List.of(new HashTokenTransformer("secret"), encryptTransformer)));
        TokenGeneratorResult result = new TokenGeneratorResult();

        tokenGenerator.storeRawToken(result, "ML1", "quantized-signature");

        assertEquals("encrypted:quantized-signature", result.getTokens().get("ML1"));
    }

    /**
     * Verifies class-keyed attributes produce raw signatures while requested legacy rules are excluded.
     *
     * @throws Exception if token generation fails
     */
    @Test
    void excludesLegacyRulesAndReturnsValidSignatures() throws Exception {
        when(tokenDefinition.getTokenIdentifiers()).thenReturn(Set.of("keep", "skip"));
        when(tokenDefinition.getTokenDefinition("keep"))
                .thenReturn(List.of(new AttributeExpression(FirstNameAttribute.class, "U")));
        when(tokenDefinition.getTokenDefinition("skip"))
                .thenReturn(List.of(new AttributeExpression(FirstNameAttribute.class, "U")));
        when(tokenizer.tokenize(anyString())).thenReturn("hashed-token");
        Map<Class<? extends Attribute>, String> personAttributes = Map.of(FirstNameAttribute.class, "John");

        assertEquals(Map.of("keep", "JOHN", "skip", "JOHN"), tokenGenerator.getAllTokenSignatures(personAttributes));

        TokenGeneratorResult result = tokenGenerator.generateTokensExcluding(personAttributes, Set.of("skip"));
        assertEquals(Map.of("keep", "hashed-token"), result.getTokens());
    }

    /**
     * Verifies invalid class-keyed attributes are returned as invalid attribute names.
     */
    @Test
    void reportsInvalidClassKeyedAttributes() {
        Map<Class<? extends Attribute>, String> personAttributes = Map.of(
                FirstNameAttribute.class,
                "",
                LastNameAttribute.class,
                "Smith");

        assertEquals(Set.of("FirstName"), tokenGenerator.getInvalidPersonAttributes(personAttributes));
    }

    /**
     * Verifies embedding-derived tokens and precomputed signatures are stored with blank fallbacks.
     *
     * @throws Exception if tokenization fails unexpectedly
     */
    @Test
    void appliesEmbeddingAndPrecomputedSignaturesWithBlankFallback() throws Exception {
        TokenGeneratorResult result = new TokenGeneratorResult();
        tokenGenerator.applyEmbeddingDerivedTokens(result, "ML1-R", List.of("first", "second"));

        when(tokenizer.tokenize("signature")).thenReturn("hashed-signature");
        when(tokenizer.tokenize("blank-signature")).thenReturn(Token.BLANK);
        when(tokenizer.tokenize("failed-signature")).thenThrow(new IllegalStateException("tokenizer failed"));

        tokenGenerator.applyPrecomputedSignature(result, "ML1", "signature");
        tokenGenerator.applyPrecomputedSignature(result, "blank", "blank-signature");
        tokenGenerator.applyPrecomputedSignature(result, "failed", "failed-signature");

        assertEquals("first", result.getTokens().get("ML1-R0"));
        assertEquals("second", result.getTokens().get("ML1-R1"));
        assertEquals("hashed-signature", result.getTokens().get("ML1"));
        assertEquals(Token.BLANK, result.getTokens().get("blank"));
        assertEquals(Token.BLANK, result.getTokens().get("failed"));
        assertEquals(Set.of("blank", "failed"), result.getBlankTokensByRule());
    }

    /**
     * Verifies null, blank, and transformation-failing raw tokens are stored as blank tokens.
     */
    @Test
    void storesNullBlankAndFailedRawTokensAsBlank() {
        TokenTransformer failingTransformer = token -> {
            throw new IllegalStateException("transformer failed");
        };
        tokenGenerator = new TokenGenerator(
                tokenDefinition,
                new PassthroughTokenizer(List.of(failingTransformer)));
        TokenGeneratorResult result = new TokenGeneratorResult();

        tokenGenerator.storeRawToken(result, "null", null);
        tokenGenerator.storeRawToken(result, "blank", Token.BLANK);
        tokenGenerator.storeRawToken(result, "failed", "raw-token");

        assertEquals(Map.of("null", Token.BLANK, "blank", Token.BLANK, "failed", Token.BLANK), result.getTokens());
        assertEquals(Set.of("null", "blank", "failed"), result.getBlankTokensByRule());
    }
}
