/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.general;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class RecordIdAttributeTest {

    private RecordIdAttribute recordIdAttribute;

    @BeforeEach
    void setUp() {
        recordIdAttribute = new RecordIdAttribute();
    }

    @Test
    void getName_ShouldReturnRecordId() {
        assertEquals("RecordId", recordIdAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnRecordIdAndId() {
        assertArrayEquals(new String[] { "RecordId", "Id" }, recordIdAttribute.getAliases());
    }

    @Test
    void normalize_ShouldTrimWhitespace() {
        assertEquals("test123", recordIdAttribute.normalize("test123"));
        assertEquals("test123", recordIdAttribute.normalize("  test123  "));
        assertEquals("ID-12345", recordIdAttribute.normalize("  ID-12345  "));
        assertEquals("record_001", recordIdAttribute.normalize("\t\nrecord_001\n\t"));
    }

    @Test
    void validate_ShouldNotAllowNullOrEmpty() {
        assertFalse(recordIdAttribute.validate(null), "Null value should not be allowed");
        assertFalse(recordIdAttribute.validate(""), "Empty value should not be allowed");
        assertTrue(recordIdAttribute.validate("test123"), "Non-empty value should be allowed");
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(recordIdAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        RecordIdAttribute deserializedAttribute = (RecordIdAttribute) ois.readObject();
        ois.close();

        // Test various record ID values with both original and deserialized attributes
        String[] testValues = {
                "test123",
                "  test123  ",
                "record_001",
                "ID-12345",
                "  user@domain.com  ",
                "a1b2c3d4",
                "RECORD123",
                "123abc"
        };

        for (String value : testValues) {
            assertEquals(
                    recordIdAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    recordIdAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    recordIdAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    recordIdAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
