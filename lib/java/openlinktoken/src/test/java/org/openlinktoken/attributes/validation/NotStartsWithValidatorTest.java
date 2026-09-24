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

/** Tests prefix exclusion, edge cases, and serialization for {@link NotStartsWithValidator}. */
class NotStartsWithValidatorTest {

    /** Verifies a null value is rejected. */
    @Test
    void testNullValue() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton("invalid"));
        assertFalse(validator.eval(null), "Null value should not be allowed");
    }

    /** Verifies an empty invalid-prefix set allows an ordinary value. */
    @Test
    void testEmptyInvalidPrefixes() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.emptySet());
        assertTrue(validator.eval("anyvalue"), "Empty prefix sets should allow any value");
    }

    /** Verifies values without a forbidden prefix are accepted. */
    @Test
    void testValueNotStartingWithInvalidPrefix() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton("bad"));
        assertTrue(validator.eval("goodvalue"), "Values not starting with invalid prefixes should be allowed");
    }

    /** Verifies values beginning with a forbidden prefix are rejected. */
    @Test
    void testValueStartingWithInvalidPrefix() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton("bad"));
        assertFalse(validator.eval("badvalue"), "Values starting with invalid prefixes should not be allowed");
    }

    /** Verifies an exact match to a forbidden prefix is rejected. */
    @Test
    void testExactMatch() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton("bad"));
        assertFalse(validator.eval("bad"), "Values that exactly match invalid prefixes should not be allowed");
    }

    /** Verifies each configured invalid prefix is rejected independently. */
    @Test
    void testMultipleInvalidPrefixes() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Set.of("bad", "evil", "wrong"));
        assertTrue(validator.eval("goodvalue"), "Valid values should be allowed");
        assertFalse(validator.eval("badvalue"), "Values starting with 'bad' should not be allowed");
        assertFalse(validator.eval("evilplan"), "Values starting with 'evil' should not be allowed");
        assertFalse(validator.eval("wrongway"), "Values starting with 'wrong' should not be allowed");
        assertTrue(validator.eval("rightway"), "Values not starting with any invalid prefix should be allowed");
    }

    /** Verifies prefix comparisons are case-sensitive. */
    @Test
    void testCaseSensitive() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton("Bad"));
        assertTrue(validator.eval("badvalue"), "Validation should be case-sensitive");
        assertFalse(validator.eval("Badvalue"), "Values starting with exact case match should not be allowed");
    }

    /** Verifies an empty value is accepted when no forbidden prefix matches it. */
    @Test
    void testEmptyStringValue() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton("bad"));
        assertTrue(validator.eval(""), "Empty string should be allowed if it doesn't start with invalid prefix");
    }

    /** Verifies an empty forbidden prefix rejects every value, including an empty one. */
    @Test
    void testEmptyStringPrefix() {
        NotStartsWithValidator validator = new NotStartsWithValidator(Collections.singleton(""));
        assertFalse(validator.eval("anyvalue"), "Any value should be invalid if empty string is an invalid prefix");
        assertFalse(validator.eval(""), "Empty string should be invalid if empty string is an invalid prefix");
    }

    /** Verifies serialization preserves forbidden prefixes and validation behavior. */
    @Test
    void testSerialization() throws Exception {
        NotStartsWithValidator validator = new NotStartsWithValidator(Set.of("bad", "evil"));
        ByteArrayOutputStream byteOut = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(byteOut);
        out.writeObject(validator);

        ByteArrayInputStream byteIn = new ByteArrayInputStream(byteOut.toByteArray());
        ObjectInputStream in = new ObjectInputStream(byteIn);
        NotStartsWithValidator deserializedValidator = (NotStartsWithValidator) in.readObject();

        // Test that both validators behave the same way
        String[] testValues = { "goodvalue", "badvalue", "evilplan", "rightway", "", null };

        for (String value : testValues) {
            assertEquals(validator.eval(value), deserializedValidator.eval(value),
                    "Validators should behave identically for value: " + value);
        }

        // Additional specific tests on deserialized validator
        assertTrue(deserializedValidator.eval("goodvalue"));
        assertFalse(deserializedValidator.eval("badvalue"));
        assertFalse(deserializedValidator.eval("evilplan"));
    }
}
