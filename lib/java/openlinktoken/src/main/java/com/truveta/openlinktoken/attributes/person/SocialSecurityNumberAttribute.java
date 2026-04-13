/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.person;

import java.text.DecimalFormatSymbols;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;

import com.truveta.openlinktoken.attributes.BaseAttribute;
import com.truveta.openlinktoken.attributes.utilities.AttributeUtilities;
import com.truveta.openlinktoken.attributes.validation.NotInValidator;
import com.truveta.openlinktoken.attributes.validation.RegexValidator;

/**
 * Represents the social security number attribute.
 *
 * This class extends BaseAttribute and provides functionality for working with
 * social security number fields. It recognizes "SocialSecurityNumber" and
 * "NationalIdentificationNumber" as valid aliases for this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format (xxx-xx-xxxx).
 *
 * The attribute also performs validation on input values, ensuring they match
 * the following format:
 * - xxx-xx-xxxx
 * - xxxxxxxxx
 */
public class SocialSecurityNumberAttribute extends BaseAttribute {

    private static final String NAME = "SocialSecurityNumber";
    private static final String[] ALIASES = new String[] { NAME, "NationalIdentificationNumber" };
    private static final String DASH = "-";
    private static final String SSN_FORMAT = "%09d";

    private static final int MIN_SSN_LENGTH = 7;
    private static final int SSN_LENGTH = 9;

    private static final char DECIMAL_SEPARATOR = DecimalFormatSymbols.getInstance(Locale.getDefault())
            .getDecimalSeparator();

    /**
     * Regular expression to validate Social Security Numbers (SSNs).
     *
     * Allows:
     * - 7 to 9 digits, optionally followed by a decimal separator and zero(s).
     * - Properly formatted SSNs with or without dashes, ensuring:
     *   - The first three digits are not "000", "666", or in the range "900-999".
     *   - The middle two digits are not "00".
     *   - The last four digits are not "0000".
     */
    private static final String SSN_REGEX = "^(?:\\d{7,9}(\\" + DECIMAL_SEPARATOR + "0*)?)" +
            "|(?:^(?!000|666|9\\d\\d)(\\d{3})-?(?!00)(\\d{2})-?(?!0000)(\\d{4})$)";

    private static final Pattern DIGITS_ONLY_PATTERN = Pattern.compile("\\d+");

    private static final Set<String> INVALID_SSNS = Set.of(
            "111-11-1111",
            "222-22-2222",
            "333-33-3333",
            "444-44-4444",
            "555-55-5555",
            "777-77-7777",
            "888-88-8888",

            // Common placeholder SSNs sorted
            "001-23-4567",
            "009-99-9999",
            "010-10-1010",
            "012-34-5678",
            "087-65-4321",
            "098-76-5432",
            "099-99-9999",
            "111-22-3333",
            "121-21-2121",
            "123-45-6789",
            "123-45-9999");

    public SocialSecurityNumberAttribute() {
        super(List.of(
                new NotInValidator(INVALID_SSNS),
                new RegexValidator(SSN_REGEX)));
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
     * Validates the social security number value.
     * This method overrides the validate method from BaseAttribute
     * to ensure that the value is normalized before validation.
     */
    @Override
    public boolean validate(String value) {
        return super.validate(normalize(value)); // Validate normalized SSN
    }

    /**
     * Normalize the social security number value. Remove any dashes and format the
     * value as xxx-xx-xxxx. If not possible return the original but trimmed value.
     *
     * @param originalValue the social security number value.
     */
    @Override
    public String normalize(String originalValue) {

        if (originalValue == null || originalValue.isEmpty()) {
            return originalValue;
        }

        // Remove any whitespace
        String trimmedValue = AttributeUtilities.WHITESPACE.matcher(originalValue.trim()).replaceAll(StringUtils.EMPTY);

        // Remove any dashes for now
        String normalizedValue = trimmedValue.replace(DASH, StringUtils.EMPTY);

        // Remove decimal point/separator and all following numbers if present
        int decimalIndex = normalizedValue.indexOf(DECIMAL_SEPARATOR);
        if (decimalIndex != -1) {
            normalizedValue = normalizedValue.substring(0, decimalIndex);
        }

        // Check if the string contains only digits
        if (!DIGITS_ONLY_PATTERN.matcher(normalizedValue).matches()) {
            return originalValue; // Return original value if it contains non-numeric characters
        }

        if (normalizedValue.length() < MIN_SSN_LENGTH || normalizedValue.length() > SSN_LENGTH) {
            return originalValue; // Invalid length for SSN
        }

        normalizedValue = padWithZeros(normalizedValue);

        return formatWithDashes(normalizedValue);
    }

    // If SSN is between 7-8 digits, pad with leading zeros to reach 9 digits
    // Examples:
    // "1234567" -> "001234567"
    // "12345678" -> "012345678"
    private String padWithZeros(String ssn) {
        if (ssn.length() >= MIN_SSN_LENGTH && ssn.length() < SSN_LENGTH) {
            ssn = String.format(SSN_FORMAT, Long.parseLong(ssn));
        }
        return ssn;
    }

    /**
     * Takes a 9-digit SSN and adds dashes in the right places.
     *
     * Takes: "123456789"
     * Returns: "123-45-6789"
     *
     * SSN parts:
     * - First 3 digits: Area number
     * - Middle 2 digits: Group number
     * - Last 4 digits: Serial number
     */
    private String formatWithDashes(String value) {
        String areaNumber = value.substring(0, 3);
        String groupNumber = value.substring(3, 5);
        String serialNumber = value.substring(5);
        value = String.join(DASH,
                areaNumber,
                groupNumber,
                serialNumber);
        return value;
    }
}
