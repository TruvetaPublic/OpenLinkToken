/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.Collections;
import java.util.Set;

import org.junit.jupiter.api.Test;

class NotInValidatorTest {

    @Test
    void testNullValue() {
        NotInValidator validator = new NotInValidator(Collections.singleton("invalid"));
        assertFalse(validator.eval(null), "Null value should not be allowed");
    }

    @Test
    void testEmptyInvalidValues() {
        NotInValidator validator = new NotInValidator(Collections.emptySet());
        assertTrue(validator.eval("value"), "Empty sets should allow any value");
    }

    @Test
    void testValueNotInInvalidList() {
        NotInValidator validator = new NotInValidator(Collections.singleton("invalid"));
        assertTrue(validator.eval("valid"), "Values not in the invalid list should be allowed");
    }

    @Test
    void testValueInInvalidList() {
        NotInValidator validator = new NotInValidator(Collections.singleton("invalid"));
        assertFalse(validator.eval("invalid"), "Values in the invalid list should not be allowed");
    }

    @Test
    void testMultipleInvalidValues() {
        NotInValidator validator = new NotInValidator(Set.of("invalid1", "invalid2", "invalid3"));
        assertTrue(validator.eval("valid"));
        assertFalse(validator.eval("invalid1"));
        assertFalse(validator.eval("invalid2"));
        assertFalse(validator.eval("invalid3"));
    }

    @Test
    void testSerialization() throws Exception {
        NotInValidator validator = new NotInValidator(Set.of("invalid1", "invalid2"));
        ByteArrayOutputStream byteOut = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(byteOut);
        out.writeObject(validator);

        ByteArrayInputStream byteIn = new ByteArrayInputStream(byteOut.toByteArray());
        ObjectInputStream in = new ObjectInputStream(byteIn);
        NotInValidator deserializedValidator = (NotInValidator) in.readObject();

        assertEquals(validator.eval("valid"), deserializedValidator.eval("valid"));
        assertFalse(deserializedValidator.eval("invalid1"));
        assertFalse(deserializedValidator.eval("invalid2"));
    }
}
