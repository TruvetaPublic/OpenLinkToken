/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class AgeAttributeTest {

    private AgeAttribute ageAttribute;

    @BeforeEach
    void setUp() {
        ageAttribute = new AgeAttribute();
    }

    @Test
    void getName_ShouldReturnAge() {
        assertEquals("Age", ageAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnAgeAlias() {
        assertArrayEquals(new String[] { "Age" }, ageAttribute.getAliases());
    }

    @Test
    void normalize_ValidAge_ShouldNormalizeToInteger() {
        assertEquals("25", ageAttribute.normalize("25"));
        assertEquals("0", ageAttribute.normalize("0"));
        assertEquals("120", ageAttribute.normalize("120"));
        assertEquals("42", ageAttribute.normalize("  42  "));
        assertEquals("100", ageAttribute.normalize("100"));
    }

    @Test
    void normalize_InvalidAgeFormat_ShouldThrowIllegalArgumentException() {
        assertThrows(IllegalArgumentException.class, () -> {
            ageAttribute.normalize("25.5");
        });
        assertThrows(IllegalArgumentException.class, () -> {
            ageAttribute.normalize("abc");
        });
        assertThrows(IllegalArgumentException.class, () -> {
            ageAttribute.normalize("");
        });
        assertThrows(IllegalArgumentException.class, () -> {
            ageAttribute.normalize(null);
        });
    }

    @Test
    void validate_ValidAge_ShouldReturnTrue() {
        assertTrue(ageAttribute.validate("0"));
        assertTrue(ageAttribute.validate("25"));
        assertTrue(ageAttribute.validate("120"));
        assertTrue(ageAttribute.validate("100"));
        assertTrue(ageAttribute.validate("  50  "));
    }

    @Test
    void validate_InvalidAge_ShouldReturnFalse() {
        // Out of range
        assertFalse(ageAttribute.validate("-1"));
        assertFalse(ageAttribute.validate("121"));
        assertFalse(ageAttribute.validate("200"));

        // Invalid format
        assertFalse(ageAttribute.validate("25.5"));
        assertFalse(ageAttribute.validate("abc"));
        assertFalse(ageAttribute.validate("25a"));
        assertFalse(ageAttribute.validate(""));
        assertFalse(ageAttribute.validate(null));
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testAge = "  42  ";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = ageAttribute.normalize(testAge);
                    results.add(result);

                    finishLatch.countDown();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
            thread.start();
        }

        startLatch.countDown(); // Start all threads
        finishLatch.await(15, TimeUnit.SECONDS); // Wait for all threads to complete

        // Verify all threads got the same result
        assertEquals(threadCount, results.size());
        for (String result : results) {
            assertEquals("42", result);
        }
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(ageAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        AgeAttribute deserializedAttribute = (AgeAttribute) ois.readObject();
        ois.close();

        // Test various age values with both original and deserialized attributes
        String[] testValues = {
                "0",
                "25",
                "50",
                "100",
                "120",
                "  42  ",
                "65"
        };

        for (String value : testValues) {
            assertEquals(
                    ageAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    ageAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    ageAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    ageAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }

    @Test
    void validate_BoundaryValues_ShouldValidateCorrectly() {
        // Lower boundary
        assertTrue(ageAttribute.validate("0"));
        assertFalse(ageAttribute.validate("-1"));

        // Upper boundary
        assertTrue(ageAttribute.validate("120"));
        assertFalse(ageAttribute.validate("121"));
    }
}
