/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

import java.util.List;

import org.openlinktoken.attributes.BaseAttribute;
import org.openlinktoken.attributes.validation.RegexValidator;
import org.openlinktoken.attributes.validation.SerializableAttributeValidator;

/**
 * Represents a generic decimal (floating-point) attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * decimal fields. It recognizes "Decimal" as the primary alias for this attribute type.
 *
 * The attribute performs normalization on input values, trimming whitespace and
 * ensuring the value is a valid decimal number.
 *
 * The attribute also performs validation on input values, ensuring they match
 * common decimal number formats (with or without decimal points, scientific notation).
 */
public class DecimalAttribute extends BaseAttribute {

    private static final String NAME = "Decimal";
    private static final String[] ALIASES = new String[] { NAME };

    /**
     * Regular expression pattern for validating decimal format.
     *
     * This regex validates that the input is:
     * - Optional leading whitespace
     * - Optional leading sign (+ or -)
     * - One or more digits, optionally followed by a decimal point and more digits
     * - OR a decimal point followed by one or more digits
     * - Optional exponent notation (e or E followed by optional sign and digits)
     * - Optional trailing whitespace
     *
     * Valid examples: 123, -45.67, +89.0, .5, 1., 1.5e10, -3.14E-2
     */
    private static final String DECIMAL_REGEX = "^\\s*[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?\\s*$";

    public DecimalAttribute() {
        super(List.of(new RegexValidator(DECIMAL_REGEX)));
    }

    /**
     * Protected constructor for subclasses to add additional validators.
     *
     * @param additionalValidators additional validators to apply beyond the base decimal format validation
     */
    protected DecimalAttribute(List<SerializableAttributeValidator> additionalValidators) {
        super(createValidatorList(additionalValidators));
    }

    private static List<SerializableAttributeValidator> createValidatorList(
            List<SerializableAttributeValidator> additionalValidators) {
        java.util.ArrayList<SerializableAttributeValidator> validators = new java.util.ArrayList<>();
        validators.add(new RegexValidator(DECIMAL_REGEX));
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
            throw new IllegalArgumentException("Decimal value cannot be null");
        }

        // Trim whitespace and parse as double
        String trimmed = value.trim();

        try {
            double decimalValue = Double.parseDouble(trimmed);
            // Return the decimal value as a string
            return String.valueOf(decimalValue);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid decimal format: " + value);
        }
    }

}
