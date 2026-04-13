/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
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

class BirthDateAttributeTest {

    private BirthDateAttribute birthDateAttribute;

    @BeforeEach
    void setUp() {
        birthDateAttribute = new BirthDateAttribute();
    }

    @Test
    void getName_ShouldReturnBirthDate() {
        assertEquals("BirthDate", birthDateAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnBirthDateAndDateOfBirthAliases() {
        assertArrayEquals(new String[] { "BirthDate", "DateOfBirth" }, birthDateAttribute.getAliases());
    }

    @Test
    void normalize_ValidDateFormats_ShouldNormalizeToYYYYMMDD() {
        assertEquals("2023-10-26", birthDateAttribute.normalize("2023-10-26"));
        assertEquals("2023-10-26", birthDateAttribute.normalize("2023/10/26"));
        assertEquals("2023-10-26", birthDateAttribute.normalize("10/26/2023"));
        assertEquals("2023-10-26", birthDateAttribute.normalize("10-26-2023"));
        assertEquals("2023-10-26", birthDateAttribute.normalize("26.10.2023"));
    }

    @Test
    void normalize_InvalidDateFormat_ShouldThrowIllegalArgumentException() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            birthDateAttribute.normalize("20231026");
        });
        assertEquals("Invalid date format: 20231026", exception.getMessage());
    }

    @Test
    void validate_ValidDate_ShouldReturnTrue() {
        assertTrue(birthDateAttribute.validate("2023-10-26"));
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testDate = "10/26/2023";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = birthDateAttribute.normalize(testDate);
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
            assertEquals("2023-10-26", result);
        }
    }

    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(birthDateAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        BirthDateAttribute deserializedAttribute = (BirthDateAttribute) ois.readObject();
        ois.close();

        // Test various date formats with both original and deserialized attributes
        String[] testValues = {
                "2023-10-26",
                "2023/10/26",
                "10/26/2023",
                "10-26-2023",
                "26.10.2023",
                "1990-01-01",
                "12/31/1999",
                "01-01-2000"
        };

        for (String value : testValues) {
            assertEquals(
                    birthDateAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    birthDateAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    birthDateAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    birthDateAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
