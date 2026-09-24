/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

import org.openlinktoken.attributes.general.StringAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;

/** Tests construction, equality, and representation of attribute-field descriptors. */
class AttributeFieldTest {

    /** Verifies construction retains the field identifier and attribute class. */
    @Test
    void testConstructor() {
        var field = new AttributeField("LastName", LastNameAttribute.class);
        assertEquals("LastName", field.getFieldId());
        assertEquals(LastNameAttribute.class, field.getAttributeClass());
    }

    /** Verifies construction rejects a null field identifier. */
    @Test
    void testConstructorRejectsNullFieldId() {
        assertThrows(NullPointerException.class, () -> new AttributeField(null, StringAttribute.class));
    }

    /** Verifies construction rejects a null attribute class. */
    @Test
    void testConstructorRejectsNullAttributeClass() {
        assertThrows(NullPointerException.class, () -> new AttributeField("Test", null));
    }

    /** Verifies field equality and hash codes depend on the field identifier. */
    @Test
    void testEqualityByFieldId() {
        var field1 = new AttributeField("Name", StringAttribute.class);
        var field2 = new AttributeField("Name", FirstNameAttribute.class);
        assertEquals(field1, field2);
        assertEquals(field1.hashCode(), field2.hashCode());
    }

    /** Verifies fields with different identifiers are unequal. */
    @Test
    void testInequalityByFieldId() {
        var field1 = new AttributeField("FirstName", StringAttribute.class);
        var field2 = new AttributeField("LastName", StringAttribute.class);
        assertNotEquals(field1, field2);
    }

    /** Verifies the descriptor's string representation includes its identifier and class name. */
    @Test
    void testToString() {
        var field = new AttributeField("BirthDate", StringAttribute.class);
        var str = field.toString();
        assertEquals("AttributeField{fieldId='BirthDate', attributeClass=StringAttribute}", str);
    }
}
