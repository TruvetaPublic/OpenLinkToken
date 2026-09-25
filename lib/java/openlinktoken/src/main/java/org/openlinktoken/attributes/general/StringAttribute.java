/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

import java.util.List;

import org.openlinktoken.attributes.BaseAttribute;

/**
 * Represents a generic string attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * general text fields. It recognizes "String" and "Text" as valid aliases for
 * this attribute type.
 *
 * The attribute performs normalization on input values by trimming leading and
 * trailing whitespace.
 *
 * The attribute validates that values are not null or empty (after trimming).
 */
public class StringAttribute extends BaseAttribute {

    private static final String NAME = "String";
    private static final String[] ALIASES = new String[] { NAME, "Text" };

    /** Creates a string attribute with the base non-empty validation rule. */
    public StringAttribute() {
        super(List.of());
    }

    /** {@inheritDoc} */
    @Override
    public String getName() {
        return NAME;
    }

    /** {@inheritDoc} */
    @Override
    public String[] getAliases() {
        return ALIASES;
    }

    /**
     * Trims leading and trailing whitespace from the value.
     *
     * @param value the string value to normalize
     * @return the trimmed value
     * @throws IllegalArgumentException if the value is {@code null}
     */
    @Override
    public String normalize(String value) {
        if (value == null) {
            throw new IllegalArgumentException("String value cannot be null");
        }

        return value.trim();
    }

}
