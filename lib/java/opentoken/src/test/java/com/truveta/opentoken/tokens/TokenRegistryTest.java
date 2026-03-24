/**
 * Copyright (c) Truveta. All rights reserved.
 */

package com.truveta.opentoken.tokens;

import com.truveta.opentoken.attributes.AttributeExpression;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

class TokenRegistryTest {

    @Test
    void testLoadAllTokensReturnsNonEmptyMap() {
        Map<String, List<AttributeExpression>> tokens = TokenRegistry.loadAllTokens();

        assertFalse(tokens.isEmpty(), "Tokens map should not be empty");

        String[] expectedTokens = { "T1", "T2", "T3", "T4", "T5" };

        for (String tokenId : expectedTokens) {
            assertTrue(tokens.containsKey(tokenId), "Tokens map should contain " + tokenId);

            List<AttributeExpression> definitions = tokens.get(tokenId);
            assertNotNull(definitions, "Definitions for " + tokenId + " should not be null");
            assertFalse(definitions.isEmpty(), "Definitions for " + tokenId + " should not be empty");
        }
    }
}
