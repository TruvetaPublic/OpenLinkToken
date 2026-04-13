/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokens;

import java.util.List;
import java.util.Map;
import java.util.Set;

import com.truveta.openlinktoken.attributes.AttributeExpression;

/**
 * Encapsulates the token definitions.
 *
 * <p>
 * The tokens are generated using some token generation rules. This class
 * encapsulates the definition of those rules. Together, they are commonly
 * referred to as <b>token definitions</b> or <b>rule definitions</b>.
 *
 * <p>
 * Each token/rule definition is a collection of
 * <code>AttributeExpression</code> that are concatenated together to get
 * the token signature.
 *
 * @see com.truveta.openlinktoken.attributes.AttributeExpression
 *      AttributeExpression
 */
public class TokenDefinition implements BaseTokenDefinition {
    private static final long serialVersionUID = 1L;
    private final Map<String, List<AttributeExpression>> definitions;

    /**
     * Initializes the token definitions.
     */
    public TokenDefinition() {
        // load all implementations of Token interface and store in definitions
        this.definitions = TokenRegistry.loadAllTokens();
    }

    @Override
    public String getVersion() {
        return "2.0";
    }

    @Override
    public Set<String> getTokenIdentifiers() {
        return definitions.keySet();
    }

    @Override
    public List<AttributeExpression> getTokenDefinition(String tokenId) {
        return definitions.get(tokenId);
    }
}
