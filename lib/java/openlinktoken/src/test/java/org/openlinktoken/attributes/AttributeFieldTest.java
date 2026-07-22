/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

import org.openlinktoken.attributes.general.StringAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;

class AttributeFieldTest {

    @Test
    void testConstructor() {
        var field = new AttributeField("LastName", LastNameAttribute.class);
        assertEquals("LastName", field.getFieldId());
        assertEquals(LastNameAttribute.class, field.getAttributeClass());
    }

    @Test
    void testConstructorRejectsNullFieldId() {
        assertThrows(NullPointerException.class, () -> new AttributeField(null, StringAttribute.class));
    }

    @Test
    void testConstructorRejectsNullAttributeClass() {
        assertThrows(NullPointerException.class, () -> new AttributeField("Test", null));
    }

    @Test
    void testEqualityByFieldId() {
        var field1 = new AttributeField("Name", StringAttribute.class);
        var field2 = new AttributeField("Name", FirstNameAttribute.class);
        assertEquals(field1, field2);
        assertEquals(field1.hashCode(), field2.hashCode());
    }

    @Test
    void testInequalityByFieldId() {
        var field1 = new AttributeField("FirstName", StringAttribute.class);
        var field2 = new AttributeField("LastName", StringAttribute.class);
        assertNotEquals(field1, field2);
    }

    @Test
    void testToString() {
        var field = new AttributeField("BirthDate", StringAttribute.class);
        var str = field.toString();
        assertEquals("AttributeField{fieldId='BirthDate', attributeClass=StringAttribute}", str);
    }
}
