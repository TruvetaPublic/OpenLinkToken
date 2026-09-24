/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

/**
 * A <code>No Operation</code> token transformer. No transformation is
 * applied whatsoever.
 */
public class NoOperationTokenTransformer implements TokenTransformer {
    private static final long serialVersionUID = 1L;

    /**
     * No operation token transformer.
     * <p>
     * Does not transform the token in any ways.
     */
    @Override
    public String transform(String token) {
        return token;
    }
}
