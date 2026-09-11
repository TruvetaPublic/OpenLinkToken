/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Collections;
import java.util.List;

import org.apache.commons.codec.binary.Hex;
import org.bouncycastle.crypto.digests.SHAKEDigest;

import org.openlinktoken.crypto.CryptoSuite;
import org.openlinktoken.tokens.Token;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Generates tokens using the digest selected by a crypto suite.
 *
 * <p>
 * The token is generated using the configured digest and is hex encoded. If
 * token transformations are specified, the token is then transformed by those
 * transformers.
 *
 */
public final class SHA256Tokenizer implements Tokenizer {

    private static final long serialVersionUID = 1L;

    /**
     * The empty token value.
     * <p>
     * This is the value returned when the token signature is <code>null</code> or
     * blank.
     */
    public static final String EMPTY = Token.BLANK;
    private final List<TokenTransformer> tokenTransformerList;
    private final CryptoSuite cryptoSuite;

    /**
     * Initializes the tokenizer.
     *
     * @param tokenTransformerList a list of token transformers.
     */
    public SHA256Tokenizer(List<TokenTransformer> tokenTransformerList) {
        this(tokenTransformerList, CryptoSuite.defaultSuite());
    }

    /**
     * Initializes the tokenizer with an explicit crypto suite.
     *
     * @param tokenTransformerList a list of token transformers
     * @param cryptoSuite the suite selecting the token digest
     */
    public SHA256Tokenizer(List<TokenTransformer> tokenTransformerList, CryptoSuite cryptoSuite) {
        this.tokenTransformerList = tokenTransformerList;
        this.cryptoSuite = cryptoSuite;
    }

    /**
     * Generates a token for the given token signature.
     * <p>
     * <code>
     *   Token = Hex(Digest(token-signature))
     * </code>
     * <p>
     * The token is optionally transformed with one or more transformers.
     *
     * @param value the token signature value.
     *
     * @return the token. If the token signature value is <code>null</code> or
     *         blank,
     *         {@link #EMPTY EMPTY} is returned.
     *
     * @throws UnsupportedEncodingException   if the UTF-8 encoding is not supported
     * @throws NoSuchAlgorithmException       if the configured digest algorithm is not supported
     * @throws Exception                      if an error is thrown by a transformer
     */
    public String tokenize(String value) throws Exception {
        if (value == null || value.isBlank()) {
            return EMPTY;
        }
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8.name());

        byte[] hash;
        if ("SHAKE256-256".equals(cryptoSuite.getTokenDigestAlgorithm())) {
            SHAKEDigest digest = new SHAKEDigest(256);
            digest.update(bytes, 0, bytes.length);
            hash = new byte[32];
            digest.doFinal(hash, 0, hash.length);
        } else {
            String digestAlgorithm = switch (cryptoSuite.getTokenDigestAlgorithm()) {
                case "SHA-256" -> "SHA-256";
                case "SHA3-256" -> "SHA3-256";
                default -> throw new NoSuchAlgorithmException(
                        "Unsupported token digest algorithm: " + cryptoSuite.getTokenDigestAlgorithm());
            };
            MessageDigest digest = MessageDigest.getInstance(digestAlgorithm);
            hash = digest.digest(bytes);
        }
        String transformedToken = Hex.encodeHexString(hash);

        for (TokenTransformer tokenTransformer : tokenTransformerList) {
            transformedToken = tokenTransformer.transform(transformedToken);
        }

        return transformedToken;
    }

    /**
     * Returns the transformer list applied after digesting.
     *
     * @return unmodifiable view of the transformer list
     */
    @Override
    public List<TokenTransformer> getTokenTransformerList() {
        return Collections.unmodifiableList(tokenTransformerList);
    }
}
