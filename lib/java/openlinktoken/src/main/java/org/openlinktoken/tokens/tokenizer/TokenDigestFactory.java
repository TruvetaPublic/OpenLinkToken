/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.io.Serializable;
import java.security.NoSuchAlgorithmException;

import org.openlinktoken.crypto.CryptoSuite;

/**
 * Creates token digest implementations from suite or algorithm identifiers.
 */
public final class TokenDigestFactory implements Serializable {
    private static final long serialVersionUID = 1L;


    /**
     * Constructs this factory with no arguments; private visibility keeps it non-instantiable to callers.
     */
    private TokenDigestFactory() {
    }

    /**
     * Creates the digest implementation declared by a crypto suite.
     *
     * @param cryptoSuite the suite selecting the digest
     * @return the selected digest implementation
     */
    public static TokenDigest forSuite(CryptoSuite cryptoSuite) {
        if (cryptoSuite == null) {
            throw new IllegalArgumentException("A valid CryptoSuite is required to select a token digest.");
        }
        try {
            return forAlgorithm(cryptoSuite.getTokenDigestAlgorithm());
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalArgumentException(
                    "Unsupported token digest algorithm '" + cryptoSuite.getTokenDigestAlgorithm() + "'.",
                    error);
        }
    }

    /**
     * Creates a digest implementation from its registered algorithm identifier.
     *
     * @param algorithm the suite-level digest identifier
     * @return the selected digest implementation
     * @throws NoSuchAlgorithmException if the identifier is unsupported
     */
    public static TokenDigest forAlgorithm(String algorithm) throws NoSuchAlgorithmException {
        return switch (algorithm) {
            case CryptoSuite.TOKEN_DIGEST_SHA256 -> new SHA256TokenDigest();
            case CryptoSuite.TOKEN_DIGEST_SHA3_256 -> new SHA3TokenDigest();
            case CryptoSuite.TOKEN_DIGEST_SHAKE256_256 -> new SHAKE256TokenDigest();
            default -> throw new NoSuchAlgorithmException("Unsupported token digest algorithm '" + algorithm + "'.");
        };
    }
}
