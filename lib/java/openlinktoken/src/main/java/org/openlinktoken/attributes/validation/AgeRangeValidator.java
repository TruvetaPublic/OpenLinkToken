/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import lombok.NoArgsConstructor;

/**
 * A Validator that asserts that the age value is within
 * an acceptable range (between 0 and 120).
 *
 * This validator checks that ages are:
 * - Not negative
 * - Not greater than 120 years
 *
 * If the age is outside this range, the validation fails.
 */
@NoArgsConstructor
public final class AgeRangeValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    private static final int MIN_AGE = 0;
    private static final int MAX_AGE = 120;

    /**
     * Validates that the age value is within acceptable range.
     *
     * @param value the age string to validate
     * @return true if the age is within acceptable range (0 to 120),
     *         false otherwise
     */
    @Override
    public boolean eval(String value) {
        if (value == null || value.trim().isEmpty()) {
            return false;
        }

        try {
            int age = Integer.parseInt(value.trim());
            return age >= MIN_AGE && age <= MAX_AGE;
        } catch (NumberFormatException e) {
            // If the value cannot be parsed as an integer, it's invalid
            return false;
        }
    }
}
