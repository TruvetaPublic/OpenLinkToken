/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens.definitions;

import java.util.ArrayList;

import com.truveta.opentoken.attributes.AttributeExpression;
import com.truveta.opentoken.tokens.Token;

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
