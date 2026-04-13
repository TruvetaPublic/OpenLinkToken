/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import java.util.List;

import javax.validation.constraints.NotNull;

import com.truveta.openlinktoken.attributes.BaseAttribute;
import com.truveta.openlinktoken.attributes.utilities.AttributeUtilities;
import com.truveta.openlinktoken.attributes.validation.NotInValidator;
import com.truveta.openlinktoken.attributes.validation.RegexValidator;

/**
 * Represents the last name of a person.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * last name fields. It recognizes "LastName" and "Surname" as valid aliases for
 * this attribute type.
 *
 * The attribute normalizes values by removing diacritics, generational suffixes,
 * and non-alphabetic characters. It validates that names are either:
 * - Longer than 2 characters, or
 * - Exactly 2 characters containing at least one vowel (including names with two vowels), or
 * - The specific last name "Ng"
 */
public class LastNameAttribute extends BaseAttribute {

    private static final String NAME = "LastName";
    private static final String[] ALIASES = new String[] { NAME, "Surname" };

    /**
     * Regular expression pattern for validating last names.
     *
     * This pattern matches:
     *  - Any name with 3 or more characters (including spaces within)
     *  - 2-character names with at least one vowel (consonant+vowel, vowel+consonant, or two vowels)
     *  - The special case "Ng" (case-insensitive)
     *  - Allows optional leading and trailing whitespace
     *
     * Breakdown of the regex:
     *   ^\s*                                 Start of string, optional leading whitespace
     *   (?:                                  Start of non-capturing group:
     *     (?:.{3,})                          Any name with 3+ characters
     *     |                                  OR
     *     (?:[^aeiouAEIOU\s][aeiouAEIOU])    2-char: consonant + vowel (no spaces)
     *     |                                  OR
     *     (?:[aeiouAEIOU][^aeiouAEIOU\s])    2-char: vowel + consonant (no spaces)
     *     |                                  OR
     *     (?:[aeiouAEIOU]{2})                2-char: two vowels (no spaces)
     *     |                                  OR
     *     (?:[Nn][Gg])                       Special case: "Ng" (case-insensitive)
     *   )
     *   \s*$                                 Optional trailing whitespace, end of string
     */
    private static final @NotNull String LAST_NAME_REGEX = "^\\s*(?:(?:.{3,})|(?:[^aeiouAEIOU\\s][aeiouAEIOU])|(?:[aeiouAEIOU][^aeiouAEIOU\\s])|(?:[aeiouAEIOU]{2})|(?:[Nn][Gg]))\\s*$";

    private final RegexValidator regexValidator;

    public LastNameAttribute() {
        super(List.of(
                new NotInValidator(
                        AttributeUtilities.COMMON_PLACEHOLDER_NAMES)));
        this.regexValidator = new RegexValidator(LAST_NAME_REGEX);
    }

    @Override
    public boolean validate(String value) {
        if (value == null) {
            return false;
        }

        // First, check placeholder values on the ORIGINAL value using built-in validators
        // This ensures "N/A", "<masked>", etc. are properly rejected
        if (!super.validate(value)) {
            return false;
        }

        // Normalize the value for pattern matching
        // This ensures that validate(normalize(x)) == validate(normalize(normalize(x)))
        String normalizedValue = normalize(value);

        // Reject single letters after normalization
        if (normalizedValue.length() == 1) {
            return false;
        }

        // Check that normalized value is not a placeholder
        // This ensures idempotency: values like "TEST16" normalize to "TEST" which is a placeholder
        if (!super.validate(normalizedValue)) {
            return false;
        }

        // Validate the normalized value against the regex pattern
        // Use the pre-created regex validator instance to avoid creating new instances on each call
        return regexValidator.eval(normalizedValue);
    }

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

    @Override
    public String normalize(String value) {
        String normalizedValue = AttributeUtilities.normalizeDiacritics(value);

        String valueWithoutSuffix = AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN.matcher(normalizedValue)
                .replaceAll("");

        // if the generational suffix removal doesn't result in an empty string,
        // continue with the value without suffix, otherwise use the value with suffix
        // as last name
        if (!valueWithoutSuffix.isEmpty()) {
            normalizedValue = valueWithoutSuffix;
        }

        // remove generational suffix

        normalizedValue = AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN.matcher(normalizedValue).replaceAll("");

        // remove dashes, spaces and other non-alphanumeric characters
        normalizedValue = AttributeUtilities.NON_ALPHABETIC_PATTERN.matcher(normalizedValue).replaceAll("");

        return normalizedValue;
    }
}
