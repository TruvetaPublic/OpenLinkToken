/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens.definitions;

import java.util.ArrayList;

import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.tokens.Token;

/**
 * Represents optional ML1 token definition.
 */
public class ML1Token implements Token {
    private static final long serialVersionUID = 1L;
    public static final String TOKEN_ID = "ML1";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    /**
     * Return the stable registry identifier for this token definition.
     *
     * @return ML1 token identifier
     */
    @Override
    public String getIdentifier() {
        return TOKEN_ID;
    }

    /**
     * Return the attribute expressions that make up the ML1 definition.
     *
     * @return ordered ML1 attribute expressions
     */
    @Override
    public ArrayList<AttributeExpression> getDefinition() {
        return definition;
    }
}
