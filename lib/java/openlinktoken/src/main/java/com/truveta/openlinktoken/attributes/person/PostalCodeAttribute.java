/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import java.util.List;

import com.truveta.openlinktoken.attributes.CombinedAttribute;
import com.truveta.openlinktoken.attributes.SerializableAttribute;

/**
 * Represents the postal code of a person.
 *
 * This class combines US and Canadian postal code implementations to provide
 * functionality for working with postal code fields. It recognizes "PostalCode",
 * "ZipCode", "ZIP3", "ZIP4", and "ZIP5" as valid aliases for this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format. Supports both US ZIP codes (3, 4, or 5 digits) and Canadian
 * postal codes (3, 4, 5, or 6 characters in A1A 1A1 format). ZIP-3 codes (3 digits/characters)
 * are automatically padded to full length during normalization.
 *
 * This class instantiates postal code attributes with minLength=3 to support
 * partial postal codes (ZIP-3, ZIP-4, and partial Canadian formats).
 */
public class PostalCodeAttribute extends CombinedAttribute {

    private static final String NAME = "PostalCode";
    private static final String[] ALIASES = new String[] { NAME, "ZipCode", "ZIP3", "ZIP4", "ZIP5" };

    private final List<SerializableAttribute> implementations = List.of(
            new USPostalCodeAttribute(3),
            new CanadianPostalCodeAttribute(3));

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

    @Override
    protected List<SerializableAttribute> getAttributeImplementations() {
        return implementations;
    }
}
