/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

import java.util.List;

import org.openlinktoken.attributes.BaseAttribute;
import org.openlinktoken.attributes.validation.RegexValidator;
import org.openlinktoken.attributes.validation.SerializableAttributeValidator;

/**
 * Represents a generic integer attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * integer fields. It recognizes "Integer" as the primary alias for this attribute type.
 *
 * The attribute performs normalization on input values, trimming whitespace and
 * ensuring the value is a valid integer.
 *
 * The attribute also performs validation on input values, ensuring they are numeric
 * integers (no decimals, no negative sign handling beyond parsing).
 */
public class IntegerAttribute extends BaseAttribute {

    private static final String NAME = "Integer";
    private static final String[] ALIASES = new String[] { NAME };

    /**
     * Regular expression pattern for validating integer format.
     *
     * This regex validates that the input is:
     * - Optional leading whitespace
     * - Optional leading sign (+ or -)
     * - One or more digits
     * - Optional trailing whitespace
     */
    private static final String INTEGER_REGEX = "^\\s*[+-]?\\d+\\s*$";

    public IntegerAttribute() {
        super(List.of(new RegexValidator(INTEGER_REGEX)));
    }

    /**
     * Protected constructor for subclasses to add additional validators.
     *
     * @param additionalValidators additional validators to apply beyond the base integer format validation
     */
    protected IntegerAttribute(List<SerializableAttributeValidator> additionalValidators) {
        super(createValidatorList(additionalValidators));
    }

    private static List<SerializableAttributeValidator> createValidatorList(
            List<SerializableAttributeValidator> additionalValidators) {
        java.util.ArrayList<SerializableAttributeValidator> validators = new java.util.ArrayList<>();
        validators.add(new RegexValidator(INTEGER_REGEX));
        validators.addAll(additionalValidators);
        return validators;
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
            throw new IllegalArgumentException("Integer value cannot be null");
        }

        // Trim whitespace and parse as integer
        String trimmed = value.trim();

        try {
            long intValue = Long.parseLong(trimmed);
            // Return the trimmed integer as a string
            return String.valueOf(intValue);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid integer format: " + value);
        }
    }

}
