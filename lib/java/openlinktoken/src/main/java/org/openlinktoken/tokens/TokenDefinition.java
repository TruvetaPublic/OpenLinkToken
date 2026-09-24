/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;
import java.util.Map;
import java.util.Set;

import org.openlinktoken.attributes.AttributeExpression;

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
 * @see org.openlinktoken.attributes.AttributeExpression
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

    /**
     * Returns the version of the built-in token definitions.
     *
     * @return the definition version, {@code "2.0"}
     */
    @Override
    public String getVersion() {
        return "2.0";
    }

    /** {@inheritDoc} */
    @Override
    public Set<String> getTokenIdentifiers() {
        return definitions.keySet();
    }

    /**
     * Returns the attribute expressions for a token identifier.
     *
     * @param tokenId the token identifier
     * @return the expressions for the identifier, or {@code null} if it is not registered
     */
    @Override
    public List<AttributeExpression> getTokenDefinition(String tokenId) {
        return definitions.get(tokenId);
    }
}
