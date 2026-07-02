/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.definitions;

import java.util.ArrayList;
import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.tokens.Token;

/**
 * Represents the token definition for token T2.
 *
 * <p>
 * It is a collection of attribute expressions
 * that are concatenated together to get the token signature.
 * The token signature is as follows:
 * U(last-name)|U(first-name-1)|birth-date|postal-code-3
 * </p>
 *
 * @see org.openlinktoken.tokens.Token Token
 */
public class T2Token implements Token {
    private static final long serialVersionUID = 1L;
    private static final String ID = "T2";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    public T2Token() {
        definition.add(new AttributeExpression("LastName", LastNameAttribute.class, "T|U"));
        definition.add(new AttributeExpression("FirstName", FirstNameAttribute.class, "T|U"));
        definition.add(new AttributeExpression("BirthDate", BirthDateAttribute.class, "T|D"));
        definition.add(new AttributeExpression("PostalCode", PostalCodeAttribute.class, "T|S(0,3)|U"));
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
