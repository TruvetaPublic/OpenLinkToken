/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.definitions;

import java.util.ArrayList;

import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.tokens.Token;

/**
 * Represents optional T6 token definition.
 */
public class T6Token implements Token {
    private static final long serialVersionUID = 1L;
    private static final String ID = "T6";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    @Override
    public String getIdentifier() {
        return ID;
    }

    @Override
    public ArrayList<AttributeExpression> getDefinition() {
        return definition;
    }
}
