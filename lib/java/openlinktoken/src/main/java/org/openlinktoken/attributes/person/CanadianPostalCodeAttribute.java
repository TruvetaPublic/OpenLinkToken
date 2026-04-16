/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.person;

import java.util.List;
import java.util.Set;

import org.apache.commons.lang3.StringUtils;

import org.openlinktoken.attributes.BaseAttribute;
import org.openlinktoken.attributes.utilities.AttributeUtilities;
import org.openlinktoken.attributes.validation.NotStartsWithValidator;
import org.openlinktoken.attributes.validation.RegexValidator;

/**
 * Represents Canadian postal codes.
 *
 * This class handles validation and normalization of Canadian postal codes,
 * supporting the A1A 1A1 format (letter-digit-letter space digit-letter-digit).
 */
public class CanadianPostalCodeAttribute extends BaseAttribute {

    private static final String NAME = "CanadianPostalCode";
    private static final String[] ALIASES = new String[] { NAME, "CanadianZipCode" };

    /**
     * Regular expression pattern for validating Canadian postal codes.
     *
     * The pattern matches Canadian postal codes in the format "A1A 1A1" or "A1A1A1",
     * where 'A' represents an uppercase or lowercase letter and '1' represents a digit.
     * Also accepts partial formats:
     * - 3-character format "A1A" which will be padded to full format "A1A 000"
     * - 4-character format "A1A 1" which will be padded to "A1A 1A0"
     * - 5-character format "A1A 1A" which will be padded to "A1A 1A0"
     *
     * Breakdown:
     *   ^\\s*        - Allows optional leading whitespace.
     *   [A-Za-z]     - Matches a single letter (case-insensitive).
     *   \\d          - Matches a single digit.
     *   [A-Za-z]     - Matches a single letter (case-insensitive).
     *   (            - Start optional group for partial or full postal code:
     *     \\s?       - Allows an optional space between the two segments.
     *     \\d        - Matches a single digit.
     *     (          - Start optional group for last two characters:
     *       [A-Za-z] - Matches a single letter (case-insensitive).
     *       \\d?     - Matches an optional digit.
     *     )?         - End optional group for last two characters
     *   )?           - End optional group
     *   \\s*$        - Allows optional trailing whitespace.
     *
     * This pattern ensures that the postal code follows the Canadian standard,
     * optionally surrounded by whitespace and with an optional space in the middle.
     */
    private static final String CANADIAN_POSTAL_REGEX = "^\\s*[A-Za-z]\\d[A-Za-z](\\s?\\d([A-Za-z]\\d?)?)?\\s*$";

    // Full 6-character invalid postal codes
    private static final Set<String> INVALID_ZIP_CODES = Set.of(
            // 6-character Canadian postal code placeholders
            "A1A 1A1",
            "X0X 0X0",
            "Y0Y 0Y0",
            "Z0Z 0Z0",
            "A0A 0A0",
            "B1B 1B1",
            "C2C 2C2",
            "K1A 0A6",  // Canadian government address
            "H0H 0H0"   // Santa Claus postal code
    );

    // 3-character codes that are invalid when standalone (not when part of full codes)
    private static final Set<String> INVALID_ZIP3_CODES = Set.of(
            "K1A",  // Canadian government
            "M7A",  // Government of Ontario
            "H0H"   // Santa Claus
    );

    private final int minLength;
    private final RegexValidator regexValidator;
    private final NotStartsWithValidator notStartsWithValidator;

    /**
     * Constructs a CanadianPostalCodeAttribute with default minimum length of 6.
     */
    public CanadianPostalCodeAttribute() {
        this(6);
    }

    /**
     * Constructs a CanadianPostalCodeAttribute with specified minimum length.
     *
     * @param minLength The minimum length for postal codes (e.g., 3, 4, 5, or 6)
     */
    public CanadianPostalCodeAttribute(int minLength) {
        super(List.of());
        this.minLength = minLength;
        this.regexValidator = new RegexValidator(CANADIAN_POSTAL_REGEX);
        this.notStartsWithValidator = new NotStartsWithValidator(INVALID_ZIP_CODES);
    }

