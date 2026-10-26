/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Calculates SHA-256 token digests.
 */
public final class SHA256TokenDigest implements TokenDigest {
    private static final long serialVersionUID = 1L;

    /**
     * Calculates a SHA-256 digest.
     *
     * @param value the token-signature bytes
     * @return the SHA-256 digest
     * @throws NoSuchAlgorithmException if SHA-256 is unavailable
     */
    @Override
    public byte[] digest(byte[] value) throws NoSuchAlgorithmException {
        return MessageDigest.getInstance(CryptoSuite.TOKEN_DIGEST_SHA256).digest(value);
    }
}
