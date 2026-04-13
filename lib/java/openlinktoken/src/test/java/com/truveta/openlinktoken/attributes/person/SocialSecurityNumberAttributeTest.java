/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

class SocialSecurityNumberAttributeTest {
    private SocialSecurityNumberAttribute ssnAttribute;

    @BeforeEach
    void setUp() {
        ssnAttribute = new SocialSecurityNumberAttribute();
    }

    @Test
    void getName_ShouldReturnSocialSecurityNumber() {
        assertEquals("SocialSecurityNumber", ssnAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnSocialSecurityNumberAndNationalIdentificationNumber() {
        String[] expectedAliases = { "SocialSecurityNumber", "NationalIdentificationNumber" };
        assertArrayEquals(expectedAliases, ssnAttribute.getAliases());
    }

    @Test
    void normalize_ShouldFormatWithDashes() {
        assertEquals("123-45-6789", ssnAttribute.normalize("123456789"), "Should format without dashes");
        assertEquals("123-45-6789", ssnAttribute.normalize("123-45-6789"), "Should format with dashes");
        assertEquals("123-45-6789", ssnAttribute.normalize("123456789.0"), "Should format with decimal point");
        assertEquals("001-23-4567", ssnAttribute.normalize("1234567"), "Should format with leading zeros");
        assertEquals("001-23-4567", ssnAttribute.normalize("1234567.0"),
                "Should format with leading zeros and decimal point");
    }

    @Test
    void normalize_ShouldHandleEdgeCases() {
        assertEquals("1234567890", ssnAttribute.normalize("1234567890"), "Should return unchanged");
        assertEquals("12345678901.0", ssnAttribute.normalize("12345678901.0"),
                "Should drop decimal point even if exceeds length");
        assertEquals("12345678901", ssnAttribute.normalize("12345678901"),
                "Should return unchanged for long input without decimal");
        assertEquals("12345.0", ssnAttribute.normalize("12345.0"), "Should retain decimal point for short input");
        assertEquals("Unknown", ssnAttribute.normalize("Unknown"), "Should return non-numeric input unchanged");
        assertEquals("ABC-12-DEFG", ssnAttribute.normalize("ABC-12-DEFG"), "Should return non-numeric input unchanged");
    }

    @Test
    void normalize_ShouldHandleShortInputsWithoutCrashing() {
        assertEquals("123456", ssnAttribute.normalize("123456"), "Should handle 6-digit input without crashing");
        assertEquals("12345", ssnAttribute.normalize("12345"), "Should handle 5-digit input without crashing");
        assertEquals("1234", ssnAttribute.normalize("1234"), "Should handle 4-digit input without crashing");
        assertEquals("123", ssnAttribute.normalize("123"), "Should handle 3-digit input without crashing");
        assertEquals("12", ssnAttribute.normalize("12"), "Should handle 2-digit input without crashing");
        assertEquals("1", ssnAttribute.normalize("1"), "Should handle 1-digit input without crashing");
        assertEquals("", ssnAttribute.normalize(""), "Should handle empty input without crashing");
    }

    @Test
    void normalize_ShouldHandleSpaces() {
        assertEquals("123-45-6789", ssnAttribute.normalize("123 45 6789"), "Should normalize spaces to dashes");
        assertEquals("123-45-6789", ssnAttribute.normalize("123  45  6789"),
                "Should normalize multiple spaces to dashes");
        assertEquals("123-45-6789", ssnAttribute.normalize(" 123456789 "), "Should trim and format");
    }

    @Test
    void normalize_ShouldHandleMixedFormatting() {
        assertEquals("123-45-6789", ssnAttribute.normalize("123 45-6789"), "Should normalize mix of spaces and dashes");
        assertEquals("123-45-6789", ssnAttribute.normalize("123-45 6789"), "Should normalize mix of dashes and spaces");
        assertEquals("123-45-6789", ssnAttribute.normalize(" 123-456789"),
                "Should handle leading space and partial formatting");
    }

    @Test
    void normalize_ShouldHandleNullAndEmptyValues() {
        assertEquals(null, ssnAttribute.normalize(null), "Should return null for null input");
        assertEquals("", ssnAttribute.normalize(""), "Should return empty for empty input");
    }

    @Test
    void validate_ShouldReturnTrueForValidSSNs() {
        assertTrue(ssnAttribute.validate("223-45-6789"), "Valid SSN should be allowed");
        assertTrue(ssnAttribute.validate("223456789"), "Valid SSN without dashes should be allowed");
        assertTrue(ssnAttribute.validate("002-23-4567"), "Valid SSN with leading zeros should be allowed");
        assertTrue(ssnAttribute.validate("2234567"), "7-digit SSN should be allowed");
        assertTrue(ssnAttribute.validate("22345678"), "8-digit SSN should be allowed");
        assertTrue(ssnAttribute.validate("223456789.0"), "SSN with decimal should be allowed");
        assertTrue(ssnAttribute.validate("2234567.0"), "7-digit SSN with decimal should be allowed");
        assertTrue(ssnAttribute.validate("22345678.00"), "8-digit SSN with decimal should be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForInvalidSSNs() {
        assertFalse(ssnAttribute.validate(null), "Null value should not be allowed");
        assertFalse(ssnAttribute.validate(""), "Empty value should not be allowed");
        assertFalse(ssnAttribute.validate("12345"), "Short SSN (5 digits) should not be allowed");
        assertFalse(ssnAttribute.validate("123456"), "Short SSN (6 digits) should not be allowed");
        assertFalse(ssnAttribute.validate("1234567890"), "Long SSN should not be allowed");
        assertFalse(ssnAttribute.validate("000-00-0000"), "Invalid sequence should not be allowed");
        assertFalse(ssnAttribute.validate("666-00-0000"), "SSN starting with 666 should not be allowed");
        assertFalse(ssnAttribute.validate("123-11-0000"), "All zeros in last group should not be allowed");
        assertFalse(ssnAttribute.validate("123-00-1234"), "All zeros in middle group should not be allowed");
        assertFalse(ssnAttribute.validate("000-45-6789"), "All zeros in first group should not be allowed");
        assertFalse(ssnAttribute.validate("900-45-6789"), "SSN starting with 900 should not be allowed");
        assertFalse(ssnAttribute.validate("999-45-6789"), "SSN starting with 999 should not be allowed");
        assertFalse(ssnAttribute.validate("ABCDEFGHI"), "Non-numeric should not be allowed");
        assertFalse(ssnAttribute.validate("123-45-67AB"), "Mixed alphanumeric should not be allowed");
        assertFalse(ssnAttribute.validate("123.456.789"), "Multiple decimals should not be allowed");
        assertFalse(ssnAttribute.validate("123456789.123"),
                "Decimal with non-zero fractional part should not be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForSpecificInvalidSSNs() {
        assertFalse(ssnAttribute.validate("111-22-3333"), "Invalid SSN 111-22-3333 should not be allowed");
        assertFalse(ssnAttribute.validate("111223333"), "Invalid SSN 111223333 (without dashes) should not be allowed");
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testSSN = "123456789";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = ssnAttribute.normalize(testSSN);
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
            assertEquals("123-45-6789", result);
        }
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(ssnAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        SocialSecurityNumberAttribute deserializedAttribute = (SocialSecurityNumberAttribute) ois.readObject();
        ois.close();

        // Test various SSN values with both original and deserialized attributes
        String[] testValues = {
                "123456789",
                "123-45-6789",
                "001-23-4567",
                "001234567",
                "999-99-9999",
                "999999999"
        };

        for (String value : testValues) {
            assertEquals(
                    ssnAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    ssnAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    ssnAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    ssnAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
