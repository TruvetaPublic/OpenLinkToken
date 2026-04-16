/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.general;

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

class DateAttributeTest {

    private DateAttribute dateAttribute;

    @BeforeEach
    void setUp() {
        dateAttribute = new DateAttribute();
    }

    @Test
    void getName_ShouldReturnDate() {
        assertEquals("Date", dateAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnDateAlias() {
        assertArrayEquals(new String[] { "Date" }, dateAttribute.getAliases());
    }

    @Test
    void normalize_ValidDateFormats_ShouldNormalizeToYYYYMMDD() {
        assertEquals("2023-10-26", dateAttribute.normalize("2023-10-26"));
        assertEquals("2023-10-26", dateAttribute.normalize("2023/10/26"));
        assertEquals("2023-10-26", dateAttribute.normalize("10/26/2023"));
        assertEquals("2023-10-26", dateAttribute.normalize("10-26-2023"));
        assertEquals("2023-10-26", dateAttribute.normalize("26.10.2023"));
    }

    @Test
    void normalize_ISO8601Timestamps_ShouldNormalizeToYYYYMMDD() {
        assertEquals("1972-08-18", dateAttribute.normalize("1972-08-18T00:00:00.000Z"));
        assertEquals("2023-10-26", dateAttribute.normalize("2023-10-26T12:34:56.789Z"));
        assertEquals("2023-10-26", dateAttribute.normalize("2023-10-26T12:34:56Z"));
        assertEquals("2023-10-26", dateAttribute.normalize("2023-10-26T12:34:56.789+05:30"));
        assertEquals("2023-10-26", dateAttribute.normalize("2023-10-26T12:34:56-08:00"));
    }

    @Test
    void normalize_InvalidDateFormat_ShouldThrowIllegalArgumentException() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            dateAttribute.normalize("20231026");
        });
        assertEquals("Invalid date format: 20231026", exception.getMessage());
    }

    @Test
    void validate_ValidDate_ShouldReturnTrue() {
        assertTrue(dateAttribute.validate("2023-10-26"));
        assertTrue(dateAttribute.validate("2023/10/26"));
        assertTrue(dateAttribute.validate("10/26/2023"));
        assertTrue(dateAttribute.validate("10-26-2023"));
        assertTrue(dateAttribute.validate("26.10.2023"));
    }

    @Test
    void validate_ISO8601Timestamps_ShouldReturnTrue() {
        assertTrue(dateAttribute.validate("1972-08-18T00:00:00.000Z"));
        assertTrue(dateAttribute.validate("2023-10-26T12:34:56.789Z"));
        assertTrue(dateAttribute.validate("2023-10-26T12:34:56Z"));
        assertTrue(dateAttribute.validate("2023-10-26T12:34:56.789+05:30"));
        assertTrue(dateAttribute.validate("2023-10-26T12:34:56-08:00"));
    }

    @Test
    void validate_InvalidDate_ShouldReturnFalse() {
        assertFalse(dateAttribute.validate("20231026"));
        assertFalse(dateAttribute.validate("invalid-date"));
        assertFalse(dateAttribute.validate("2023"));
        assertFalse(dateAttribute.validate(null));
        assertFalse(dateAttribute.validate(""));
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
                    String result = dateAttribute.normalize(testDate);
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

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(dateAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        DateAttribute deserializedAttribute = (DateAttribute) ois.readObject();
        ois.close();

        // Test various date values with both original and deserialized attributes
        String[] testValues = {
                "2023-10-26",
                "2023/10/26",
                "10/26/2023",
                "10-26-2023",
                "26.10.2023",
                "2000-01-01",
                "1990/12/31",
                "12/31/1999"
        };

        for (String value : testValues) {
            assertEquals(
                    dateAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    dateAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    dateAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    dateAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }

    @Test
    void normalize_FutureDates_ShouldNormalize() {
        // Unlike BirthDate, generic Date should allow future dates
        assertEquals("2030-12-31", dateAttribute.normalize("2030-12-31"));
        assertEquals("2050-01-01", dateAttribute.normalize("01/01/2050"));
    }

    @Test
    void normalize_HistoricalDates_ShouldNormalize() {
        // Generic Date should allow any historical dates
        assertEquals("1900-01-01", dateAttribute.normalize("1900-01-01"));
        assertEquals("1800-12-31", dateAttribute.normalize("12/31/1800"));
    }
}
