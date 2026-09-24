/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import org.openlinktoken.attributes.general.StringAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;

/** Tests default field registration and custom field lookup. */
class FieldRegistryTest {

    /** Verifies the default registry contains the built-in field identifiers. */
    @Test
    void testCreateDefaultLoadsBuiltInAttributes() {
        var registry = FieldRegistry.createDefault();
        assertTrue(registry.size() > 0);
        assertTrue(registry.getFieldIds().contains("FirstName"));
        assertTrue(registry.getFieldIds().contains("LastName"));
        assertTrue(registry.getFieldIds().contains("String"));
    }

    /** Verifies lookup returns the registered attribute instance. */
    @Test
    void testGetAttributeReturnsRegisteredInstance() {
        var registry = FieldRegistry.createDefault();
        var attribute = registry.getAttribute("FirstName");
        assertTrue(attribute.isPresent());
        assertEquals("FirstName", attribute.get().getName());
    }

    /** Verifies an unknown field identifier has no registered attribute. */
    @Test
    void testGetAttributeReturnsEmptyForUnknownField() {
        var registry = FieldRegistry.createDefault();
        var attribute = registry.getAttribute("NonExistent");
        assertFalse(attribute.isPresent());
    }

    /** Verifies field lookup returns its identifier and attribute class. */
    @Test
    void testGetFieldReturnsAttributeField() {
        var registry = FieldRegistry.createDefault();
        var field = registry.getField("LastName");
        assertTrue(field.isPresent());
        assertEquals("LastName", field.get().getFieldId());
        assertEquals(LastNameAttribute.class, field.get().getAttributeClass());
    }

    /** Verifies the builder can register multiple custom fields for one attribute instance. */
    @Test
    void testBuilderRegistersCustomField() {
        var attribute = new StringAttribute();
        var registry = FieldRegistry.Builder.fromDefaults()
                .register("MotherLastName", StringAttribute.class, attribute)
                .register("FatherLastName", StringAttribute.class, attribute)
                .build();

        assertTrue(registry.getFieldIds().contains("MotherLastName"));
        assertTrue(registry.getFieldIds().contains("FatherLastName"));

        var motherAttr = registry.getAttribute("MotherLastName");
        var fatherAttr = registry.getAttribute("FatherLastName");
        assertTrue(motherAttr.isPresent());
        assertTrue(fatherAttr.isPresent());
        assertEquals(attribute, motherAttr.get());
        assertEquals(attribute, fatherAttr.get());
    }

    /** Verifies building from defaults preserves the built-in fields. */
    @Test
    void testBuilderFromDefaultsIncludesBuiltIns() {
        var registry = FieldRegistry.Builder.fromDefaults().build();
        assertTrue(registry.getFieldIds().contains("FirstName"));
        assertTrue(registry.getFieldIds().contains("LastName"));
    }

    /** Verifies multiple field identifiers can share one attribute type and instance. */
    @Test
    void testMultipleFieldsSameAttributeType() {
        var stringAttr = new StringAttribute();
        var registry = new FieldRegistry.Builder()
                .register("Field1", StringAttribute.class, stringAttr)
                .register("Field2", StringAttribute.class, stringAttr)
                .register("Field3", StringAttribute.class, stringAttr)
                .build();

        assertEquals(3, registry.size());

        var field1 = registry.getField("Field1");
        var field2 = registry.getField("Field2");
        var field3 = registry.getField("Field3");

        assertTrue(field1.isPresent());
        assertTrue(field2.isPresent());
        assertTrue(field3.isPresent());

        assertNotNull(registry.getAttribute("Field1").orElse(null));
        assertNotNull(registry.getAttribute("Field2").orElse(null));
        assertNotNull(registry.getAttribute("Field3").orElse(null));
    }
}
