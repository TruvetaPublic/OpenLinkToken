/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.person;

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

class LastNameAttributeTest {

    private LastNameAttribute lastNameAttribute;

    @BeforeEach
    void setUp() {
        lastNameAttribute = new LastNameAttribute();
    }

    @Test
    void getName_ShouldReturnLastName() {
        assertEquals("LastName", lastNameAttribute.getName());
    }

    @Test
    void getAliases_ShouldReturnLastNameAndSurname() {
        String[] expectedAliases = { "LastName", "Surname" };
        String[] actualAliases = lastNameAttribute.getAliases();
        assertArrayEquals(expectedAliases, actualAliases);
    }

    @Test
    void normalize_ShouldProcessLastName() {
        String input = "Doe";
        assertEquals("Doe", lastNameAttribute.normalize(input), "Last name should be properly normalized");
    }

    @Test
    void normalize_Accent() {
        String name1 = "Gómez";
        String name2 = "Gutiérrez";
        String name3 = "Hernández";
        String name4 = "Mäder";
        assertEquals("Gomez", lastNameAttribute.normalize(name1));
        assertEquals("Gutierrez", lastNameAttribute.normalize(name2));
        assertEquals("Hernandez", lastNameAttribute.normalize(name3));
        assertEquals("Mader", lastNameAttribute.normalize(name4));
    }

    @Test
    void validate_ShouldReturnTrueForValidLastNames_Part1() {
        // Names with 3+ characters
        assertTrue(lastNameAttribute.validate("Doe"), "3+ character last name should be allowed");
        assertTrue(lastNameAttribute.validate("Smith-Jones"), "Hyphenated last name should be allowed");
        assertTrue(lastNameAttribute.validate("  Wang  "), "Name with whitespace should be allowed");

        // 2-character names with at least one vowel
        assertTrue(lastNameAttribute.validate("Li"), "2-character name with a vowel should be allowed");
        assertTrue(lastNameAttribute.validate("Wu"), "2-character name with a vowel should be allowed");
        assertTrue(lastNameAttribute.validate("Ai"), "2-character name with a vowel should be allowed");
        assertTrue(lastNameAttribute.validate("Im"), "2-character name with a vowel should be allowed");
    }

    @Test
    void validate_ShouldReturnTrueForValidLastNames_Part2() {
        // More 2-character names with at least one vowel
        assertTrue(lastNameAttribute.validate("Ek"), "2-character name with a vowel should be allowed");
        assertTrue(lastNameAttribute.validate("Ox"), "2-character name with a vowel should be allowed");
        assertTrue(lastNameAttribute.validate("Uk"), "2-character name with a vowel should be allowed");

        // Special case for "Ng"
        assertTrue(lastNameAttribute.validate("Ng"), "Ng should be allowed as a special case");
        assertTrue(lastNameAttribute.validate("ng"), "ng should be allowed as a special case (case insensitive)");
        assertTrue(lastNameAttribute.validate("NG"), "NG should be allowed as a special case (case insensitive)");
    }

    @Test
    void validate_ShouldReturnFalseForInvalidLastNames() {
        // Null or empty
        assertFalse(lastNameAttribute.validate(null), "Null value should not be allowed");
        assertFalse(lastNameAttribute.validate(""), "Empty value should not be allowed");
        assertFalse(lastNameAttribute.validate("  "), "Whitespace-only value should not be allowed");

        // Single character
        assertFalse(lastNameAttribute.validate("D"), "Single character last name should not be allowed");

        // 2-character names with no vowels (except Ng)
        assertFalse(lastNameAttribute.validate("Mn"), "2-character name with no vowels should not be allowed");
        assertFalse(lastNameAttribute.validate("Pq"), "2-character name with no vowels should not be allowed");
        assertFalse(lastNameAttribute.validate("Xz"), "2-character name with no vowels should not beallowed");
    }

