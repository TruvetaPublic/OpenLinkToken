/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.utilities;

import java.text.Normalizer;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * This class includes functions such as normalizing accents,
 * standardizing formats, and other attribute-related transformations.
 *
 */
public class AttributeUtilities {
    private static final Pattern DIACRITICS = Pattern.compile("\\p{M}");
    private static final Map<Character, String> LATIN_EXTENDED_TRANSLITERATION_MAP = Map.ofEntries(
            Map.entry('Æ', "AE"),
            Map.entry('æ', "ae"),
            Map.entry('Ð', "D"),
            Map.entry('ð', "d"),
            Map.entry('Ø', "O"),
            Map.entry('ø', "o"),
            Map.entry('Þ', "TH"),
            Map.entry('þ', "th"),
            Map.entry('ß', "ss"),
            Map.entry('ẞ', "SS"),
            Map.entry('Đ', "D"),
            Map.entry('đ', "d"),
            Map.entry('Ħ', "H"),
            Map.entry('ħ', "h"),
            Map.entry('ı', "i"),
            Map.entry('Ĳ', "IJ"),
            Map.entry('ĳ', "ij"),
            Map.entry('Ŀ', "L"),
            Map.entry('ŀ', "l"),
            Map.entry('Ł', "L"),
            Map.entry('ł', "l"),
            Map.entry('ŉ', "n"),
            Map.entry('Ŋ', "NG"),
            Map.entry('ŋ', "ng"),
            Map.entry('Œ', "OE"),
            Map.entry('œ', "oe"),
            Map.entry('Ŧ', "T"),
            Map.entry('ŧ', "t"),
            Map.entry('ſ', "s"),
            Map.entry('Ƒ', "F"),
            Map.entry('ƒ', "f"),
            Map.entry('Ǆ', "DZ"),
            Map.entry('ǅ', "Dz"),
            Map.entry('ǆ', "dz"),
            Map.entry('Ǉ', "LJ"),
            Map.entry('ǈ', "Lj"),
            Map.entry('ǉ', "lj"),
            Map.entry('Ǌ', "NJ"),
            Map.entry('ǋ', "Nj"),
            Map.entry('ǌ', "nj"),
            Map.entry('Ǳ', "DZ"),
            Map.entry('ǲ', "Dz"),
            Map.entry('ǳ', "dz"),
            Map.entry('Ǽ', "AE"),
            Map.entry('ǽ', "ae"),
            Map.entry('Ǿ', "O"),
            Map.entry('ǿ', "o"));

    /**
     * Pattern that matches any character that is not an alphabetic character (a-z
     * or A-Z).
     * Used for removing or identifying non-alphabetic characters in strings.
     */
    public static final Pattern NON_ALPHABETIC_PATTERN = Pattern.compile("[^a-zA-Z]");

    /**
     * Pattern that matches one or more whitespace characters.
     * This includes spaces, tabs, line breaks, and other Unicode whitespace.
     *
     * Examples:
     * " " -> single space
     * "\t" -> tab
     * "\n" -> newline
     * "\r\n" -> carriage return + newline
     * " " -> multiple spaces
     */
    public static final Pattern WHITESPACE = Pattern.compile("\\s+");

    /**
     * Pattern that matches generational suffixes at the end of a string.
     * Matches case-insensitive suffixes after a whitespace character.
     *
     * Matches the following types of generational suffixes:
     * - Jr, Jr., Junior
     * - Sr, Sr., Senior
     * - Roman numerals (I, II, III, IV, V, VI, VII, VIII, IX, X)
     * - Ordinal numbers (1st, 2nd, 3rd, 4th, etc.)
     *
     * Examples:
     * "John Smith Jr" -> matches " Jr"
     * "Jane Doe Sr." -> matches " Sr."
     * "Robert Johnson III" -> matches " III"
     * "Thomas Wilson 2nd" -> matches " 2nd"
     */
    public static final Pattern GENERATIONAL_SUFFIX_PATTERN = Pattern
            .compile("(?i)\\s+(jr\\.?|junior|sr\\.?|senior|I{1,3}|IV|V|VI{0,3}|IX|X|\\d+(st|nd|rd|th))$");

    /**
     * A set of common placeholder names used to identify non-identifying or
     * placeholder text in data fields.
     *
     * This set includes various standard terms and phrases that are commonly used
     * as placeholders
     * in data records when actual values are unknown, not applicable, unavailable,
     * or intentionally masked.
     * These placeholders might be found in production data but don't represent
     * actual identifying information.
     *
     * These values should be treated as non-identifying data and may need special
     * handling during
     * data processing, anonymization, or when analyzing data quality.
     */
    public static final Set<String> COMMON_PLACEHOLDER_NAMES = Set.of(
            "Unknown", // Placeholder for unknown last names
            "N/A", // Not applicable
            "None", // No last name provided
            "Test", // Commonly used in testing scenarios
            "Sample", // Sample data placeholder
            "Donor", // Placeholder for donor records
            "Patient", // Placeholder for patient records
            "Automation Test", // Placeholder for automation tests
            "Automationtest", // Another variation of automation test
            "patient not found", // Placeholder for cases where patient data is not found
            "patientnotfound", // Another variation of patient not found
            "<masked>", // Placeholder for masked data
            "Anonymous", // Placeholder for anonymous records
            "zzztrash", // Placeholder for test or trash data
            "Missing", // Placeholder for missing data
            "Unavailable", // Placeholder for unavailable data
            "Not Available", // Placeholder for data not available
            "NotAvailable" // Placeholder for data not available (no spaces)
    );

    private AttributeUtilities() {
        throw new UnsupportedOperationException("This is a utility class and cannot be instantiated");
    }

    /**
     * Removes diacritic marks from the given string.
     *
     * This method performs the following steps:
     * 1. Trims the input string
     * 2. Normalizes the string using NFD form, which separates characters from
     * their diacritical marks
     * 3. Removes all diacritical marks using a predefined regular expression
     * pattern
     *
     * @param value The string from which to remove diacritical marks
     * @return A new string with all diacritical marks removed
     */
    public static String normalizeDiacritics(String value) {
        String trimmedValue = value.trim();
        StringBuilder transliteratedValue = new StringBuilder(trimmedValue.length());

        for (int index = 0; index < trimmedValue.length(); index++) {
            char character = trimmedValue.charAt(index);
            transliteratedValue.append(LATIN_EXTENDED_TRANSLITERATION_MAP.getOrDefault(character,
                    String.valueOf(character)));
        }

        return DIACRITICS.matcher(Normalizer.normalize(transliteratedValue.toString(), Normalizer.Form.NFD))
                .replaceAll("");
    }
}
