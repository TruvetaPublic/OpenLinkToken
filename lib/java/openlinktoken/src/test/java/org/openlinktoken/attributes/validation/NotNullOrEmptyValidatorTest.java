/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;

import org.junit.jupiter.api.Test;

class NotNullOrEmptyValidatorTest {

    @Test
    void validTests() {
        var validator = new NotNullOrEmptyValidator();

        var result = validator.eval("test");
        assertTrue(result);

        result = validator.eval("123");
        assertTrue(result);

        result = validator.eval("  test  ");
        assertTrue(result);

        result = validator.eval("special!@#$");
        assertTrue(result);

        result = validator.eval("multi\nline");
        assertTrue(result);
    }

    @Test
    void invalidTests() {
        var validator = new NotNullOrEmptyValidator();

        var result = validator.eval(null);
        assertFalse(result, "Null value should not be allowed");
        result = validator.eval("");
        assertFalse(result, "Empty value should not be allowed");
        result = validator.eval(" ");
        assertFalse(result, "Blank value should not be allowed");
        result = validator.eval("\t");
        assertFalse(result, "Tab value should not be allowed");
        result = validator.eval("\n");
        assertFalse(result, "Newline value should not be allowed");
        result = validator.eval("\r");
        assertFalse(result, "Carriage return value should not be allowed");
    }

    @Test
    void serialization_ShouldPreserveState() throws Exception {
        // Test serialization and deserialization
        NotNullOrEmptyValidator originalValidator = new NotNullOrEmptyValidator();

        // Serialize the validator
        ByteArrayOutputStream byteOut = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(byteOut);
        out.writeObject(originalValidator);
        out.close();

        // Deserialize the validator
        ByteArrayInputStream byteIn = new ByteArrayInputStream(byteOut.toByteArray());
        ObjectInputStream in = new ObjectInputStream(byteIn);
        NotNullOrEmptyValidator deserializedValidator = (NotNullOrEmptyValidator) in.readObject();
        in.close();

        // Test that both validators behave the same way
        String[] testValues = { "valid", null, "", " ", "\t", "\n", "test123" };

        for (String value : testValues) {
            assertEquals(originalValidator.eval(value), deserializedValidator.eval(value),
                    "Validators should behave identically for value: " + value);
        }
    }
}
