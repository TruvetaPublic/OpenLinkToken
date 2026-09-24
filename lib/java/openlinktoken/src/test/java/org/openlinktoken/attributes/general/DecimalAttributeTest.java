/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class DecimalAttributeTest {
    private DecimalAttribute attribute;

    @BeforeEach
    void setUp() {
        attribute = new DecimalAttribute();
    }

    @Test
    void testGetName_ShouldReturnDecimal() {
        assertEquals("Decimal", attribute.getName());
    }

    @Test
    void testGetAliases_ShouldReturnDecimalAlias() {
        String[] aliases = attribute.getAliases();
        assertEquals(1, aliases.length);
        assertEquals("Decimal", aliases[0]);
    }

    @Test
    void testNormalize_ValidDecimal_ShouldReturnNormalized() {
        assertEquals("123.45", attribute.normalize("123.45"));
        assertEquals("0.0", attribute.normalize("0"));
        assertEquals("-456.78", attribute.normalize("-456.78"));
        assertEquals("789.0", attribute.normalize("  789  "));
        assertEquals("0.5", attribute.normalize(".5"));
        assertEquals("1.0", attribute.normalize("1."));
    }

    @Test
    void testNormalize_WithPositiveSign_ShouldNormalize() {
        assertEquals("123.45", attribute.normalize("+123.45"));
    }

    @Test
    void testNormalize_ScientificNotation_ShouldNormalize() {
        String result = attribute.normalize("1.5e10");
        assertEquals("1.5E10", result);

        result = attribute.normalize("-3.14E-2");
        assertEquals("-0.0314", result);
    }

    @Test
    void testNormalize_NullValue_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize(null));
    }

    @Test
    void testNormalize_InvalidDecimal_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize("abc"));
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize(""));
        assertThrows(IllegalArgumentException.class, () -> attribute.normalize("   "));
    }

    @Test
    void testValidate_ValidDecimal_ShouldReturnTrue() {
        assertTrue(attribute.validate("123.45"));
        assertTrue(attribute.validate("0"));
        assertTrue(attribute.validate("-456.78"));
        assertTrue(attribute.validate("  789  "));
        assertTrue(attribute.validate("+123.45"));
        assertTrue(attribute.validate(".5"));
        assertTrue(attribute.validate("1."));
        assertTrue(attribute.validate("1.5e10"));
        assertTrue(attribute.validate("-3.14E-2"));
    }

    @Test
    void testValidate_InvalidDecimal_ShouldReturnFalse() {
        assertFalse(attribute.validate(null));
        assertFalse(attribute.validate(""));
        assertFalse(attribute.validate("abc"));
        assertFalse(attribute.validate("1.2.3"));
    }

    @Test
    void testValidate_BoundaryValues_ShouldReturnTrue() {
        assertTrue(attribute.validate("0.0"));
        assertTrue(attribute.validate("3.14159265358979"));
        assertTrue(attribute.validate("1.0E308")); // Near max double
        assertTrue(attribute.validate("1.0E-308")); // Near min positive double
    }

}
