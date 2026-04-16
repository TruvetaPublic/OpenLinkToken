/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import java.util.regex.Pattern;
import javax.validation.constraints.NotNull;

import lombok.Getter;
import lombok.Setter;

/**
 * A Validator that is designed for validating with regex expressions.
 */
@Getter
@Setter
public final class RegexValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    private final Pattern compiledPattern;

    public RegexValidator(@NotNull String pattern) {
        this.compiledPattern = Pattern.compile(pattern);
    }

    /**
     * Validates that the value matches the regex pattern.
     */
    @Override
    public boolean eval(String value) {
        return value != null && compiledPattern.matcher(value).matches();
    }
}
