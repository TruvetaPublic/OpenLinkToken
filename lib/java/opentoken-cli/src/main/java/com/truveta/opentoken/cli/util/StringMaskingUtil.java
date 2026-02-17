/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.util;

/**
 * Utility class for masking sensitive strings in CLI commands.
 * <p>
 * This class provides methods to mask secrets and sensitive data
 * for logging and display purposes.
 */
public final class StringMaskingUtil {

    private static final String NULL_MASK = "<null>";
    private static final String DEFAULT_MASK = "***";

    private StringMaskingUtil() {
        // Utility class; prevent instantiation.
    }

    /**
     * Masks a sensitive string for logging.
     * <p>
     * - Null values are masked as "&lt;null&gt;"
     * - Strings with 3 or fewer characters are masked as "***"
     * - Longer strings show first 3 characters followed by asterisks
     *
     * @param input The string to mask
     * @return The masked string
     */
    public static String maskString(String input) {
        if (input == null) {
            return NULL_MASK;
        }
        if (input.length() <= 3) {
            return DEFAULT_MASK;
        }
        return input.substring(0, 3) + "*".repeat(input.length() - 3);
    }
}