    @Test
    void validate_ShouldReturnFalseForBasicPlaceholderValues() {
        // Test basic placeholder values
        assertFalse(lastNameAttribute.validate("Unknown"), "Unknown should not be allowed");
        assertFalse(lastNameAttribute.validate("N/A"), "N/A should not be allowed");
        assertFalse(lastNameAttribute.validate("None"), "None should not be allowed");
        assertFalse(lastNameAttribute.validate("Test"), "Test should not be allowed");
        assertFalse(lastNameAttribute.validate("Sample"), "Sample should not be allowed");
        assertFalse(lastNameAttribute.validate("Anonymous"), "Anonymous should not be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForMedicalPlaceholderValues() {
        // Test medical/healthcare specific placeholders
        assertFalse(lastNameAttribute.validate("Donor"), "Donor should not be allowed");
        assertFalse(lastNameAttribute.validate("Patient"), "Patient should not be allowed");
        assertFalse(lastNameAttribute.validate("patient not found"), "patient not found should not be allowed");
        assertFalse(lastNameAttribute.validate("patientnotfound"), "patientnotfound should not be allowed");
        assertFalse(lastNameAttribute.validate("<masked>"), "<masked> should not be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForTestingPlaceholderValues() {
        // Test automation/testing specific placeholders
        assertFalse(lastNameAttribute.validate("Automation Test"), "Automation Test should not be allowed");
        assertFalse(lastNameAttribute.validate("Automationtest"), "Automationtest should not be allowed");
        assertFalse(lastNameAttribute.validate("zzztrash"), "zzztrash should not be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForDataAvailabilityPlaceholders() {
        // Test data availability placeholders
        assertFalse(lastNameAttribute.validate("Missing"), "Missing should not be allowed");
        assertFalse(lastNameAttribute.validate("Unavailable"), "Unavailable should not be allowed");
        assertFalse(lastNameAttribute.validate("Not Available"), "Not Available should not be allowed");
        assertFalse(lastNameAttribute.validate("NotAvailable"), "NotAvailable should not be allowed");
    }

    @Test
    void validate_ShouldReturnFalseForCaseInsensitivePlaceholders() {
        // Test case insensitivity (NotInValidator uses equalsIgnoreCase)
        assertFalse(lastNameAttribute.validate("UNKNOWN"), "UNKNOWN (uppercase) should not be allowed");
        assertFalse(lastNameAttribute.validate("unknown"), "unknown (lowercase) should not be allowed");
        assertFalse(lastNameAttribute.validate("UnKnOwN"), "UnKnOwN (mixed case) should not be allowed");

        assertFalse(lastNameAttribute.validate("SAMPLE"), "SAMPLE (uppercase) should not be allowed");
        assertFalse(lastNameAttribute.validate("sample"), "sample (lowercase) should not be allowed");

        assertFalse(lastNameAttribute.validate("MISSING"), "MISSING (uppercase) should not be allowed");
        assertFalse(lastNameAttribute.validate("missing"), "missing (lowercase) should not be allowed");
    }

    @Test
    void validate_ShouldReturnTrueForValidCommonLastNames() {
        // Common legitimate last names (all 3+ characters)
        assertTrue(lastNameAttribute.validate("Smith"), "Smith should be allowed");
        assertTrue(lastNameAttribute.validate("Johnson"), "Johnson should be allowed");
        assertTrue(lastNameAttribute.validate("García"), "García should be allowed");
        assertTrue(lastNameAttribute.validate("O'Connor"), "O'Connor should be allowed");
        assertTrue(lastNameAttribute.validate("Smith-Jones"), "Smith-Jones should be allowed");
        assertTrue(lastNameAttribute.validate("MacDonald"), "MacDonald should be allowed");
        assertTrue(lastNameAttribute.validate("De La Cruz"), "De La Cruz should be allowed");
    }

    @Test
    void validate_ShouldReturnTrueForTwoCharacterLastNames() {
        // Two-character last names with vowels
        assertTrue(lastNameAttribute.validate("Lo"), "Lo should be allowed (2 chars with vowel)");
        assertTrue(lastNameAttribute.validate("Wu"), "Wu should be allowed (2 chars with vowel)");
        assertTrue(lastNameAttribute.validate("Xu"), "Xu should be allowed (2 chars with vowel)");
    }

    @Test
    void validate_ShouldReturnTrueForEdgeCases() {
        // Edge cases for validation rule
        assertTrue(lastNameAttribute.validate(" Ng "), "Ng with spaces should be allowed");
        assertTrue(lastNameAttribute.validate(" Wu "), "Wu with spaces should be allowed");
        assertTrue(lastNameAttribute.validate(" Ai "), "Ai with spaces should be allowed");
    }

    @Test
    void validate_ShouldReturnTrueForLastNamesCloseToPlaceholders() {
        // Test last names that might be similar to placeholders but are legitimate
        assertTrue(lastNameAttribute.validate("Tester"), "Tester should be allowed (different from Test)");
        assertTrue(lastNameAttribute.validate("Samples"), "Samples should be allowed (different from Sample)");
        assertTrue(lastNameAttribute.validate("Patton"), "Patton should be allowed (different from Patient)");
        assertTrue(lastNameAttribute.validate("Anderson"), "Anderson should be allowed (different from Anonymous)");
    }

    @Test
    void normalize_ThreadSafety() throws InterruptedException {
        final int threadCount = 100;
        final CountDownLatch startLatch = new CountDownLatch(1);
        final CountDownLatch finishLatch = new CountDownLatch(threadCount);
        final CyclicBarrier barrier = new CyclicBarrier(threadCount);
        final List<String> results = Collections.synchronizedList(new ArrayList<>());
        final String testName = "Hernández";

        for (int i = 0; i < threadCount; i++) {
            Thread thread = new Thread(() -> {
                try {
                    startLatch.await(); // Wait for all threads to be ready
                    barrier.await(); // Synchronize to increase contention

                    // Perform normalization
                    String result = lastNameAttribute.normalize(testName);
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
            assertEquals("Hernandez", result);
        }
    }

    @Test
    void normalize_ShouldRemoveGenerationalSuffixes() {
        // Test various generational suffix formats
        assertEquals("Smith", lastNameAttribute.normalize("Smith Jr."));
        assertEquals("Johnson", lastNameAttribute.normalize("Johnson Junior"));
        assertEquals("Williams", lastNameAttribute.normalize("Williams Sr."));
        assertEquals("Brown", lastNameAttribute.normalize("Brown Senior"));
        assertEquals("Davis", lastNameAttribute.normalize("Davis II"));
        assertEquals("Miller", lastNameAttribute.normalize("Miller III"));
        assertEquals("Wilson", lastNameAttribute.normalize("Wilson IV"));
        assertEquals("Moore", lastNameAttribute.normalize("Moore V"));
        assertEquals("Taylor", lastNameAttribute.normalize("Taylor VI"));
        assertEquals("Anderson", lastNameAttribute.normalize("Anderson VII"));
        assertEquals("Thomas", lastNameAttribute.normalize("Thomas VIII"));
        assertEquals("Jackson", lastNameAttribute.normalize("Jackson IX"));
        assertEquals("White", lastNameAttribute.normalize("White X"));

        // Test numeric suffixes
        assertEquals("Garcia", lastNameAttribute.normalize("Garcia 1st"));
        assertEquals("Martinez", lastNameAttribute.normalize("Martinez 2nd"));
        assertEquals("Robinson", lastNameAttribute.normalize("Robinson 3rd"));
        assertEquals("Clark", lastNameAttribute.normalize("Clark 4th"));
        assertEquals("Rodriguez", lastNameAttribute.normalize("Rodriguez 5th"));

        // Test case insensitive matching
        assertEquals("Lewis", lastNameAttribute.normalize("Lewis jr."));
        assertEquals("Lee", lastNameAttribute.normalize("Lee SENIOR"));
        assertEquals("Walker", lastNameAttribute.normalize("Walker ii"));
        assertEquals("Hall", lastNameAttribute.normalize("Hall JR"));

        // Test suffixes without periods
        assertEquals("Allen", lastNameAttribute.normalize("Allen Jr"));
        assertEquals("Young", lastNameAttribute.normalize("Young Sr"));
    }

    @Test
    void normalize_ShouldRemoveSpecialCharacters() {
        // Test removal of dashes, spaces, and other non-alphanumeric characters
        assertEquals("OConnor", lastNameAttribute.normalize("O'Connor"));
        assertEquals("SmithJones", lastNameAttribute.normalize("Smith-Jones"));
        assertEquals("VanDerBerg", lastNameAttribute.normalize("Van Der Berg"));
        assertEquals("McDonald", lastNameAttribute.normalize("Mc Donald"));
        assertEquals("DelaRosa", lastNameAttribute.normalize("De la Rosa"));

        // Test various special characters
        assertEquals("Smith", lastNameAttribute.normalize("Smith@#$"));
        assertEquals("Johnson", lastNameAttribute.normalize("Johnson_123"));
        assertEquals("WilliamsCo", lastNameAttribute.normalize("Williams&Co"));
        assertEquals("Brown", lastNameAttribute.normalize("Brown*"));
        assertEquals("DavisTest", lastNameAttribute.normalize("Davis(Test)"));
        assertEquals("MillerWilson", lastNameAttribute.normalize("Miller+Wilson"));
        assertEquals("GarciaLopez", lastNameAttribute.normalize("García-López"));

        // Test numbers mixed with letters
        assertEquals("Smith", lastNameAttribute.normalize("Smith123"));
        assertEquals("Johnson", lastNameAttribute.normalize("John5son"));
        assertEquals("Tet", lastNameAttribute.normalize("Te$t123"));
    }

    @Test
    void normalize_ShouldHandleGenerationalSuffixesAndSpecialCharacters() {
        // Test combination of generational suffixes and special characters
        assertEquals("OConnor", lastNameAttribute.normalize("O'Connor Jr."));
        assertEquals("SmithJones", lastNameAttribute.normalize("Smith-Jones Senior"));
        assertEquals("McDonald", lastNameAttribute.normalize("Mc Donald III"));
        assertEquals("VanDerBerg", lastNameAttribute.normalize("Van Der Berg II"));

        // Test with accents, suffixes, and special characters
        assertEquals("GarciaLopez", lastNameAttribute.normalize("García-López Jr."));
        assertEquals("HernandezMartinez", lastNameAttribute.normalize("Hernández-Martinez Sr."));
        assertEquals("RodriguezOBrien", lastNameAttribute.normalize("Rodríguez O'Brien III"));
    }

    @Test
    void normalize_ShouldHandleComplexCombinations() {
        // Test names with accents, special characters, and suffixes all together
        assertEquals("GomezRodriguez", lastNameAttribute.normalize("Gómez-Rodríguez Jr."));
        assertEquals("DelaCroix", lastNameAttribute.normalize("De-la-Croix Sr."));
        assertEquals("OBrienMcCarthy", lastNameAttribute.normalize("O'Brien-McCarthy III"));
        assertEquals("VanderWaal", lastNameAttribute.normalize("Vander-Waal IV"));

        // Test edge cases
        assertEquals("TetNme", lastNameAttribute.normalize("Te$t-N@me Jr."));
        assertEquals("ComplexName", lastNameAttribute.normalize("Cömplex-Nâme123 Senior"));
    }

    @Test
    void testSerialization() throws Exception {
        // Serialize the attribute
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(lastNameAttribute);
        oos.close();

        // Deserialize the attribute
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        LastNameAttribute deserializedAttribute = (LastNameAttribute) ois.readObject();
        ois.close();

        // Test various values with both original and deserialized attributes
        String[] testValues = {
                "Smith",
                "Johnson",
                "García",
                "Gómez",
                "Mäder",
                "van der Berg",
                "O'Connor",
                "Smith-Jones",
                "McDonald"
        };

        for (String value : testValues) {
            assertEquals(
                    lastNameAttribute.getName(),
                    deserializedAttribute.getName(),
                    "Attribute names should match");

            assertArrayEquals(
                    lastNameAttribute.getAliases(),
                    deserializedAttribute.getAliases(),
                    "Attribute aliases should match");

            assertEquals(
                    lastNameAttribute.normalize(value),
                    deserializedAttribute.normalize(value),
                    "Normalization should be identical for value: " + value);

            assertEquals(
                    lastNameAttribute.validate(value),
                    deserializedAttribute.validate(value),
                    "Validation should be identical for value: " + value);
        }
    }

    @Test
    void validate_ShouldAcceptSpecialCaseNgAndTwoLetterNamesWithVowels() {
        // Special case: Ng (case variations)
        assertTrue(lastNameAttribute.validate("Ng"), "Ng should be allowed as a special case");
        assertTrue(lastNameAttribute.validate("NG"), "NG should be allowed as a special case");
        assertTrue(lastNameAttribute.validate("ng"), "ng should be allowed as a special case");

        // Two-letter last names with vowels (consonant+vowel)
        assertTrue(lastNameAttribute.validate("Li"), "Li should be allowed (consonant+vowel)");
        assertTrue(lastNameAttribute.validate("Wu"), "Wu should be allowed (consonant+vowel)");
        assertTrue(lastNameAttribute.validate("Xu"), "Xu should be allowed (consonant+vowel)");
        assertTrue(lastNameAttribute.validate("Yi"), "Yi should be allowed (consonant+vowel)");

        // Two-letter last names with vowels (vowel+consonant)
        assertTrue(lastNameAttribute.validate("Ox"), "Ox should be allowed (vowel+consonant)");
        assertTrue(lastNameAttribute.validate("An"), "An should be allowed (vowel+consonant)");

        // Two-letter last names with two vowels
        assertTrue(lastNameAttribute.validate("Ai"), "Ai should be allowed (vowel+vowel)");
        assertTrue(lastNameAttribute.validate("Oe"), "Oe should be allowed (vowel+vowel)");
        assertTrue(lastNameAttribute.validate("Ia"), "Ia should be allowed (vowel+vowel)");
        assertTrue(lastNameAttribute.validate("Eu"), "Eu should be allowed (vowel+vowel)");
        assertTrue(lastNameAttribute.validate("Ao"), "Ao should be allowed (vowel+vowel)");

        // Whitespace handling with 2-char names
        assertTrue(lastNameAttribute.validate("  Ng  "), "Ng with spaces should be allowed");
        assertTrue(lastNameAttribute.validate("  Ai  "), "Ai with spaces should be allowed");
        assertTrue(lastNameAttribute.validate("  Wu  "), "Wu with spaces should be allowed");
    }

    @Test
    void validate_ShouldRejectTwoLetterNamesWithoutVowelsAndSingleLetters() {
        // Two-letter names without vowels (should be rejected)
        assertFalse(lastNameAttribute.validate("Ms"), "Ms should not be allowed (no vowels)");
        assertFalse(lastNameAttribute.validate("Zh"), "Zh should not be allowed (no vowels)");
        assertFalse(lastNameAttribute.validate("Ps"), "Ps should not be allowed (no vowels)");
        assertFalse(lastNameAttribute.validate("Ts"), "Ts should not be allowed (no vowels)");

        // Single-letter names (should be rejected)
        assertFalse(lastNameAttribute.validate("A"), "Single letter A should not be allowed");
        assertFalse(lastNameAttribute.validate("Z"), "Single letter Z should not be allowed");
        assertFalse(lastNameAttribute.validate("  B  "), "Single letter B with spaces should not be allowed");
    }

    @Test
    void validate_IdempotencyShouldBeStable() {
        // Test that validation is idempotent: validate(x) == validate(normalize(x))
        // This ensures that normalized values can be re-validated successfully

        // Test with values that would fail without the fix
        String[] testCases = {
            "N.M.",      // Normalizes to "NM" (2 consonants)
            "A.B.",      // Normalizes to "AB" (2 consonants)
            "J-K",       // Normalizes to "JK" (2 consonants)
            "Smith-Jones",  // Normalizes to "SmithJones"
            "O'Connor",     // Normalizes to "OConnor"
            "Van Der Berg", // Normalizes to "VanDerBerg"
            "García-López", // Normalizes to "GarciaLopez"
        };

        for (String testCase : testCases) {
            String normalized = lastNameAttribute.normalize(testCase);
            boolean validOriginal = lastNameAttribute.validate(testCase);
            boolean validNormalized = lastNameAttribute.validate(normalized);

            // If original is valid, normalized should also be valid (idempotency)
            if (validOriginal) {
                assertTrue(validNormalized,
                    String.format("Idempotency failed: '%s' is valid but normalized '%s' is not",
                    testCase, normalized));
            }

            // Double normalization should produce the same result
            String doubleNormalized = lastNameAttribute.normalize(normalized);
            assertEquals(normalized, doubleNormalized,
                String.format("Normalization not idempotent: normalize('%s') != normalize(normalize('%s'))",
                normalized, testCase));
        }
    }

    @Test
    void validate_NormalizedValuesShouldPassValidation() {
        // Specific test for the idempotency requirement
        // Validation should be stable: validate(x) == validate(normalize(x))

        // Test case 1: "N.M." normalizes to "NM" (2 consonants - INVALID)
        String input1 = "N.M.";
        String normalized1 = lastNameAttribute.normalize(input1);
        assertEquals("NM", normalized1, "N.M. should normalize to NM");

        boolean valid1 = lastNameAttribute.validate(input1);
        boolean validNormalized1 = lastNameAttribute.validate(normalized1);
        assertEquals(valid1, validNormalized1,
            "Validation should be idempotent: validate('N.M.') == validate('NM')");
        assertFalse(valid1, "N.M. should be invalid (normalizes to 2 consonants)");

        // Test case 2: "A.I." normalizes to "AI" (2 vowels - VALID)
        String input2 = "A.I.";
        String normalized2 = lastNameAttribute.normalize(input2);
        assertEquals("AI", normalized2, "A.I. should normalize to AI");

        boolean valid2 = lastNameAttribute.validate(input2);
        boolean validNormalized2 = lastNameAttribute.validate(normalized2);
        assertEquals(valid2, validNormalized2,
            "Validation should be idempotent: validate('A.I.') == validate('AI')");
        assertTrue(valid2, "A.I. should be valid (normalizes to 2 vowels)");
    }

    @Test
    void validate_ShouldRejectValuesNormalizingToPlaceholders() {
        // Test that values which normalize to placeholder values are rejected
        // This ensures idempotency: validate(x) should equal validate(normalize(x))

        // "TEST16" normalizes to "TEST" which is a placeholder
        assertFalse(lastNameAttribute.validate("TEST16"),
            "TEST16 should be rejected (normalizes to placeholder TEST)");

        // "SAMPLE123" normalizes to "SAMPLE" which is a placeholder
        assertFalse(lastNameAttribute.validate("SAMPLE123"),
            "SAMPLE123 should be rejected (normalizes to placeholder SAMPLE)");

        // "Unknown999" normalizes to "Unknown" which is a placeholder
        assertFalse(lastNameAttribute.validate("Unknown999"),
            "Unknown999 should be rejected (normalizes to placeholder Unknown)");

        // "Patient-123" normalizes to "Patient123" then "Patient" which is a placeholder
        assertFalse(lastNameAttribute.validate("Patient-123"),
            "Patient-123 should be rejected (normalizes to placeholder Patient)");

        // Verify normalization produces placeholder values
        assertEquals("TEST", lastNameAttribute.normalize("TEST16"));
        assertEquals("SAMPLE", lastNameAttribute.normalize("SAMPLE123"));
        assertEquals("Unknown", lastNameAttribute.normalize("Unknown999"));
        assertEquals("Patient", lastNameAttribute.normalize("Patient-123"));

        // Verify the normalized values themselves are invalid
        assertFalse(lastNameAttribute.validate("TEST"), "TEST is a placeholder");
        assertFalse(lastNameAttribute.validate("SAMPLE"), "SAMPLE is a placeholder");
        assertFalse(lastNameAttribute.validate("Unknown"), "Unknown is a placeholder");
        assertFalse(lastNameAttribute.validate("Patient"), "Patient is a placeholder");
    }
}
