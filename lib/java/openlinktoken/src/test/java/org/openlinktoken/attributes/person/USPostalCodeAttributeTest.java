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

class USPostalCodeAttributeTest {
    private USPostalCodeAttribute usPostalCodeAttribute;

    @BeforeEach
    void setUp() {
        usPostalCodeAttribute = new USPostalCodeAttribute(3);
    }

    @Test
    void getName_ShouldReturnUSPostalCode() {
        assertEquals("USPostalCode", usPostalCodeAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnUSZipCodeAliases() {
        String[] expectedAliases = { "USPostalCode", "USZipCode" };
        assertArrayEquals(expectedAliases, usPostalCodeAttribute.getAliases());
    }

    @Test
    void normalize_ShouldReturnFirst5Digits() {
        assertEquals("10001", usPostalCodeAttribute.normalize("10001-6789"));
        assertEquals("10001", usPostalCodeAttribute.normalize("10001"));
        assertEquals("10001", usPostalCodeAttribute.normalize("100016789"));
        assertEquals("95123", usPostalCodeAttribute.normalize("95123-6789"));
        assertEquals("95123", usPostalCodeAttribute.normalize("951236789"));
        assertEquals("65201", usPostalCodeAttribute.normalize("65201-6789"));
        assertEquals("65201", usPostalCodeAttribute.normalize("652016789"));
    }

    @Test
    void normalize_ShouldHandleWhitespace() {
        // Test different types of whitespace for US ZIP codes
        assertEquals("10001", usPostalCodeAttribute.normalize("10001"), "No whitespace");
        assertEquals("10001", usPostalCodeAttribute.normalize(" 10001"), "Leading space");
        assertEquals("10001", usPostalCodeAttribute.normalize("10001 "), "Trailing space");
        assertEquals("10001", usPostalCodeAttribute.normalize(" 10001 "), "Leading and trailing spaces");
        assertEquals("10001", usPostalCodeAttribute.normalize("1 0 0 0 1"), "Spaces between digits");
        assertEquals("10001", usPostalCodeAttribute.normalize("10\t001"), "Tab character");
        assertEquals("10001", usPostalCodeAttribute.normalize("10\n001"), "Newline character");
        assertEquals("10001", usPostalCodeAttribute.normalize("10\r\n001"), "Carriage return and newline");
        assertEquals("10001", usPostalCodeAttribute.normalize("  10   001  "), "Multiple spaces");
    }

    @Test
    void validate_ShouldReturnTrueForValidUSZipCodes() {
        assertTrue(usPostalCodeAttribute.validate("95123 "));
        assertTrue(usPostalCodeAttribute.validate(" 95123"));
        assertTrue(usPostalCodeAttribute.validate("95123"));
        assertTrue(usPostalCodeAttribute.validate("95123-6789"));
        assertTrue(usPostalCodeAttribute.validate("951236789"));
        assertTrue(usPostalCodeAttribute.validate("65201-6789"));
        assertTrue(usPostalCodeAttribute.validate("652016789"));
        assertTrue(usPostalCodeAttribute.validate("10001"));
        assertTrue(usPostalCodeAttribute.validate("100016789"));
        assertTrue(usPostalCodeAttribute.validate("90210-1234"));
        assertTrue(usPostalCodeAttribute.validate("902101234"));
    }

    @Test
    void validate_ShouldReturnFalseForNullAndEmpty() {
        assertFalse(usPostalCodeAttribute.validate(null), "Null value should not be allowed");
        assertFalse(usPostalCodeAttribute.validate(""), "Empty value should not be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForInvalidFormats() {
        assertFalse(usPostalCodeAttribute.validate("12"), "Too short postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("123456"), "Long postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("1234-5678"), "Invalid format should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("abcde"), "Non-numeric should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("K1A 0A6"), "Canadian postal code should not validate");
    }

    @Test
    void validate_ShouldReturnFalseForPlaceholderZipCodes() {
        assertFalse(usPostalCodeAttribute.validate("12345"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("54321"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("01234"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("98765"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("00000"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("11111"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("22222"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("33333"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("55555"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("66666"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("77777"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("88888"), "Invalid postal code should not be allowed");
        assertFalse(usPostalCodeAttribute.validate("99999"), "Invalid postal code should not be allowed");
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testPostalCode = "10001-6789";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await();
                    barrier.await();

                    String result = usPostalCodeAttribute.normalize(testPostalCode);
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
            assertEquals("10001", result);
        }
    }

    @Test
    void normalize_ShouldHandleEdgeCases() {
        // Test short postal codes (less than 3 characters) - should return trimmed original
        assertEquals("12", usPostalCodeAttribute.normalize("12"));
        assertEquals("1", usPostalCodeAttribute.normalize("1"));

        // Test null and empty values
        assertNull(usPostalCodeAttribute.normalize(null));
        assertEquals("", usPostalCodeAttribute.normalize(""));

        // Test exactly 5 characters and longer ZIP codes
        assertEquals("10001", usPostalCodeAttribute.normalize("10001"));
        assertEquals("10001", usPostalCodeAttribute.normalize(" 10001"));
        assertEquals("10001", usPostalCodeAttribute.normalize("10001-1234"));
        assertEquals("10001", usPostalCodeAttribute.normalize("100011234"));

        // Test non-US formats - should return trimmed original
        assertEquals("K1A 0A7", usPostalCodeAttribute.normalize("K1A 0A7"));
        assertEquals("k1a0a7", usPostalCodeAttribute.normalize("k1a0a7"));
    }

    @Test
    void normalize_ShouldPadZip3ToZip5() {
        // Test ZIP-3 padding with "00"
        assertEquals("95100", usPostalCodeAttribute.normalize("951"));
        assertEquals("95100", usPostalCodeAttribute.normalize(" 951"));
        assertEquals("95100", usPostalCodeAttribute.normalize("951 "));
        assertEquals("95100", usPostalCodeAttribute.normalize(" 951 "));
        assertEquals("12300", usPostalCodeAttribute.normalize("123"));
        assertEquals("98000", usPostalCodeAttribute.normalize("980"));
        assertEquals("30300", usPostalCodeAttribute.normalize("303"));
        assertEquals("60600", usPostalCodeAttribute.normalize("606"));
    }

    @Test
    void validate_ShouldReturnTrueForValidZip3() {
        // US ZIP-3 codes should be valid (will be padded during normalization)
        // Example from issue: "951" should be accepted
        assertTrue(usPostalCodeAttribute.validate("951"));
        assertTrue(usPostalCodeAttribute.validate(" 951"));
        assertTrue(usPostalCodeAttribute.validate("951 "));
        assertTrue(usPostalCodeAttribute.validate(" 951 "));

        // Other valid ZIP-3 codes
        assertTrue(usPostalCodeAttribute.validate("123"));
        assertTrue(usPostalCodeAttribute.validate("980"));
        assertTrue(usPostalCodeAttribute.validate("303"));
        assertTrue(usPostalCodeAttribute.validate("606"));
    }

    @Test
    void validate_ShouldReturnFalseForInvalidZip3ThatWouldBeInvalid() {
        // These ZIP-3 codes are invalid as per requirements
        assertFalse(usPostalCodeAttribute.validate("000"), "000 should be invalid");
        assertFalse(usPostalCodeAttribute.validate("555"), "555 should be invalid");
        assertFalse(usPostalCodeAttribute.validate("888"), "888 should be invalid");

        // These ZIP-3 codes are VALID - they don't start with 000, 555, or 888
        assertTrue(usPostalCodeAttribute.validate("111"), "111 should be valid");
        assertTrue(usPostalCodeAttribute.validate("123"), "123 should be valid");
        assertTrue(usPostalCodeAttribute.validate("222"), "222 should be valid");
        assertTrue(usPostalCodeAttribute.validate("987"), "987 should be valid");
    }

    @Test
    void normalize_ShouldPadZip4ToZip5() {
        // Test ZIP-4 padding with "0"
        assertEquals("12340", usPostalCodeAttribute.normalize("1234"));
        assertEquals("12340", usPostalCodeAttribute.normalize(" 1234"));
        assertEquals("12340", usPostalCodeAttribute.normalize("1234 "));
        assertEquals("12340", usPostalCodeAttribute.normalize(" 1234 "));
        assertEquals("56780", usPostalCodeAttribute.normalize("5678"));
        assertEquals("90210", usPostalCodeAttribute.normalize("9021"));
        assertEquals("30300", usPostalCodeAttribute.normalize("3030"));
    }

    @Test
    void validate_ShouldReturnTrueForValidZip4() {
        // US ZIP-4 codes should be valid (will be padded during normalization)
        assertTrue(usPostalCodeAttribute.validate("1234"));
        assertTrue(usPostalCodeAttribute.validate(" 1234"));
        assertTrue(usPostalCodeAttribute.validate("1234 "));
        assertTrue(usPostalCodeAttribute.validate(" 1234 "));

        // Other valid ZIP-4 codes
        assertTrue(usPostalCodeAttribute.validate("5678"));
        assertTrue(usPostalCodeAttribute.validate("9021"));
        assertTrue(usPostalCodeAttribute.validate("3030"));
        assertTrue(usPostalCodeAttribute.validate("6060"));
    }

    @Test
    void validate_ShouldReturnFalseForInvalidZip4ThatWouldBeInvalid() {
        // These ZIP-4 codes start with invalid ZIP-3 prefixes
        assertFalse(usPostalCodeAttribute.validate("0001"), "0001 should be invalid (starts with 000)");
        assertFalse(usPostalCodeAttribute.validate("5555"), "5555 should be invalid (starts with 555)");
        assertFalse(usPostalCodeAttribute.validate("8888"), "8888 should be invalid (starts with 888)");

        // These ZIP-4 codes are VALID - they don't start with 000, 555, or 888
        assertTrue(usPostalCodeAttribute.validate("1111"), "1111 should be valid");
        assertTrue(usPostalCodeAttribute.validate("1234"), "1234 should be valid");
        assertTrue(usPostalCodeAttribute.validate("2222"), "2222 should be valid");
        assertTrue(usPostalCodeAttribute.validate("9876"), "9876 should be valid");
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(usPostalCodeAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        USPostalCodeAttribute deserializedAttribute = (USPostalCodeAttribute) ois.readObject();
        ois.close();

        // Test various US ZIP code values with both original and deserialized attributes
        String[] testValues = {
                "10001",
                "10001-1234",
                "90210-5678",
                "30301",
                "60601-2345"
        };

        for (String value : testValues) {
            assertEquals(
                    usPostalCodeAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    usPostalCodeAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    usPostalCodeAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    usPostalCodeAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }
}
