/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Calculates SHA3-256 token digests.
 */
public final class SHA3TokenDigest implements TokenDigest {

    /**
     * Calculates a SHA3-256 digest.
     *
     * @param value the token-signature bytes
     * @return the SHA3-256 digest
     * @throws NoSuchAlgorithmException if SHA3-256 is unavailable
     */
    @Override
    public byte[] digest(byte[] value) throws NoSuchAlgorithmException {
        return MessageDigest.getInstance(CryptoSuite.TOKEN_DIGEST_SHA3_256).digest(value);
    }
}