    @Override
    public boolean validate(String value) {
        if (value == null) {
            return false;
        }

        // First, check the regex pattern on the ORIGINAL value
        // This ensures the format is valid before normalization
        if (!regexValidator.eval(value)) {
            return false;
        }

        // Normalize the value to ensure idempotency
        // This converts to uppercase and formats consistently
        String normalizedValue = normalize(value);

        // Validate the NORMALIZED value against the full invalid codes
        // This ensures "k1a 0a6" and "K1A 0A6" are treated consistently
        for (String invalidCode : INVALID_ZIP_CODES) {
            if (normalizedValue.equalsIgnoreCase(invalidCode)) {
                return false;
            }
        }

        // Additionally check for codes starting with invalid ZIP-3 prefixes
        // But ONLY for padded partial codes (normalized length is 7 and ends with padding)
        // Full 6-character codes (without padding) are checked against the exact invalid list above
        if (normalizedValue.length() == 7 && normalizedValue.contains(" ")) {
            String zip3 = normalizedValue.substring(0, 3).toUpperCase();
            for (String invalidZip3 : INVALID_ZIP3_CODES) {
                if (zip3.equals(invalidZip3.toUpperCase())) {
                    // Check if this is a padded partial code
                    // Padded codes end with "000" (3-char), "A0" (4-char), or "0" (5-char after last letter)
                    String lastPart = normalizedValue.substring(4); // After "K1A "
                    if (lastPart.equals("000") ||           // K1A → K1A 000
                        lastPart.matches("\\dA0") ||        // K1A1 → K1A 1A0
                        lastPart.matches("\\d[A-Z]0")) {    // K1A1A → K1A 1A0
                        return false;
                    }
                }
            }
        }

        return true;
    }

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

    /**
     * Normalizes a Canadian postal code to standard A1A 1A1 format.
     *
     * For Canadian postal codes:
     * - Codes shorter than minLength are rejected (return original)
     * - 3-character format (e.g., "J1X") is padded with " 000" to create full format (e.g., "J1X 000") if minLength <= 3
     * - 4-character format (e.g., "J1X 1") is padded with "A0" to create full format (e.g., "J1X 1A0") if minLength <= 4
     * - 5-character format (e.g., "J1X 1A") is padded with "0" to create full format (e.g., "J1X 1A0") if minLength <= 5
     * - 6-character format returns uppercase format with space (e.g., "k1a0a6" becomes "K1A 0A6")
     * If the input value is null or doesn't match Canadian postal pattern, the
     * original trimmed value is returned.
     *
     * @param value The postal code to normalize
     * @return The normalized postal code or the original trimmed value if
     *         normalization
     *         isn't applicable
     */
    @Override
    public String normalize(String value) {
        if (value == null) {
            return value;
        }

        String trimmed = value.trim().replaceAll(AttributeUtilities.WHITESPACE.pattern(), StringUtils.EMPTY);

        // Check if it's a 3-character Canadian postal code (ZIP-3) - pad with " 000" if minLength allows
        if (trimmed.matches("[A-Za-z]\\d[A-Za-z]")) {
            if (minLength <= 3) {
                String upper = trimmed.toUpperCase();
                return upper + " 000";
            }
            // If minLength > 3, reject this by returning original
            return value.trim();
        }

        // Check if it's a 4-character partial postal code (e.g., "A1A1") - pad with "A0" if minLength allows
        if (trimmed.matches("[A-Za-z]\\d[A-Za-z]\\d")) {
            if (minLength <= 4) {
                String upper = trimmed.toUpperCase();
                return upper.substring(0, 3) + " " + upper.substring(3) + "A0";
            }
            // If minLength > 4, reject this by returning original
            return value.trim();
        }

        // Check if it's a 5-character partial postal code (e.g., "A1A1A") - pad with "0" if minLength allows
        if (trimmed.matches("[A-Za-z]\\d[A-Za-z]\\d[A-Za-z]")) {
            if (minLength <= 5) {
                String upper = trimmed.toUpperCase();
                return upper.substring(0, 3) + " " + upper.substring(3) + "0";
            }
            // If minLength > 5, reject this by returning original
            return value.trim();
        }

        // Check if it's a Canadian postal code (6 alphanumeric characters)
        if (trimmed.matches("[A-Za-z]\\d[A-Za-z]\\d[A-Za-z]\\d")) {
            String upper = trimmed.toUpperCase();
            return upper.substring(0, 3) + " " + upper.substring(3, 6);
        }

        // For values that don't match Canadian postal patterns, return trimmed original
        return value.trim();
    }
}
