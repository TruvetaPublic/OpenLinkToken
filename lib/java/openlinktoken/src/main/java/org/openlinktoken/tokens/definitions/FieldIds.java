/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.definitions;

import org.openlinktoken.attributes.AttributeExpression;

/**
 * Enumerates the field identifiers referenced by the built-in T1-T5 token definitions.
 *
 * <p>
 * Centralizing these values avoids duplicating the same field-id strings across
 * multiple token definition classes.
 *
 * @see AttributeExpression
 */
public enum FieldIds {
    LAST_NAME("LastName"),
    FIRST_NAME("FirstName"),
    SEX("Sex"),
    BIRTH_DATE("BirthDate"),
    POSTAL_CODE("PostalCode"),
    SOCIAL_SECURITY_NUMBER("SocialSecurityNumber");

    private final String fieldId;

    FieldIds(String fieldId) {
        this.fieldId = fieldId;
    }

    /**
     * Returns the field identifier string used to key person attributes.
     *
     * @return the field id
     */
    public String getFieldId() {
        return fieldId;
    }
}
