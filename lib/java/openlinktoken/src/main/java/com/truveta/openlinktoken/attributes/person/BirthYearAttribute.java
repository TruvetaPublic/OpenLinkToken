/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import java.util.List;

import com.truveta.openlinktoken.attributes.general.YearAttribute;
import com.truveta.openlinktoken.attributes.validation.YearRangeValidator;

/**
 * Represents the birth year attribute.
 *
 * This class extends YearAttribute and provides functionality for working with
 * birth year fields. It recognizes "BirthYear" as a valid alias for this
 * attribute type.
 *
 * The attribute performs normalization on input values by trimming whitespace
 * and validates that the birth year is a 4-digit year between 1910 and the current year.
 */
public class BirthYearAttribute extends YearAttribute {

    private static final String NAME = "BirthYear";
    private static final String[] ALIASES = new String[] { NAME, "YearOfBirth" };

    public BirthYearAttribute() {
        super(List.of(new YearRangeValidator()));
    }

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

}
