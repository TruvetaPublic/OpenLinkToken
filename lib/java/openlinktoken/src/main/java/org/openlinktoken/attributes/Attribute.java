/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

/**
 * A generic interface for attributes.
 *
 * <p>
 * An attribute is a piece of information that can be used to generate a token.
 * </p>
 *
 * <p>
 * An attribute has a name and a list of aliases. The name is the canonical name
 * of the attribute, while the aliases are alternative names that can be used to
 * refer to the attribute.
 * <p>
 *
 * <p>
 * An attribute also has a normalization function that converts the attribute
 * value to a canonical form. This is useful for attributes that have multiple
 * valid representations.
 * </p>
 *
 * <p>
 * An attribute also has a validation function that checks if the attribute
 * value
 * is valid.
 * </p>
 */
public interface Attribute {

    /**
     * Gets the name of the attribute.
     *
     * @return the name of the attribute.
     */
    String getName();

    /**
     * Gets the aliases of the attribute.
     *
     * @return the aliases of the attribute.
     */
    String[] getAliases();

    /**
     * Normalizes the attribute value.
     *
     * @param value the attribute value.
     *
     * @return the normalized attribute value.
     */
    String normalize(String value);

    /**
     * Validates the attribute value.
     *
     * @param value the attribute value.
     *
     * @return <code>true</code> if the attribute value is valid;
     *         <code>false</code> otherwise.
     */
    boolean validate(String value);
}
