/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.general;

/**
 * Represents an attribute for handling record identifiers.
 *
 * This class extends StringAttribute and provides functionality for working with
 * identifier fields. It recognizes "RecordId" and "Id" as valid aliases for
 * this attribute type.
 *
 * The attribute normalizes values by trimming leading and trailing whitespace
 * (inherited from StringAttribute).
 */
public class RecordIdAttribute extends StringAttribute {

    private static final String NAME = "RecordId";
    private static final String[] ALIASES = new String[] { NAME, "Id" };

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

}
