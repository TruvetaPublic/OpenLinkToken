/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

import org.apache.commons.codec.binary.Hex;

import org.openlinktoken.crypto.CryptoSuite;
import org.openlinktoken.tokens.Token;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Generates tokens using a digest selected by a crypto suite.
 */
public class CryptoSuiteTokenizer implements Tokenizer {
    private static final long serialVersionUID = 1L;

    /**
     * The empty token value returned for null or blank signatures.
     */
    public static final String EMPTY = Token.BLANK;

    private final List<TokenTransformer> tokenTransformerList;
    private final String cryptoSuiteId;
    private transient TokenDigest tokenDigest;

    /**
     * Creates a tokenizer with the backward-compatible default suite.
     *
     * @param tokenTransformerList a list of token transformers
     */
    public CryptoSuiteTokenizer(List<TokenTransformer> tokenTransformerList) {
        this(tokenTransformerList, CryptoSuite.defaultSuite());
    }

    /**
     * Creates a tokenizer with an explicit crypto suite.
     *
     * @param tokenTransformerList a list of token transformers
     * @param cryptoSuite the suite selecting the token digest
     */
    public CryptoSuiteTokenizer(List<TokenTransformer> tokenTransformerList, CryptoSuite cryptoSuite) {
        this.tokenTransformerList = tokenTransformerList;
        CryptoSuite resolvedCryptoSuite = cryptoSuite == null ? CryptoSuite.defaultSuite() : cryptoSuite;
        this.cryptoSuiteId = resolvedCryptoSuite.getSuiteId();
        this.tokenDigest = TokenDigestFactory.forSuite(resolvedCryptoSuite);
    }

    /**
     * Restores the tokenizer and rebuilds its transient digest implementation.
     *
     * <p>This method returns no value.</p>
     *
     * @param ois the object stream containing the tokenizer state
     * @throws IOException if the digest cannot be reconstructed
     * @throws ClassNotFoundException if a serialized class cannot be resolved
     */
    private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
        ois.defaultReadObject();
        try {
            CryptoSuite resolvedCryptoSuite = this.cryptoSuiteId == null
                    ? CryptoSuite.defaultSuite()
                    : CryptoSuite.fromId(this.cryptoSuiteId);
            this.tokenDigest = TokenDigestFactory.forSuite(resolvedCryptoSuite);
        } catch (IllegalArgumentException e) {
            throw new IOException("Failed to reconstruct token digest", e);
        }
    }

    /**
     * Generates a token for the given token signature.
     *
     * @param value the token signature value
     * @return the hexadecimal digest token after all configured transformations
     * @throws Exception if the digest or a transformer fails
     */
    @Override
    public String tokenize(String value) throws Exception {
        if (value == null || value.isBlank()) {
            return EMPTY;
        }

        String transformedToken = Hex.encodeHexString(tokenDigest.digest(value.getBytes(StandardCharsets.UTF_8)));
        for (TokenTransformer tokenTransformer : tokenTransformerList) {
            transformedToken = tokenTransformer.transform(transformedToken);
        }
        return transformedToken;
    }

    /**
     * Returns the transformer list applied after digesting.
     *
     * <p>This method accepts no arguments.</p>
     *
     * @return an unmodifiable view of the transformer list
     */
    @Override
    public List<TokenTransformer> getTokenTransformerList() {
        return Collections.unmodifiableList(tokenTransformerList);
    }
}
