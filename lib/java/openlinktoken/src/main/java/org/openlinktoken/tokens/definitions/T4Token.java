/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.definitions;

import java.util.ArrayList;
import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import org.openlinktoken.tokens.Token;

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
 * @see org.openlinktoken.tokens.Token Token
 */
public class T4Token implements Token {
    private static final long serialVersionUID = 1L;
    private static final String ID = "T4";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    public T4Token() {
        definition.add(new AttributeExpression("SocialSecurityNumber", SocialSecurityNumberAttribute.class, "T|M(\\d+)"));
        definition.add(new AttributeExpression("Sex", SexAttribute.class, "T|U"));
        definition.add(new AttributeExpression("BirthDate", BirthDateAttribute.class, "T|D"));
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
