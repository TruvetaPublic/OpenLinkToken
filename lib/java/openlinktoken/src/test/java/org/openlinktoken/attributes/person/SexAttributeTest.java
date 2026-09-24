/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.person;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
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

class SexAttributeTest {
    private SexAttribute sexAttribute;

    @BeforeEach
    void setUp() {
        sexAttribute = new SexAttribute();
    }

    @Test
    void getName_ShouldReturnSex() {
        assertEquals("Sex", sexAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnSexAndGender() {
        String[] expectedAliases = { "Sex", "Gender" };
        assertArrayEquals(expectedAliases, sexAttribute.getAliases());
    }

    @Test
    void normalize_ShouldReturnMaleForMInput() {
        assertEquals("Male", sexAttribute.normalize("M"));
        assertEquals("Male", sexAttribute.normalize("Male"));
        assertEquals("Male", sexAttribute.normalize("m"));
        assertEquals("Male", sexAttribute.normalize("male"));
    }

    @Test
    void normalize_ShouldReturnFemaleForFInput() {
        assertEquals("Female", sexAttribute.normalize("F"));
        assertEquals("Female", sexAttribute.normalize("Female"));
        assertEquals("Female", sexAttribute.normalize("f"));
        assertEquals("Female", sexAttribute.normalize("female"));
    }

    @Test
    void normalize_ShouldReturnNullForInvalidInput() {
        assertNull(sexAttribute.normalize("X"), "Invalid value should return null");
        assertNull(sexAttribute.normalize("Other"), "Invalid value should return null");
    }

    @Test
    void validate_ShouldReturnTrueForValidValues() {
        assertTrue(sexAttribute.validate("M"));
        assertTrue(sexAttribute.validate("F"));
        assertTrue(sexAttribute.validate("Male"));
        assertTrue(sexAttribute.validate("Female"));
    }

    @Test
    void validate_ShouldReturnFalseForInvalidValues() {
        assertFalse(sexAttribute.validate("X"), "Invalid value should not be allowed");
        assertFalse(sexAttribute.validate("Other"), "Invalid value should not be allowed");
        assertFalse(sexAttribute.validate(""), "Empty value should not be allowed");
        assertFalse(sexAttribute.validate(null), "Null value should not be allowed");
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testSex = "m";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = sexAttribute.normalize(testSex);
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
            assertEquals("Male", result);
        }
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(sexAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        SexAttribute deserializedAttribute = (SexAttribute) ois.readObject();
        ois.close();

        // Test various sex values with both original and deserialized attributes
        String[] testValues = {
                "M",
                "Male",
                "m",
                "male",
                "F",
                "Female",
                "f",
                "female",
                "U",
                "Unknown",
                "u",
                "unknown"
        };

        for (String value : testValues) {
            assertEquals(
                    sexAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    sexAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    sexAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    sexAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
