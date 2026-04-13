/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.validation;

import java.time.Year;

import lombok.NoArgsConstructor;

/**
 * A Validator that asserts that a year value is within
 * an acceptable range (between 1910 and current year).
 *
 * This validator checks that years are:
 * - Not before 1910
 * - Not after the current year
 *
 * If the year is outside this range, the validation fails.
 */
@NoArgsConstructor
public final class YearRangeValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    private static final int MIN_YEAR = 1910;

    /**
     * Validates that the year value is within acceptable range.
     *
     * @param value the year string to validate
     * @return true if the year is within acceptable range (1910 to current year),
     *         false otherwise
     */
    @Override
    public boolean eval(String value) {
        if (value == null || value.trim().isEmpty()) {
            return false;
        }

        try {
            int year = Integer.parseInt(value.trim());
            int currentYear = Year.now().getValue();
            return year >= MIN_YEAR && year <= currentYear;
        } catch (NumberFormatException e) {
            // If the value cannot be parsed as an integer, it's invalid
            return false;
        }
    }
}
