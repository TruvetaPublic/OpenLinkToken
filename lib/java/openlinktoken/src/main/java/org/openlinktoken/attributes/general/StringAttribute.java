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

    public StringAttribute() {
        super(List.of());
    }

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

    @Override
    public String normalize(String value) {
        if (value == null) {
            throw new IllegalArgumentException("String value cannot be null");
        }

        return value.trim();
    }

}
