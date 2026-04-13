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
import java.time.Year;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class BirthYearAttributeTest {

    private BirthYearAttribute birthYearAttribute;

    @BeforeEach
    void setUp() {
        birthYearAttribute = new BirthYearAttribute();
    }

    @Test
    void getName_ShouldReturnBirthYear() {
        assertEquals("BirthYear", birthYearAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnBirthYearAndYearOfBirthAliases() {
        assertArrayEquals(new String[] { "BirthYear", "YearOfBirth" }, birthYearAttribute.getAliases());
    }

    @Test
    void normalize_ValidYear_ShouldNormalizeToInteger() {
        assertEquals("1990", birthYearAttribute.normalize("1990"));
        assertEquals("2000", birthYearAttribute.normalize("2000"));
        assertEquals("1950", birthYearAttribute.normalize("  1950  "));
        assertEquals("2020", birthYearAttribute.normalize("2020"));
    }

    @Test
    void normalize_InvalidYearFormat_ShouldThrowIllegalArgumentException() {
        assertThrows(IllegalArgumentException.class, () -> {
            birthYearAttribute.normalize("90");
        });
        assertThrows(IllegalArgumentException.class, () -> {
            birthYearAttribute.normalize("abc");
        });
        assertThrows(IllegalArgumentException.class, () -> {
            birthYearAttribute.normalize("");
        });
        assertThrows(IllegalArgumentException.class, () -> {
            birthYearAttribute.normalize(null);
        });
    }

    @Test
    void validate_ValidYear_ShouldReturnTrue() {
        assertTrue(birthYearAttribute.validate("1910"));
        assertTrue(birthYearAttribute.validate("1990"));
        assertTrue(birthYearAttribute.validate("2000"));
        assertTrue(birthYearAttribute.validate(String.valueOf(Year.now().getValue())));
        assertTrue(birthYearAttribute.validate("  1980  "));
    }

    @Test
    void validate_InvalidYear_ShouldReturnFalse() {
        // Out of range
        assertFalse(birthYearAttribute.validate("1899"));
        assertFalse(birthYearAttribute.validate(String.valueOf(Year.now().getValue() + 1)));
        assertFalse(birthYearAttribute.validate("2100"));

        // Invalid format
        assertFalse(birthYearAttribute.validate("90"));
        assertFalse(birthYearAttribute.validate("abc"));
        assertFalse(birthYearAttribute.validate("19a0"));
        assertFalse(birthYearAttribute.validate(""));
        assertFalse(birthYearAttribute.validate(null));
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testYear = "  1990  ";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = birthYearAttribute.normalize(testYear);
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
            assertEquals("1990", result);
        }
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(birthYearAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        BirthYearAttribute deserializedAttribute = (BirthYearAttribute) ois.readObject();
        ois.close();

        // Test various year values with both original and deserialized attributes
        String[] testValues = {
                "1910",
                "1950",
                "1990",
                "2000",
                "2020",
                "  1980  "
        };

        for (String value : testValues) {
            assertEquals(
                    birthYearAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    birthYearAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    birthYearAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    birthYearAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }

    @Test
    void validate_BoundaryValues_ShouldValidateCorrectly() {
        int currentYear = Year.now().getValue();

        // Lower boundary
        assertTrue(birthYearAttribute.validate("1910"));
        assertFalse(birthYearAttribute.validate("1909"));

        // Upper boundary (current year)
        assertTrue(birthYearAttribute.validate(String.valueOf(currentYear)));
        assertFalse(birthYearAttribute.validate(String.valueOf(currentYear + 1)));
    }
}
