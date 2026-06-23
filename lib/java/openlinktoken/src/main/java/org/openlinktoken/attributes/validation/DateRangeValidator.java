/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import java.text.ParseException;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Date;
import java.util.Locale;

import org.apache.commons.lang3.time.DateUtils;

import lombok.Getter;
import lombok.Setter;

/**
 * A generic validator that asserts that a date value is within
 * a configurable date range.
 *
 * This validator can be configured with:
 * - Minimum date (inclusive) - can be null for no lower bound
 * - Maximum date (inclusive) - can be null for no upper bound
 * - Use current date as maximum - dynamically sets max to today
 *
 * If both minDate and maxDate are null and useCurrentDateAsMax is false,
 * the validator will only check that the date can be parsed.
 */
@Getter
@Setter
public final class DateRangeValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    // Supported date formats for parsing
    private static final String[] POSSIBLE_INPUT_FORMATS = new String[] {
            "yyyy-MM-dd", "yyyy/MM/dd", "MM/dd/yyyy",
            "MM-dd-yyyy", "dd.MM.yyyy",
            // ISO 8601 timestamp formats
            "yyyy-MM-dd'T'HH:mm:ss.SSSX", "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
            "yyyy-MM-dd'T'HH:mm:ssX", "yyyy-MM-dd'T'HH:mm:ssXXX"
    };

    private final LocalDate minDate;
    private final LocalDate maxDate;
    private final boolean useCurrentDateAsMax;

    /**
     * Creates a DateRangeValidator with specified minimum and maximum dates.
     *
     * @param minDate the minimum allowed date (inclusive), or null for no lower bound
     * @param maxDate the maximum allowed date (inclusive), or null for no upper bound
     */
    public DateRangeValidator(LocalDate minDate, LocalDate maxDate) {
        this.minDate = minDate;
        this.maxDate = maxDate;
        this.useCurrentDateAsMax = false;
    }

    /**
     * Creates a DateRangeValidator with specified minimum date and option to use current date as max.
     *
     * @param minDate the minimum allowed date (inclusive), or null for no lower bound
     * @param useCurrentDateAsMax if true, uses current date as maximum; otherwise no upper bound
     */
    public DateRangeValidator(LocalDate minDate, boolean useCurrentDateAsMax) {
        this.minDate = minDate;
        this.maxDate = null;
        this.useCurrentDateAsMax = useCurrentDateAsMax;
    }

    /**
     * Creates a DateRangeValidator with no bounds (will only validate parseable dates).
     */
    public DateRangeValidator() {
        this.minDate = null;
        this.maxDate = null;
        this.useCurrentDateAsMax = false;
    }

    /**
     * Validates that the date value is within the configured range.
     *
     * @param value the date string to validate
     * @return true if the date is within the configured range, false otherwise
     */
    @Override
    public boolean eval(String value) {
        if (value == null || value.trim().isEmpty()) {
            return false;
        }

        try {
            // Parse the date using various supported formats
            Date date = DateUtils.parseDateStrictly(value, Locale.ENGLISH, POSSIBLE_INPUT_FORMATS);

            // Convert Date to LocalDate
            LocalDate localDate = date.toInstant().atZone(ZoneId.systemDefault()).toLocalDate();

            // Check minimum date
            if (minDate != null && localDate.isBefore(minDate)) {
                return false;
            }

            // Check maximum date
            LocalDate effectiveMaxDate = useCurrentDateAsMax ? LocalDate.now() : maxDate;
            return effectiveMaxDate == null || !localDate.isAfter(effectiveMaxDate);

        } catch (ParseException e) {
            // If the date cannot be parsed, it's invalid
            return false;
        }
    }
}
