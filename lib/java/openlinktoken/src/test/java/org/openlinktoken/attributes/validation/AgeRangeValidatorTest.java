/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class AgeRangeValidatorTest {

    private AgeRangeValidator validator;

    @BeforeEach
    void setUp() {
        validator = new AgeRangeValidator();
    }

    @Test
    void eval_ValidAges_ShouldReturnTrue() {
        assertTrue(validator.eval("0"), "Age 0 should be valid");
        assertTrue(validator.eval("25"), "Age 25 should be valid");
        assertTrue(validator.eval("120"), "Age 120 should be valid");
        assertTrue(validator.eval("100"), "Age 100 should be valid");
        assertTrue(validator.eval("  42  "), "Age with whitespace should be valid");
    }

    @Test
    void eval_InvalidAges_ShouldReturnFalse() {
        // Out of range
        assertFalse(validator.eval("-1"), "Negative age should be invalid");
        assertFalse(validator.eval("121"), "Age 121 should be invalid");
        assertFalse(validator.eval("200"), "Age 200 should be invalid");
        assertFalse(validator.eval("1000"), "Age 1000 should be invalid");

        // Invalid format
        assertFalse(validator.eval("25.5"), "Decimal age should be invalid");
        assertFalse(validator.eval("abc"), "Non-numeric age should be invalid");
        assertFalse(validator.eval("25a"), "Age with letters should be invalid");
        assertFalse(validator.eval(""), "Empty string should be invalid");
        assertFalse(validator.eval(null), "Null should be invalid");
        assertFalse(validator.eval("   "), "Whitespace only should be invalid");
    }

    @Test
    void eval_BoundaryValues_ShouldValidateCorrectly() {
        // Lower boundary
        assertTrue(validator.eval("0"), "Lower boundary (0) should be valid");
        assertFalse(validator.eval("-1"), "Below lower boundary (-1) should be invalid");

        // Upper boundary
        assertTrue(validator.eval("120"), "Upper boundary (120) should be valid");
        assertFalse(validator.eval("121"), "Above upper boundary (121) should be invalid");
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
        AgeRangeValidator deserializedValidator = (AgeRangeValidator) in.readObject();
        in.close();

        // Test that both validators work the same
        String[] testValues = {
                "0", "25", "120", "-1", "121", "abc", ""
        };

        for (String value : testValues) {
            assertEquals(
                    validator.eval(value),
                    deserializedValidator.eval(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
