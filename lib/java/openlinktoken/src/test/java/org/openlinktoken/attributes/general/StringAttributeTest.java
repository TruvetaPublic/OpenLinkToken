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

/** Tests string attribute names, trimming, validation, and serialization. */
class StringAttributeTest {

    private StringAttribute stringAttribute;

    /** Creates a fresh string attribute for each test. */
    @BeforeEach
    void setUp() {
        stringAttribute = new StringAttribute();
    }

    /** Verifies the attribute reports the {@code String} name. */
    @Test
    void getName_ShouldReturnString() {
        assertEquals("String", stringAttribute.getName());
    }

    /** Verifies the string attribute exposes both expected aliases. */
    @Test
    void getAliases_ShouldReturnStringAndTextAliases() {
        assertArrayEquals(new String[] { "String", "Text" }, stringAttribute.getAliases());
    }

    /** Verifies normalization trims whitespace at the edges of a string. */
    @Test
    void normalize_ValidString_ShouldTrimWhitespace() {
        assertEquals("hello", stringAttribute.normalize("hello"));
        assertEquals("hello", stringAttribute.normalize("  hello  "));
        assertEquals("hello world", stringAttribute.normalize("  hello world  "));
        assertEquals("test", stringAttribute.normalize("\t\ntest\n\t"));
        assertEquals("a b c", stringAttribute.normalize("  a b c  "));
    }

    /** Verifies normalization preserves whitespace between string characters. */
    @Test
    void normalize_StringWithInternalWhitespace_ShouldPreserveIt() {
        assertEquals("hello  world", stringAttribute.normalize("  hello  world  "));
        assertEquals("test\tvalue", stringAttribute.normalize("  test\tvalue  "));
    }

    /** Verifies null input is rejected with the documented argument error. */
    @Test
    void normalize_NullValue_ShouldThrowIllegalArgumentException() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            stringAttribute.normalize(null);
        });
        assertEquals("String value cannot be null", exception.getMessage());
    }

    /** Verifies nonempty strings pass validation. */
    @Test
    void validate_ValidStrings_ShouldReturnTrue() {
        assertTrue(stringAttribute.validate("hello"));
        assertTrue(stringAttribute.validate("  hello  "));
        assertTrue(stringAttribute.validate("a"));
        assertTrue(stringAttribute.validate("123"));
        assertTrue(stringAttribute.validate("hello world"));
        assertTrue(stringAttribute.validate("test@example.com"));
    }

    /** Verifies null, empty, and whitespace-only strings fail validation. */
    @Test
    void validate_InvalidStrings_ShouldReturnFalse() {
        assertFalse(stringAttribute.validate(null));
        assertFalse(stringAttribute.validate(""));
        assertFalse(stringAttribute.validate("   "));
        assertFalse(stringAttribute.validate("\t\n"));
    }

    /** Verifies concurrent normalization returns the same trimmed string for every thread. */
    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testString = "  hello world  ";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = stringAttribute.normalize(testString);
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
            assertEquals("hello world", result);
        }
    }

    /** Verifies serialization preserves string normalization and validation behavior. */
    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(stringAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        StringAttribute deserializedAttribute = (StringAttribute) ois.readObject();
        ois.close();

        // Test various string values with both original and deserialized attributes
        String[] testValues = {
                "hello",
                "  world  ",
                "test string",
                "123",
                "a",
                "  trimmed  "
        };

        for (String value : testValues) {
            assertEquals(
                    stringAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    stringAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    stringAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    stringAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }

    /** Verifies whitespace-only input normalizes to an empty string. */
    @Test
    void normalize_EmptyStringAfterTrim_ShouldReturnEmpty() {
        // This tests that normalization doesn't fail on whitespace-only strings
        // Validation will fail, but normalization should succeed
        assertEquals("", stringAttribute.normalize("   "));
        assertEquals("", stringAttribute.normalize("\t\n"));
    }

    /** Verifies nonempty special-character and Unicode strings pass validation. */
    @Test
    void validate_SpecialCharacters_ShouldReturnTrue() {
        // StringAttribute should accept any non-empty string
        assertTrue(stringAttribute.validate("hello@world.com"));
        assertTrue(stringAttribute.validate("test-value_123"));
        assertTrue(stringAttribute.validate("!@#$%^&*()"));
        assertTrue(stringAttribute.validate("unicode: 你好"));
    }
}
