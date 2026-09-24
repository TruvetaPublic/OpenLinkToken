/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class IntegerAttributeTest {
    private IntegerAttribute attribute;

    @BeforeEach
    void setUp() {
        attribute = new IntegerAttribute();
    }

    @Test
    void testGetName_ShouldReturnInteger() {
        assertEquals("Integer", attribute.getName());
    }

    @Test
    void testGetAliases_ShouldReturnIntegerAlias() {
        String[] aliases = attribute.getAliases();
        assertEquals(1, aliases.length);
        assertEquals("Integer", aliases[0]);
    }

    @Test
    void testNormalize_ValidInteger_ShouldReturnNormalized() {
        assertEquals("123", attribute.normalize("123"));
        assertEquals("0", attribute.normalize("0"));
        assertEquals("-456", attribute.normalize("-456"));
        assertEquals("789", attribute.normalize("  789  "));
    }

    @Test
    void testNormalize_WithPositiveSign_ShouldNormalize() {
        assertEquals("123", attribute.normalize("+123"));
    }

    @Test
    void testNormalize_NullValue_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize(null));
    }

    @Test
    void testNormalize_InvalidInteger_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize("abc"));
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize("12.34"));
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize(""));
    }

    @Test
    void testValidate_ValidInteger_ShouldReturnTrue() {
        assertTrue(attribute.validate("123"));
        assertTrue(attribute.validate("0"));
        assertTrue(attribute.validate("-456"));
        assertTrue(attribute.validate("  789  "));
        assertTrue(attribute.validate("+123"));
    }

    @Test
    void testValidate_InvalidInteger_ShouldReturnFalse() {
        assertFalse(attribute.validate(null));
        assertFalse(attribute.validate(""));
        assertFalse(attribute.validate("abc"));
        assertFalse(attribute.validate("12.34"));
        assertFalse(attribute.validate("1.0e10"));
    }

    @Test
    void testValidate_BoundaryValues_ShouldReturnTrue() {
        assertTrue(attribute.validate("0"));
        assertTrue(attribute.validate("-2147483648")); // Min int
        assertTrue(attribute.validate("2147483647")); // Max int
        assertTrue(attribute.validate("9223372036854775807")); // Max long
    }

}
