/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import java.util.List;
import java.util.Set;

import org.apache.commons.lang3.StringUtils;

import com.truveta.openlinktoken.attributes.BaseAttribute;
import com.truveta.openlinktoken.attributes.utilities.AttributeUtilities;
import com.truveta.openlinktoken.attributes.validation.NotStartsWithValidator;
import com.truveta.openlinktoken.attributes.validation.RegexValidator;

/**
 * Represents US postal codes (ZIP codes).
 *
 * This class handles validation and normalization of US ZIP codes, supporting
 * both 5-digit format (12345) and 5+4 format (12345-6789).
 */
public class USPostalCodeAttribute extends BaseAttribute {

    private static final String NAME = "USPostalCode";
    private static final String[] ALIASES = new String[] { NAME, "USZipCode" };

    /**
     * Regular expression pattern for validating US postal (ZIP) codes.
     *
     * This pattern matches the following formats:
     *  - 3-digit ZIP code (e.g., "951") - will be padded to 5 digits
     *  - 4-digit ZIP code (e.g., "1234") - will be padded to 5 digits
     *  - 5-digit ZIP code (e.g., "12345")
     *  - ZIP+4 code with hyphen (e.g., "12345-6789")
     *  - 9-digit ZIP code without hyphen (e.g., "123456789")
     * The pattern also allows optional leading and trailing whitespace.
     *
     * Breakdown of the regex:
     *   ^\s*                Start of string, optional leading whitespace
     *   (                   Start of group:
     *     \d{3}             Exactly 3 digits (ZIP-3, will be padded)
     *     |                 OR
     *     \d{4}             Exactly 4 digits (ZIP-4, will be padded)
     *     |                 OR
     *     \d{5}             Exactly 5 digits
     *     ( -\d{4} )?       Optional: hyphen followed by exactly 4 digits
     *     |                 OR
     *     \d{9}             Exactly 9 digits (ZIP+4 without hyphen)
     *   )
     *   \s*$                Optional trailing whitespace, end of string
     */
    private static final String US_ZIP_REGEX = "^\\s*(\\d{3}|\\d{4}|\\d{5}(-\\d{4})?|\\d{9})\\s*$";

    private static final Set<String> INVALID_ZIP_CODES = Set.of(
            // 5-digit invalid codes
            "11111",
            "22222",
            "33333",
            "66666",
            "77777",
            "99999",
            // Commonly used placeholders
            "01234",
            "12345",
            "54321",
            "98765",
            // 3-digit invalid codes (ZIP-3 prefixes that should be invalidated)
            // Note: "000" invalidates "00000" and all codes starting with "000"
            // Note: "555" invalidates "55555" and all codes starting with "555"
            // Note: "888" invalidates "88888" and all codes starting with "888"
            "000",
            "555",
            "888"
    );

    private final int minLength;

    /**
     * Constructs a USPostalCodeAttribute with default minimum length of 5.
     */
    public USPostalCodeAttribute() {
        this(5);
    }

    /**
     * Constructs a USPostalCodeAttribute with specified minimum length.
     *
     * @param minLength The minimum length for postal codes (e.g., 3, 4, or 5)
     */
    public USPostalCodeAttribute(int minLength) {
        super(List.of(
                new RegexValidator(US_ZIP_REGEX),
                new NotStartsWithValidator(INVALID_ZIP_CODES)));
        this.minLength = minLength;
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
     * Normalizes a US ZIP code to standard 5-digit format.
     *
     * For US ZIP codes:
     * - Codes shorter than minLength are rejected (return original)
     * - 3-digit ZIP code (ZIP-3) is padded with "00" to create 5-digit format (e.g., "951" becomes "95100") if minLength <= 3
     * - 4-digit ZIP code (ZIP-4) is padded with "0" to create 5-digit format (e.g., "1234" becomes "12340") if minLength <= 4
     * - 5-digit or longer ZIP codes return the first 5 digits (e.g., "12345-6789" becomes "12345")
     * If the input value is null or doesn't match US ZIP pattern, the original
     * trimmed value is returned.
     *
     * @param value The ZIP code to normalize
     * @return The normalized ZIP code or the original trimmed value if
     *         normalization
     *         isn't applicable
     */
    @Override
    public String normalize(String value) {
        if (value == null) {
            return value;
        }

        String trimmed = value.trim().replaceAll(AttributeUtilities.WHITESPACE.pattern(), StringUtils.EMPTY);

        // Check if it's a 3-digit ZIP code (ZIP-3) - pad with "00" if minLength allows
        if (trimmed.matches("\\d{3}")) {
            if (minLength <= 3) {
                return trimmed + "00";
            }
            // If minLength > 3, reject this by returning original
            return value.trim();
        }

        // Check if it's a 4-digit ZIP code (ZIP-4) - pad with "0" if minLength allows
        if (trimmed.matches("\\d{4}")) {
            if (minLength <= 4) {
                return trimmed + "0";
            }
            // If minLength > 4, reject this by returning original
            return value.trim();
        }

        // Check if it's a US ZIP code (5 digits, 5+4 with dash, or 9 digits without
        // dash)
        if (trimmed.matches("\\d{5}(-?\\d{4})?") || trimmed.matches("\\d{9}")) {
            return trimmed.substring(0, 5);
        }

        // For values that don't match US ZIP patterns, return trimmed original
        return value.trim();
    }
}
