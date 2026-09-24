/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import java.util.Set;

import javax.validation.constraints.NotNull;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.Setter;

/**
 * A Validator that asserts that the attribute values is
 * <b>NOT IN</b> the list of invalid values.
 */
@AllArgsConstructor
@Getter
@Setter
public final class NotInValidator implements SerializableAttributeValidator {

    private static final long serialVersionUID = 1L;

    @NotNull
    private Set<String> invalidValues;

    /**
     * Validates that the attribute value is not in the list of invalid values
     * independent of case.
     */
    @Override
    public boolean eval(String value) {
        if (value == null) {
            return false;
        }

        return invalidValues.stream()
                .noneMatch(invalidValue -> invalidValue.equalsIgnoreCase(value));
    }

}
