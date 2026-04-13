/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

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

class CanadianPostalCodeAttributeTest {
    private CanadianPostalCodeAttribute canadianPostalCodeAttribute;

    @BeforeEach
    void setUp() {
        canadianPostalCodeAttribute = new CanadianPostalCodeAttribute(3);
    }

    @Test
    void getName_ShouldReturnCanadianPostalCode() {
        assertEquals("CanadianPostalCode", canadianPostalCodeAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnCanadianZipCodeAliases() {
        String[] expectedAliases = { "CanadianPostalCode", "CanadianZipCode" };
        assertArrayEquals(expectedAliases, canadianPostalCodeAttribute.getAliases());
    }

    @Test
    void normalize_ShouldHandleCanadianPostalCodes() {
        assertEquals("K1B 0A6", canadianPostalCodeAttribute.normalize("K1B0A6"));
        assertEquals("K1B 0A6", canadianPostalCodeAttribute.normalize("k1b0a6"));
        assertEquals("K1B 0A6", canadianPostalCodeAttribute.normalize("K1B 0A6"));
        assertEquals("M5V 3L9", canadianPostalCodeAttribute.normalize("m5v3l9"));
        assertEquals("H3Z 2Y7", canadianPostalCodeAttribute.normalize("H3Z2Y7"));
        assertEquals("T2X 1V4", canadianPostalCodeAttribute.normalize("t2x1v4"));
        assertEquals("V6B 1A1", canadianPostalCodeAttribute.normalize("v6b1a1"));
        assertEquals("N2L 3G1", canadianPostalCodeAttribute.normalize("N2L3G1"));
    }

    @Test
    void validate_ShouldReturnTrueForValidCanadianPostalCodes() {
        assertTrue(canadianPostalCodeAttribute.validate("K1B 0A7"));
        assertTrue(canadianPostalCodeAttribute.validate("K1B0A7"));
        assertTrue(canadianPostalCodeAttribute.validate("k1b 0a7"));
        assertTrue(canadianPostalCodeAttribute.validate("k1b0a7"));
        assertTrue(canadianPostalCodeAttribute.validate("M5V 3L9"));
        assertTrue(canadianPostalCodeAttribute.validate("H3Z 2Y7"));
        assertTrue(canadianPostalCodeAttribute.validate("T2X 1V4"));
        assertTrue(canadianPostalCodeAttribute.validate(" K1B 0A7 "));
        assertTrue(canadianPostalCodeAttribute.validate("  K1B0A7  "));
        assertTrue(canadianPostalCodeAttribute.validate("V6B 1A1"));
        assertTrue(canadianPostalCodeAttribute.validate("N2L 3G1"));
    }

    @Test
    void validate_ShouldReturnFalseForInvalidCanadianPostalCodes() {
        assertFalse(canadianPostalCodeAttribute.validate(null), "Null value should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate(""), "Empty value should not be allowed");

        // Invalid Canadian postal code formats
        assertFalse(canadianPostalCodeAttribute.validate("K1B 0A67"),
                "Too long Canadian postal code should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("K11 0A6"),
                "Invalid Canadian postal code format should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("KAA 0A6"),
                "Invalid Canadian postal code format should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("K1B 0AA"),
                "Invalid Canadian postal code format should not be allowed");

        // Invalid placeholder values
        assertFalse(canadianPostalCodeAttribute.validate("A1A 1A1"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("K1A 0A6"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("H0H 0H0"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("X0X 0X0"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("Y0Y 0Y0"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("Z0Z 0Z0"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("A0A 0A0"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("B1B 1B1"), "Invalid placeholder should not be allowed");
        assertFalse(canadianPostalCodeAttribute.validate("C2C 2C2"), "Invalid placeholder should not be allowed");

        // US ZIP codes should not validate
        assertFalse(canadianPostalCodeAttribute.validate("12345"), "US ZIP code should not validate");
        assertFalse(canadianPostalCodeAttribute.validate("12345-6789"), "US ZIP code should not validate");
    }

    @Test
    void normalize_ShouldHandleWhitespace() {
        // Test different types of whitespace for Canadian postal codes
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize("K1B0A7"), "No space");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize(" K1B0A7"), "Leading space");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize("K1B0A7 "), "Trailing space");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize(" K1B 0A7 "), "Leading and trailing spaces");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize("K1B\t0A7"), "Tab character");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize("K1B\n0A7"), "Newline character");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize("K1B\r\n0A7"), "Carriage return and newline");
        assertEquals("K1B 0A7", canadianPostalCodeAttribute.normalize("  K1B   0A7  "), "Multiple spaces");
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testPostalCode = "k1b0a7";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await();
                    barrier.await();

                    String result = canadianPostalCodeAttribute.normalize(testPostalCode);
                    results.add(result);

                    finishLatch.countDown();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
            thread.start();
        }

        startLatch.countDown();
        finishLatch.await(15, TimeUnit.SECONDS);

        assertEquals(threadCount, results.size());
        for (String result : results) {
            assertEquals("K1B 0A7", result);
        }
    }

    @Test
    void normalize_ShouldHandleEdgeCases() {
        // Test null and empty values
        assertNull(canadianPostalCodeAttribute.normalize(null));
        assertEquals("", canadianPostalCodeAttribute.normalize(""));

        // Test non-Canadian formats - should return trimmed original
        assertEquals("12345", canadianPostalCodeAttribute.normalize("12345"));
        assertEquals("12345-6789", canadianPostalCodeAttribute.normalize("12345-6789"));
        assertEquals("1234", canadianPostalCodeAttribute.normalize("1234 "));
        assertEquals("invalid", canadianPostalCodeAttribute.normalize("invalid"));
    }

    @Test
    void normalize_ShouldPadZip3ToFullPostalCode() {
        // Test Canadian ZIP-3 padding with " 000" (using valid, non-placeholder codes)
        assertEquals("J1X 000", canadianPostalCodeAttribute.normalize("J1X"));
        assertEquals("J1X 000", canadianPostalCodeAttribute.normalize(" J1X"));
        assertEquals("J1X 000", canadianPostalCodeAttribute.normalize("J1X "));
        assertEquals("J1X 000", canadianPostalCodeAttribute.normalize(" J1X "));
        assertEquals("J1X 000", canadianPostalCodeAttribute.normalize("j1x"));
        assertEquals("M5V 000", canadianPostalCodeAttribute.normalize("M5V"));
        assertEquals("M5V 000", canadianPostalCodeAttribute.normalize("m5v"));
        assertEquals("H3Z 000", canadianPostalCodeAttribute.normalize("H3Z"));
        assertEquals("T2X 000", canadianPostalCodeAttribute.normalize("T2X"));
        assertEquals("V6B 000", canadianPostalCodeAttribute.normalize("V6B"));
        assertEquals("N2L 000", canadianPostalCodeAttribute.normalize("N2L"));
        assertEquals("G1R 000", canadianPostalCodeAttribute.normalize("G1R"));
        assertEquals("L5N 000", canadianPostalCodeAttribute.normalize("L5N"));
    }

    @Test
    void validate_ShouldReturnTrueForValidZip3() {
        // Canadian ZIP-3 codes should be valid (will be padded during normalization)
        // Example from issue: "J1X" should be accepted
        assertTrue(canadianPostalCodeAttribute.validate("J1X"));
        assertTrue(canadianPostalCodeAttribute.validate(" J1X"));
        assertTrue(canadianPostalCodeAttribute.validate("J1X "));
        assertTrue(canadianPostalCodeAttribute.validate(" J1X "));
        assertTrue(canadianPostalCodeAttribute.validate("j1x"));

        // Other valid ZIP-3 codes
        assertTrue(canadianPostalCodeAttribute.validate("M5V"));
        assertTrue(canadianPostalCodeAttribute.validate("H3Z"));
        assertTrue(canadianPostalCodeAttribute.validate("T2X"));
        assertTrue(canadianPostalCodeAttribute.validate("V6B"));
        assertTrue(canadianPostalCodeAttribute.validate("N2L"));
        assertTrue(canadianPostalCodeAttribute.validate("G1R"));
        assertTrue(canadianPostalCodeAttribute.validate("L5N"));
    }

    @Test
    void validate_ShouldReturnFalseForInvalidZip3() {
        // These ZIP-3 codes are invalid as per requirements
        assertFalse(canadianPostalCodeAttribute.validate("K1A"), "K1A should be invalid");
        assertFalse(canadianPostalCodeAttribute.validate("M7A"), "M7A should be invalid");
        assertFalse(canadianPostalCodeAttribute.validate("H0H"), "H0H should be invalid");

        // These ZIP-3 codes are VALID - they are not in the invalid list
        assertTrue(canadianPostalCodeAttribute.validate("A1A"), "A1A should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("X0X"), "X0X should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("Y0Y"), "Y0Y should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("Z0Z"), "Z0Z should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("A0A"), "A0A should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("B1B"), "B1B should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("C2C"), "C2C should be valid");
    }

    @Test
    void normalize_ShouldPadPartialCanadianPostalCodes() {
        // Test 4-character partial postal code padding (e.g., "A1A1" → "A1A 1A0")
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize("J1X1"));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize(" J1X1"));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize("J1X1 "));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize(" J1X1 "));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize("J1X 1"));
        assertEquals("M5V 3A0", canadianPostalCodeAttribute.normalize("M5V3"));
        assertEquals("H3Z 2A0", canadianPostalCodeAttribute.normalize("H3Z2"));

        // Test 5-character partial postal code padding (e.g., "A1A1A" → "A1A 1A0")
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize("J1X1A"));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize(" J1X1A"));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize("J1X1A "));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize(" J1X1A "));
        assertEquals("J1X 1A0", canadianPostalCodeAttribute.normalize("J1X 1A"));
        assertEquals("M5V 3L0", canadianPostalCodeAttribute.normalize("M5V3L"));
        assertEquals("H3Z 2Y0", canadianPostalCodeAttribute.normalize("H3Z2Y"));
    }

    @Test
    void validate_ShouldReturnTrueForPartialCanadianPostalCodes() {
        // 4-character partial postal codes should be valid (will be padded during normalization)
        assertTrue(canadianPostalCodeAttribute.validate("J1X1"));
        assertTrue(canadianPostalCodeAttribute.validate(" J1X1"));
        assertTrue(canadianPostalCodeAttribute.validate("J1X1 "));
        assertTrue(canadianPostalCodeAttribute.validate(" J1X1 "));
        assertTrue(canadianPostalCodeAttribute.validate("J1X 1"));
        assertTrue(canadianPostalCodeAttribute.validate("M5V3"));
        assertTrue(canadianPostalCodeAttribute.validate("H3Z2"));

        // 5-character partial postal codes should be valid (will be padded during normalization)
        assertTrue(canadianPostalCodeAttribute.validate("J1X1A"));
        assertTrue(canadianPostalCodeAttribute.validate(" J1X1A"));
        assertTrue(canadianPostalCodeAttribute.validate("J1X1A "));
        assertTrue(canadianPostalCodeAttribute.validate(" J1X1A "));
        assertTrue(canadianPostalCodeAttribute.validate("J1X 1A"));
        assertTrue(canadianPostalCodeAttribute.validate("M5V3L"));
        assertTrue(canadianPostalCodeAttribute.validate("H3Z2Y"));
    }

    @Test
    void validate_ShouldReturnFalseForInvalidPartialCanadianPostalCodes() {
        // These partial postal codes start with invalid ZIP-3 prefixes
        assertFalse(canadianPostalCodeAttribute.validate("K1A1"), "K1A1 should be invalid (starts with K1A)");
        assertFalse(canadianPostalCodeAttribute.validate("K1A1A"), "K1A1A should be invalid (starts with K1A)");
        assertFalse(canadianPostalCodeAttribute.validate("M7A2"), "M7A2 should be invalid (starts with M7A)");
        assertFalse(canadianPostalCodeAttribute.validate("M7A2B"), "M7A2B should be invalid (starts with M7A)");
        assertFalse(canadianPostalCodeAttribute.validate("H0H3"), "H0H3 should be invalid (starts with H0H)");
        assertFalse(canadianPostalCodeAttribute.validate("H0H3C"), "H0H3C should be invalid (starts with H0H)");

        // These partial postal codes are VALID - they don't start with K1A, M7A, or H0H
        assertTrue(canadianPostalCodeAttribute.validate("K1B1"), "K1B1 should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("K1B1A"), "K1B1A should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("M5V3"), "M5V3 should be valid");
        assertTrue(canadianPostalCodeAttribute.validate("M5V3L"), "M5V3L should be valid");
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(canadianPostalCodeAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        CanadianPostalCodeAttribute deserializedAttribute = (CanadianPostalCodeAttribute) ois.readObject();
        ois.close();

        // Test various Canadian postal code values with both original and deserialized
        // attributes
        String[] testValues = {
                "K1B 0A7",
                "k1b0a7",
                "M5V 3L9",
                "H3Z2Y7",
                "T2X 1V4",
                "V6B 1A1"
        };

        for (String value : testValues) {
            assertEquals(
                    canadianPostalCodeAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    canadianPostalCodeAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    canadianPostalCodeAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    canadianPostalCodeAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }

    @Test
    void validate_IdempotencyShouldBeStable() {
        // Test that validation is idempotent: validate(x) == validate(normalize(x))
        // This ensures that normalized values can be re-validated successfully

        String[] testCases = {
            "k1a0b1",     // lowercase without space
            "K1A 0B1",    // uppercase with space (normalized form)
            "k1a 0b1",    // lowercase with space
            "j1x0a6",     // valid code lowercase
            "J1X 0A6",    // valid code uppercase
            "h0h0h0",     // Santa Claus postal code (invalid)
            "H0H 0H0",    // Santa Claus postal code uppercase (invalid)
        };

        for (String testCase : testCases) {
            String normalized = canadianPostalCodeAttribute.normalize(testCase);
            boolean validOriginal = canadianPostalCodeAttribute.validate(testCase);
            boolean validNormalized = canadianPostalCodeAttribute.validate(normalized);

            // Validation should be idempotent
            assertEquals(validOriginal, validNormalized,
                String.format("Idempotency failed: validate('%s') = %s, but validate('%s') = %s",
                testCase, validOriginal, normalized, validNormalized));

            // Double normalization should produce the same result
            String doubleNormalized = canadianPostalCodeAttribute.normalize(normalized);
            assertEquals(normalized, doubleNormalized,
                String.format("Normalization not idempotent: normalize('%s') != normalize(normalize('%s'))",
                normalized, testCase));
        }
    }
}
