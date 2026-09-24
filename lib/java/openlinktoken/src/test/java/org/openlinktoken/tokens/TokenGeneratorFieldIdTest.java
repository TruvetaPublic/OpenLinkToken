/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.FieldRegistry;
import org.openlinktoken.attributes.general.StringAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.tokens.tokenizer.PassthroughTokenizer;

/** Tests field-ID token generation with shared attribute types and legacy expressions. */
class TokenGeneratorFieldIdTest {

    private TokenGenerator tokenGenerator;

    /** Registers custom fields and creates the test token definitions. */
    @BeforeEach
    void setUp() {
        var stringAttr = new StringAttribute();
        var registry = FieldRegistry.Builder.fromDefaults()
                .register("MotherLastName", StringAttribute.class, stringAttr)
                .register("FatherLastName", StringAttribute.class, stringAttr)
                .build();

        BaseTokenDefinition tokenDefinition = new BaseTokenDefinition() {
            private final Map<String, List<AttributeExpression>> defs = Map.of(
                    "T_MULTI", List.of(
                            new AttributeExpression("MotherLastName", StringAttribute.class, "T|U"),
                            new AttributeExpression("FatherLastName", StringAttribute.class, "T|U"),
                            new AttributeExpression("FirstName", FirstNameAttribute.class, "T|S(0,1)|U")),
                    "T_LEGACY", List.of(
                            new AttributeExpression(LastNameAttribute.class, "T|U"),
                            new AttributeExpression(FirstNameAttribute.class, "T|S(0,1)|U"),
                            new AttributeExpression(SexAttribute.class, "T|U")));

            /** Returns the version label for these test token definitions. */
            @Override
            public String getVersion() {
                return "test";
            }

            /** Returns the identifiers backed by the configured test definitions. */
            @Override
            public Set<String> getTokenIdentifiers() {
                return defs.keySet();
            }

            /**
             * Looks up the expressions configured for a token identifier.
             *
             * @param tokenId identifier to look up
             * @return its expressions, or {@code null} when no definition is configured
             */
            @Override
            public List<AttributeExpression> getTokenDefinition(String tokenId) {
                return defs.get(tokenId);
            }
        };

        tokenGenerator = new TokenGenerator(tokenDefinition, new PassthroughTokenizer(List.of()), registry);
    }

    /** Verifies two fields using the same attribute type contribute to one token. */
    @Test
    void testMultiFieldSameTypeGeneratesToken() {
        Map<String, String> person = Map.of(
                "MotherLastName", "Garcia",
                "FatherLastName", "Lopez",
                "FirstName", "Ana");

        var result = tokenGenerator.getAllTokensViaFieldId(person);
        assertTrue(result.getTokens().containsKey("T_MULTI"));
        assertEquals("GARCIA|LOPEZ|A", result.getTokens().get("T_MULTI"));
    }

    /** Verifies a missing custom field produces a blank token. */
    @Test
    void testMultiFieldMissingFieldSkipsToken() {
        Map<String, String> person = Map.of(
                "MotherLastName", "Garcia",
                "FirstName", "Ana");

        var result = tokenGenerator.getAllTokensViaFieldId(person);
        // Missing field produces BLANK token
        assertEquals(Token.BLANK, result.getTokens().get("T_MULTI"));
    }

    /** Verifies legacy class-based expressions work through the field-ID API. */
    @Test
    void testLegacyExpressionsWorkWithFieldIdApi() {
        Map<String, String> person = Map.of(
                "LastName", "Smith",
                "FirstName", "John",
                "Sex", "M");

        var result = tokenGenerator.getAllTokensViaFieldId(person);
        assertTrue(result.getTokens().containsKey("T_LEGACY"));
        assertEquals("SMITH|J|MALE", result.getTokens().get("T_LEGACY"));
    }

    /** Verifies field-ID signature generation handles both custom and legacy definitions. */
    @Test
    void testSignaturesByFieldId() {
        Map<String, String> person = Map.of(
                "MotherLastName", "Garcia",
                "FatherLastName", "Lopez",
                "FirstName", "Ana",
                "LastName", "Smith",
                "Sex", "F");

        var signatures = tokenGenerator.getAllTokenSignaturesViaFieldId(person);
        assertTrue(signatures.containsKey("T_MULTI"));
        assertEquals("GARCIA|LOPEZ|A", signatures.get("T_MULTI"));
        assertTrue(signatures.containsKey("T_LEGACY"));
        assertEquals("SMITH|A|FEMALE", signatures.get("T_LEGACY"));
    }

    /** Verifies invalid custom-field values are recorded and produce a blank token. */
    @Test
    void testInvalidAttributeTracked() {
        Map<String, String> person = Map.of(
                "MotherLastName", "",
                "FatherLastName", "Lopez",
                "FirstName", "Ana");

        var result = tokenGenerator.getAllTokensViaFieldId(person);
        // Invalid attribute produces BLANK token
        assertEquals(Token.BLANK, result.getTokens().get("T_MULTI"));
        assertFalse(result.getInvalidAttributes().isEmpty());
    }
}
