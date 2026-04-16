/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;

import org.junit.jupiter.api.Test;

class RegexValidatorTest {

    @Test
    void eval_ShouldReturnTrueForMatchingPattern() {
        RegexValidator validator = new RegexValidator("^[A-Z]+$");
        assertTrue(validator.eval("ABC"), "All uppercase letters should match");
    }

    @Test
    void eval_ShouldReturnFalseForNonMatchingPattern() {
        RegexValidator validator = new RegexValidator("^[A-Z]+$");
        assertFalse(validator.eval("abc"), "Lowercase letters should not match");
        assertFalse(validator.eval("123"), "Numbers should not match");
    }

    @Test
    void eval_ShouldReturnFalseForNullValue() {
        RegexValidator validator = new RegexValidator(".*");
        assertFalse(validator.eval(null), "Null value should not match");
    }

    @Test
    void eval_ShouldReturnTrueForEmptyStringWithMatchingPattern() {
        RegexValidator validator = new RegexValidator("^$");
        assertTrue(validator.eval(""), "Empty string should match");
    }

    @Test
    void eval_ShouldReturnTrueForComplexPattern() {
        RegexValidator validator = new RegexValidator("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,6}$");
        assertTrue(validator.eval("test@email.com"), "Valid email should match");
        assertFalse(validator.eval("invalid-email"), "Invalid email should not match");
    }

    @Test
    void constructor_ShouldCompilePattern() {
        RegexValidator validator = new RegexValidator("test");
        assertNotNull(validator.getCompiledPattern(), "Pattern should be compiled");
        assertEquals("test", validator.getCompiledPattern().pattern(), "Pattern should be the same as input");
    }

    @Test
    void serialization_ShouldPreserveState() throws Exception {
        RegexValidator originalValidator = new RegexValidator("^[A-Z]+$");
        ByteArrayOutputStream byteOut = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(byteOut);
        out.writeObject(originalValidator);

        ByteArrayInputStream byteIn = new ByteArrayInputStream(byteOut.toByteArray());
        ObjectInputStream in = new ObjectInputStream(byteIn);
        RegexValidator deserializedValidator = (RegexValidator) in.readObject();

        assertEquals(originalValidator.getCompiledPattern().pattern(),
                deserializedValidator.getCompiledPattern().pattern(), "Compiled patterns should match");
    }
}
