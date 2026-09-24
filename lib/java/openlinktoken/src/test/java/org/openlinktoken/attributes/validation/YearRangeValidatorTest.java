/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.time.Year;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class YearRangeValidatorTest {

    private YearRangeValidator validator;

    @BeforeEach
    void setUp() {
        validator = new YearRangeValidator();
    }

    @Test
    void eval_ValidYears_ShouldReturnTrue() {
        int currentYear = Year.now().getValue();

        assertTrue(validator.eval("1910"), "Year 1910 should be valid");
        assertTrue(validator.eval("1950"), "Year 1950 should be valid");
        assertTrue(validator.eval("1990"), "Year 1990 should be valid");
        assertTrue(validator.eval("2000"), "Year 2000 should be valid");
        assertTrue(validator.eval(String.valueOf(currentYear)), "Current year should be valid");
        assertTrue(validator.eval("  1980  "), "Year with whitespace should be valid");
    }

    @Test
    void eval_InvalidYears_ShouldReturnFalse() {
        int currentYear = Year.now().getValue();

        // Out of range
        assertFalse(validator.eval("1909"), "Year 1909 should be invalid");
        assertFalse(validator.eval(String.valueOf(currentYear + 1)), "Future year should be invalid");
        assertFalse(validator.eval("2100"), "Far future year should be invalid");
        assertFalse(validator.eval("1900"), "Year before 1910 should be invalid");

        // Invalid format
        assertFalse(validator.eval("90"), "2-digit year should be invalid");
        assertFalse(validator.eval("abc"), "Non-numeric year should be invalid");
        assertFalse(validator.eval("19a0"), "Year with letters should be invalid");
        assertFalse(validator.eval(""), "Empty string should be invalid");
        assertFalse(validator.eval(null), "Null should be invalid");
        assertFalse(validator.eval("   "), "Whitespace only should be invalid");
    }

    @Test
    void eval_BoundaryValues_ShouldValidateCorrectly() {
        int currentYear = Year.now().getValue();

        // Lower boundary
        assertTrue(validator.eval("1910"), "Lower boundary (1910) should be valid");
        assertFalse(validator.eval("1909"), "Below lower boundary (1909) should be invalid");

        // Upper boundary (current year)
        assertTrue(validator.eval(String.valueOf(currentYear)), "Upper boundary (current year) should be valid");
        assertFalse(validator.eval(String.valueOf(currentYear + 1)), "Above upper boundary should be invalid");
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the validator
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(baos);
        out.writeObject(validator);
        out.close();

        // Deserialize the validator
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream in = new ObjectInputStream(bais);
        YearRangeValidator deserializedValidator = (YearRangeValidator) in.readObject();
        in.close();

        // Test that both validators work the same
        String[] testValues = {
                "1910", "1990", "2000", "1909", String.valueOf(Year.now().getValue() + 1), "abc", ""
        };

        for (String value : testValues) {
            assertEquals(
                    validator.eval(value),
                    deserializedValidator.eval(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
