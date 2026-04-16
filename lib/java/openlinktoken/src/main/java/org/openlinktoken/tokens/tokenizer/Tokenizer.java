/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.io.Serializable;

/**
 * Interface for tokenizing values into tokens.
 *
 * <p>
 * A tokenizer takes a string value (typically a token signature) and
 * transforms it into a token using various cryptographic or encoding
 * techniques.
 * </p>
 */
public interface Tokenizer extends Serializable {

    /**
     * Generates a token from the given value.
     *
     * @param value the value to tokenize (e.g., a token signature).
     *
     * @return the generated token. Returns a default empty token value
     *         if the input value is null or blank.
     *
     * @throws Exception if an error occurs during tokenization, such as
     *                   unsupported encoding or cryptographic algorithm issues.
     */
    String tokenize(String value) throws Exception;
}
