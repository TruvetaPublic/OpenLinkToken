/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.person;

import java.util.List;

import org.openlinktoken.attributes.general.IntegerAttribute;
import org.openlinktoken.attributes.validation.AgeRangeValidator;

/**
 * Represents the age attribute.
 *
 * This class extends IntegerAttribute and provides functionality for working with
 * age fields. It recognizes "Age" as the primary alias for this attribute type.
 *
 * The attribute performs normalization on input values, trimming whitespace and
 * ensuring the value is a valid integer (inherited from IntegerAttribute).
 *
 * The attribute also performs validation on input values, ensuring they:
 * - Are numeric integers (inherited from IntegerAttribute)
 * - Fall within an acceptable range (0-120)
 */
public class AgeAttribute extends IntegerAttribute {

    private static final String NAME = "Age";
    private static final String[] ALIASES = new String[] { NAME };

    public AgeAttribute() {
        super(List.of(new AgeRangeValidator()));
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
