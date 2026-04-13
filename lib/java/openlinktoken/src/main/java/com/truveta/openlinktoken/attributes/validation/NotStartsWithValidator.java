/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.validation;

import java.util.Set;

import javax.validation.constraints.NotNull;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.Setter;

/**
 * A Validator that asserts that the attribute value does
 * <b>NOT START WITH</b> any of the invalid prefixes.
 */
@AllArgsConstructor
@Getter
@Setter
public final class NotStartsWithValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    @NotNull
    private Set<String> invalidPrefixes;

    /**
     * Validates that the attribute value does not start with any of the invalid
     * prefixes.
     */
    @Override
    public boolean eval(String value) {
        if (value == null) {
            return false;
        }

        return invalidPrefixes.stream().noneMatch(prefix -> value.trim().startsWith(prefix));
    }

}
