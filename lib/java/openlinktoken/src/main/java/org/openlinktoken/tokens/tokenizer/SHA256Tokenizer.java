/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens.tokenizer;

import java.util.List;

import org.openlinktoken.crypto.CryptoSuite;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Backward-compatible name for the suite-aware tokenizer.
 */
public final class SHA256Tokenizer extends CryptoSuiteTokenizer {

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
        super(tokenTransformerList, cryptoSuite);
    }
}
