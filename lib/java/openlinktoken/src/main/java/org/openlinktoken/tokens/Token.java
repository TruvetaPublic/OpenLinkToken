/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.io.Serializable;
import java.util.ArrayList;
import org.openlinktoken.attributes.AttributeExpression;

/**
 * A token is a collection of attribute expressions that are concatenated
 * together to get the token signature
 * and a unique identifier.
 */
public interface Token extends Serializable {

    /**
     * Represents the value for tokens with invalid or missing data.
     * This constant is a placeholder for cases where a token is either
     * not provided or contains invalid information.
     */
    public static final String BLANK = "0000000000000000000000000000000000000000000000000000000000000000";

    /**
     * Get the unique identifier for the token.
     *
     * @return the unique identifier for the token
     */
    String getIdentifier();

    /**
     * Get the list of attribute expressions that define the token.
     *
     * @return the list of attribute expressions that define the token
     */
    ArrayList<AttributeExpression> getDefinition();
}
