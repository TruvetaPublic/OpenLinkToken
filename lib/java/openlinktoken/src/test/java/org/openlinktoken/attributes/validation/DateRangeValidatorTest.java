/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.time.LocalDate;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class DateRangeValidatorTest {

    private DateRangeValidator validator;

    @BeforeEach
    void setUp() {
        // Create a validator with the minimum date set to 1910-01-01 (previously used as the lower bound for birth dates)
        validator = new DateRangeValidator(LocalDate.of(1910, 1, 1), true);
    }

    @Test
    void eval_ValidDatesWithinRange_ShouldReturnTrue() {
        // Test boundary dates that should be valid
        assertTrue(validator.eval("1910-01-01")); // Minimum valid date
        assertTrue(validator.eval("01/01/1910")); // Same date, different format

        // Test today's date (should be valid)
        LocalDate today = LocalDate.now();
        assertTrue(validator.eval(today.toString()));

        // Test dates within acceptable range
        assertTrue(validator.eval("1950-06-15"));
        assertTrue(validator.eval("12/25/1990"));
        assertTrue(validator.eval("29.02.2000")); // Leap year
        assertTrue(validator.eval("2000-12-31"));
        assertTrue(validator.eval("01-01-2020"));
    }

    @Test
    void eval_DatesBeforeMinimum_ShouldReturnFalse() {
        // Test dates before 1910-01-01
        assertFalse(validator.eval("1909-12-31"));
        assertFalse(validator.eval("12/31/1909"));
        assertFalse(validator.eval("1900-01-01"));
        assertFalse(validator.eval("01/01/1900"));
        assertFalse(validator.eval("31.12.1909"));
        assertFalse(validator.eval("1850-06-15"));
    }

    @Test
    void eval_DatesAfterToday_ShouldReturnFalse() {
        // Test dates after today
        LocalDate tomorrow = LocalDate.now().plusDays(1);
        LocalDate nextYear = LocalDate.now().plusYears(1);

        assertFalse(validator.eval(tomorrow.toString()));
        assertFalse(validator.eval(nextYear.toString()));
        assertFalse(validator.eval("2030-01-01"));
        assertFalse(validator.eval("01/01/2030"));
        assertFalse(validator.eval("2050-12-25"));
    }

    @Test
    void eval_InvalidDateFormats_ShouldReturnFalse() {
        // Test invalid date formats
        assertFalse(validator.eval("20231026")); // No separators
        assertFalse(validator.eval("2023-13-01")); // Invalid month
        assertFalse(validator.eval("2023-02-30")); // Invalid day for February
        assertFalse(validator.eval("invalid-date"));
        assertFalse(validator.eval("2023/15/45")); // Invalid month and day
        assertFalse(validator.eval("abc-def-ghi"));
    }

    @Test
    void eval_NullAndEmptyValues_ShouldReturnFalse() {
        assertFalse(validator.eval(null));
        assertFalse(validator.eval(""));
        assertFalse(validator.eval("   ")); // Whitespace only
        assertFalse(validator.eval("\t\n"));
    }

    @Test
    void eval_VariousDateFormats_ShouldWorkCorrectly() {
        // Test all supported formats for the same date
        assertTrue(validator.eval("1995-07-15")); // yyyy-MM-dd
        assertTrue(validator.eval("1995/07/15")); // yyyy/MM/dd
        assertTrue(validator.eval("07/15/1995")); // MM/dd/yyyy
        assertTrue(validator.eval("07-15-1995")); // MM-dd-yyyy
        assertTrue(validator.eval("15.07.1995")); // dd.MM.yyyy
    }

    @Test
    void eval_LeapYearDates_ShouldWorkCorrectly() {
        // Test valid leap year dates
        assertTrue(validator.eval("2000-02-29")); // Year 2000 is a leap year
        assertTrue(validator.eval("1996-02-29")); // 1996 is a leap year

        // Test invalid leap year dates
        assertFalse(validator.eval("1900-02-29")); // 1900 is not a leap year
        assertFalse(validator.eval("2001-02-29")); // 2001 is not a leap year
    }

    @Test
    void serialization_ShouldPreserveValidationBehavior() throws Exception {
        // Serialize the validator
        ByteArrayOutputStream byteOut = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(byteOut);
        out.writeObject(validator);
        out.close();

        // Deserialize the validator
        ByteArrayInputStream byteIn = new ByteArrayInputStream(byteOut.toByteArray());
        ObjectInputStream in = new ObjectInputStream(byteIn);
        DateRangeValidator deserializedValidator = (DateRangeValidator) in.readObject();
        in.close();

        // Test that both validators behave identically
        String[] testValues = {
                "1910-01-01", // Valid boundary
                "1909-12-31", // Invalid (too old)
                "2030-01-01", // Invalid (future)
                "1990-06-15", // Valid middle range
                "invalid-date", // Invalid format
                null // Null value
        };

        for (String value : testValues) {
            boolean originalResult = validator.eval(value);
            boolean deserializedResult = deserializedValidator.eval(value);

            assertEquals(originalResult, deserializedResult,
                    String.format("Validation results should match for value: %s (original: %s, deserialized: %s)",
                            value, originalResult, deserializedResult));
        }
    }

    @Test
    void eval_EdgeCaseDates_ShouldWorkCorrectly() {
        LocalDate today = LocalDate.now();
        LocalDate yesterday = today.minusDays(1);
        LocalDate minDate = LocalDate.of(1910, 1, 1);
        LocalDate dayBeforeMinDate = minDate.minusDays(1);

        // Test edge cases around boundaries
        assertTrue(validator.eval(today.toString())); // Today should be valid
        assertTrue(validator.eval(yesterday.toString())); // Yesterday should be valid
        assertTrue(validator.eval(minDate.toString())); // Minimum date should be valid
        assertFalse(validator.eval(dayBeforeMinDate.toString())); // Day before minimum should be invalid
    }

    @Test
    void customRange_WithFixedMinAndMax_ShouldValidateCorrectly() {
        // Test with a fixed date range
        LocalDate minDate = LocalDate.of(2020, 1, 1);
        LocalDate maxDate = LocalDate.of(2023, 12, 31);
        DateRangeValidator customValidator = new DateRangeValidator(minDate, maxDate);

        // Valid dates within range
        assertTrue(customValidator.eval("2020-01-01"));
        assertTrue(customValidator.eval("2021-06-15"));
        assertTrue(customValidator.eval("2023-12-31"));

        // Invalid dates outside range
        assertFalse(customValidator.eval("2019-12-31"));
        assertFalse(customValidator.eval("2024-01-01"));
    }

    @Test
    void customRange_WithOnlyMinDate_ShouldValidateCorrectly() {
        // Test with only a minimum date (no maximum)
        LocalDate minDate = LocalDate.of(2000, 1, 1);
        DateRangeValidator customValidator = new DateRangeValidator(minDate, null);

        // Valid dates after minimum
        assertTrue(customValidator.eval("2000-01-01"));
        assertTrue(customValidator.eval("2020-06-15"));
        assertTrue(customValidator.eval("2030-12-31")); // Future dates should be valid

        // Invalid dates before minimum
        assertFalse(customValidator.eval("1999-12-31"));
    }

    @Test
    void customRange_WithOnlyMaxDate_ShouldValidateCorrectly() {
        // Test with only a maximum date (no minimum)
        LocalDate maxDate = LocalDate.of(2020, 12, 31);
        DateRangeValidator customValidator = new DateRangeValidator(null, maxDate);

        // Valid dates before maximum
        assertTrue(customValidator.eval("1900-01-01")); // Very old dates should be valid
        assertTrue(customValidator.eval("2020-06-15"));
        assertTrue(customValidator.eval("2020-12-31"));

        // Invalid dates after maximum
        assertFalse(customValidator.eval("2021-01-01"));
    }

    @Test
    void customRange_WithNoBounds_ShouldOnlyValidateParseable() {
        // Test with no bounds (only validates parseability)
        DateRangeValidator customValidator = new DateRangeValidator();

        // Valid parseable dates (any date)
        assertTrue(customValidator.eval("1800-01-01"));
        assertTrue(customValidator.eval("2050-12-31"));
        assertTrue(customValidator.eval("1950-06-15"));

        // Invalid unparseable dates
        assertFalse(customValidator.eval("invalid-date"));
        assertFalse(customValidator.eval("2023-13-01"));
        assertFalse(customValidator.eval(null));
    }
}
