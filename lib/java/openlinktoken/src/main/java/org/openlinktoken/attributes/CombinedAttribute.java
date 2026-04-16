/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import java.util.List;

/**
 * Abstract base class for attributes that combine multiple attribute implementations.
 *
 * <p>
 * This class allows for combining multiple attribute implementations where each
 * implementation handles a specific subset of validation and normalization logic.
 * The combined attribute will iterate through all implementations until it finds
 * one that reports the string as valid for validation, and uses the first
 * implementation that can normalize the value for normalization.
 * </p>
 *
 * <p>
 * Subclasses must implement {@link #getAttributeImplementations()} to provide
 * the list of attribute implementations to combine.
 * </p>
 */
public abstract class CombinedAttribute implements SerializableAttribute {

    private static final long serialVersionUID = 1L;

    /**
     * Gets the list of attribute implementations to combine.
     *
     * @return the list of attribute implementations.
     */
    protected abstract List<SerializableAttribute> getAttributeImplementations();

    /**
     * Validates the attribute value by checking if any of the combined
     * implementations consider the value valid.
     *
     * @param value the attribute value to validate.
     * @return true if any implementation validates the value successfully; false otherwise.
     */
    @Override
    public boolean validate(String value) {
        if (value == null) {
            return false;
        }

        return getAttributeImplementations().stream()
                .anyMatch(impl -> impl.validate(value));
    }

    /**
     * Normalizes the attribute value using the first implementation that
     * successfully validates the value.
     *
     * @param value the attribute value to normalize.
     * @return the normalized value from the first validating implementation,
     *         or the original trimmed value if no implementation validates it.
     */
    @Override
    public String normalize(String value) {
        if (value == null) {
            return null;
        }

        for (SerializableAttribute impl : getAttributeImplementations()) {
            if (impl.validate(value)) {
                return impl.normalize(value);
            }
        }

        // If no implementation validates the value, return trimmed original
        return value.trim();
    }
}
