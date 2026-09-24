/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.validation;

import java.util.Set;

import javax.validation.constraints.NotNull;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.Setter;

/**
 * Rejects attribute values that match a configured invalid value, ignoring case.
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
     *
     * @param value the value to validate
     * @return {@code true} if the value is non-null and is not in the invalid-value set
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
