/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.person;

import java.util.List;

import org.openlinktoken.attributes.general.YearAttribute;
import org.openlinktoken.attributes.validation.YearRangeValidator;

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

    /** Creates a birth-year attribute with the standard birth-year range validator. */
    public BirthYearAttribute() {
        super(List.of(new YearRangeValidator()));
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

}
