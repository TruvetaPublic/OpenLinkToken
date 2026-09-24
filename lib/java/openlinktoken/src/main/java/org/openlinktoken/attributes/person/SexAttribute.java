/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.person;

import java.util.List;

import org.openlinktoken.attributes.BaseAttribute;
import org.openlinktoken.attributes.validation.RegexValidator;

/**
 * Represents an assigned sex of a person.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * these type of fields. It recognizes "Sex" or "Gender" as valid aliases for
 * this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format (M or F).
 */
public class SexAttribute extends BaseAttribute {

    private static final String NAME = "Sex";
    private static final String[] ALIASES = new String[] { NAME, "Gender" };

    /**
     * Regular expression pattern for validating sex/gender values.
     *
     * This pattern matches the following formats (case-insensitive):
     *  - "M" or "F"
     *  - "Male" or "Female"
     *
     * Breakdown of the regex:
     *   ^                 Start of string
     *   (                 Start of group:
     *     [Mm](ale)?      'M' or 'm', optionally followed by 'ale'
     *     |               OR
     *     [Ff](emale)?    'F' or 'f', optionally followed by 'emale'
     *   )
     *   $                 End of string
     */
    private static final String VALIDATE_REGEX = "^([Mm](ale)?|[Ff](emale)?)$";

    /** Creates a sex attribute with the standard accepted-value validator. */
    public SexAttribute() {
        super(
                List.of(
                        new RegexValidator(VALIDATE_REGEX)));
    }

    /** {@inheritDoc} */
    @Override
    public String getName() {
        return NAME;
    }

    /**
     * Converts an initial {@code M} or {@code F} to the corresponding full value.
     *
     * @param value the value to normalize
     * @return {@code "Male"} or {@code "Female"} for a recognized initial, or {@code null} otherwise
     * @throws NullPointerException if {@code value} is {@code null}
     * @throws IndexOutOfBoundsException if {@code value} is empty
     */
    @Override
    public String normalize(String value) {
        switch (value.charAt(0)) {
            case 'M':
            case 'm':
                return "Male";
            case 'F':
            case 'f':
                return "Female";
            default:
                return null;
        }
    }

    /** {@inheritDoc} */
    @Override
    public String[] getAliases() {
        return ALIASES;
    }
}
