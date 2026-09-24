/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Tests integer attribute naming, normalization, and validation. */
class IntegerAttributeTest {
    private IntegerAttribute attribute;

    /** Creates a fresh integer attribute for each test. */
    @BeforeEach
    void setUp() {
        attribute = new IntegerAttribute();
    }

    /** Verifies the attribute reports the {@code Integer} name. */
    @Test
    void testGetName_ShouldReturnInteger() {
        assertEquals("Integer", attribute.getName());
    }

    /** Verifies the integer attribute exposes its expected alias. */
    @Test
    void testGetAliases_ShouldReturnIntegerAlias() {
        String[] aliases = attribute.getAliases();
        assertEquals(1, aliases.length);
        assertEquals("Integer", aliases[0]);
    }

    /** Verifies valid signed and whitespace-padded integers normalize consistently. */
    @Test
    void testNormalize_ValidInteger_ShouldReturnNormalized() {
        assertEquals("123", attribute.normalize("123"));
        assertEquals("0", attribute.normalize("0"));
        assertEquals("-456", attribute.normalize("-456"));
        assertEquals("789", attribute.normalize("  789  "));
    }

    /** Verifies a leading positive sign is removed during normalization. */
    @Test
    void testNormalize_WithPositiveSign_ShouldNormalize() {
        assertEquals("123", attribute.normalize("+123"));
    }

    /** Verifies null input is rejected during normalization. */
    @Test
    void testNormalize_NullValue_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize(null));
    }

    /** Verifies non-integer and blank inputs are rejected during normalization. */
    @Test
    void testNormalize_InvalidInteger_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize("abc"));
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize("12.34"));
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize(""));
    }

    /** Verifies valid signed and whitespace-padded integers pass validation. */
    @Test
    void testValidate_ValidInteger_ShouldReturnTrue() {
        assertTrue(attribute.validate("123"));
        assertTrue(attribute.validate("0"));
        assertTrue(attribute.validate("-456"));
        assertTrue(attribute.validate("  789  "));
        assertTrue(attribute.validate("+123"));
    }

    /** Verifies null, blank, decimal, and nonnumeric inputs fail validation. */
    @Test
    void testValidate_InvalidInteger_ShouldReturnFalse() {
        assertFalse(attribute.validate(null));
        assertFalse(attribute.validate(""));
        assertFalse(attribute.validate("abc"));
        assertFalse(attribute.validate("12.34"));
        assertFalse(attribute.validate("1.0e10"));
    }

    /** Verifies integer boundary values are accepted by validation. */
    @Test
    void testValidate_BoundaryValues_ShouldReturnTrue() {
        assertTrue(attribute.validate("0"));
        assertTrue(attribute.validate("-2147483648")); // Min int
        assertTrue(attribute.validate("2147483647")); // Max int
        assertTrue(attribute.validate("9223372036854775807")); // Max long
    }

}
