/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.security.NoSuchAlgorithmException;

/**
 * Calculates the raw digest bytes used by suite-aware tokenization.
 */
public interface TokenDigest {

    /**
     * Calculates a digest for UTF-8 token-signature bytes.
     *
     * @param value the token-signature bytes
     * @return the raw digest bytes
     * @throws NoSuchAlgorithmException if the required provider algorithm is unavailable
     */
    byte[] digest(byte[] value) throws NoSuchAlgorithmException;
}
