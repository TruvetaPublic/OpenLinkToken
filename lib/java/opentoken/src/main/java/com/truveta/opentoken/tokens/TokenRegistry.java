/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

import com.truveta.opentoken.attributes.AttributeExpression;
import java.util.ServiceLoader;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Registry for loading and managing token definitions.
 * <p>
 * Uses Java's ServiceLoader mechanism to discover all implementations
 * of the Token interface at runtime.
 * </p>
 */
public class TokenRegistry {

    /**
     * Private constructor to prevent instantiation.
     * This is a utility class with only static methods.
     */
    private TokenRegistry() {
        // Utility class - no instances allowed
    }

    /**
     * Loads all token definitions using the ServiceLoader mechanism.
     * <p>
     * This method discovers all Token implementations registered in
     * META-INF/services/com.truveta.opentoken.tokens.Token and creates
     * a map of token identifiers to their attribute expression definitions.
     * </p>
     *
     * @return a map where keys are token identifiers (e.g., "T1", "T2")
     *         and values are lists of AttributeExpression defining the token
     */
    public static Map<String, List<AttributeExpression>> loadAllTokens() {
        Map<String, List<AttributeExpression>> tokensMap = new HashMap<>();
        ServiceLoader<Token> loader = ServiceLoader.load(Token.class);
        for (Token token : loader) {
            tokensMap.put(token.getIdentifier(), token.getDefinition());
        }
        return tokensMap;
    }
}
