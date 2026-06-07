/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import java.io.Serializable;

/**
 * A generic interface for the token transformer.
 */
public interface TokenTransformer extends Serializable {
    /**
     * Transforms the token using a token transformation rule/strategy.
     *
     * @param token the token to be transformed.
     *
     * @return the transformed token.
     *
     * @throws Exception error encountered while transforming the token.
     */
    String transform(String token) throws Exception;
}
