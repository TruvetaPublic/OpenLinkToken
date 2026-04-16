/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

/**
 * A generic interface for attribute validation.
 */
public interface AttributeValidator {

    /**
     * Validates an attribute value.
     *
     * @param value the attribute value.
     *
     * @return <code>true</code> if the attribute is valid; <code>false</code>
     *         otherwise.
     */
    boolean eval(String value);
}
