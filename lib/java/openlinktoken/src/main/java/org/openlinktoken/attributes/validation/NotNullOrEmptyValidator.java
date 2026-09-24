/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

/**
 * A Validator that asserts the value is <b>NOT</b> <code>null</code>
 * and blank.
 */
public final class NotNullOrEmptyValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    /**
     * Validates that the attribute value is not <code>null</code> or blank.
     */
    @Override
    public boolean eval(String value) {
        return value != null && !value.isBlank();
    }

}
