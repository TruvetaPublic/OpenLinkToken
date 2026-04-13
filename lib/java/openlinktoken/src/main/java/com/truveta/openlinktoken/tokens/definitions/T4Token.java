/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokens.definitions;

import java.util.ArrayList;
import com.truveta.openlinktoken.attributes.AttributeExpression;
import com.truveta.openlinktoken.attributes.person.BirthDateAttribute;
import com.truveta.openlinktoken.attributes.person.SexAttribute;
import com.truveta.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import com.truveta.openlinktoken.tokens.Token;

/**
 * Represents the token definition for token T4.
 *
 * <p>
 * It is a collection of attribute expressions
 * that are concatenated together to get the token signature.
 * The token signature is as follows:
 * social-security-number|U(gender)|birth-date
 * </p>
 *
 * @see com.truveta.openlinktoken.tokens.Token Token
 */
public class T4Token implements Token {
    private static final long serialVersionUID = 1L;
    private static final String ID = "T4";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    public T4Token() {
        definition.add(new AttributeExpression(SocialSecurityNumberAttribute.class, "T|M(\\d+)"));
        definition.add(new AttributeExpression(SexAttribute.class, "T|U"));
        definition.add(new AttributeExpression(BirthDateAttribute.class, "T|D"));
    }

    @Override
    public String getIdentifier() {
        return ID;
    }

    @Override
    public ArrayList<AttributeExpression> getDefinition() {
        return definition;
    }
}
