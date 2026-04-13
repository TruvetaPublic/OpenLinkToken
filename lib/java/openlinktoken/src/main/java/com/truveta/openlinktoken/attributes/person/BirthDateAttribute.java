/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import java.time.LocalDate;
import java.util.List;

import com.truveta.openlinktoken.attributes.general.DateAttribute;
import com.truveta.openlinktoken.attributes.validation.DateRangeValidator;

/**
 * Represents the birth date attribute.
 *
 * This class extends DateAttribute and provides functionality for working with
 * birth date fields. It recognizes "BirthDate" and "DateOfBirth" as valid aliases
 * for this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format (yyyy-MM-dd) (inherited from DateAttribute).
 *
 * The attribute also performs validation on input values, ensuring they:
 * - Match one of the supported date formats (inherited from DateAttribute)
 * - Fall within an acceptable range for birth dates (1910-01-01 to today)
 */
public class BirthDateAttribute extends DateAttribute {

    private static final String NAME = "BirthDate";
    private static final String[] ALIASES = new String[] { NAME, "DateOfBirth" };

    public BirthDateAttribute() {
        super(List.of(new DateRangeValidator(LocalDate.of(1910, 1, 1), true)));
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
