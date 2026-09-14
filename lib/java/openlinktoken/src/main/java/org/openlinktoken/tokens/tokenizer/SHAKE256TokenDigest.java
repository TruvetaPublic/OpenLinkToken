/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import org.bouncycastle.crypto.digests.SHAKEDigest;

/**
 * Calculates fixed-width SHAKE256 token digests.
 */
public final class SHAKE256TokenDigest implements TokenDigest {
    private static final int OUTPUT_LENGTH_BYTES = 32;

    /**
     * Calculates the first 32 bytes of a SHAKE256 digest.
     *
     * @param value the token-signature bytes
     * @return a 32-byte SHAKE256 digest
     */
    @Override
    public byte[] digest(byte[] value) {
        SHAKEDigest digest = new SHAKEDigest(256);
        digest.update(value, 0, value.length);
        byte[] output = new byte[OUTPUT_LENGTH_BYTES];
        digest.doFinal(output, 0, output.length);
        return output;
    }
}
