/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

/**
 * Rejects {@code null} and blank attribute values.
 */
public final class NotNullOrEmptyValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    /**
     * Validates that the attribute value is non-null and not blank.
     *
     * @param value the value to validate
     * @return {@code true} if the value is non-null and not blank
     */
    @Override
    public boolean eval(String value) {
        return value != null && !value.isBlank();
    }

}
