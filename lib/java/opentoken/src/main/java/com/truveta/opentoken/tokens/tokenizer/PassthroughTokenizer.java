/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens.tokenizer;

import java.util.List;

import com.truveta.opentoken.tokens.Token;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

/**
 * A tokenizer that returns the input value unchanged (passthrough).
 *
 * <p>
 * This tokenizer does not apply any hashing or cryptographic transformation
 * to the input value. It simply returns the input as-is, optionally applying
 * token transformers if provided.
 * </p>
 * 
 * <p>
 * This is useful for scenarios where you want to preserve the original token
 * signature without any cryptographic processing, while still allowing for
 * optional transformations (e.g., encryption).
 * </p>
 */
public final class PassthroughTokenizer implements Tokenizer {

    private static final long serialVersionUID = 1L;

    /**
     * The empty token value.
     * <p>
     * This is the value returned when the token signature is <code>null</code> or
     * blank.
     */
    public static final String EMPTY = Token.BLANK;
    private final List<TokenTransformer> tokenTransformerList;

    /**
     * Initializes the tokenizer.
     * 
     * @param tokenTransformerList a list of token transformers.
     */
    public PassthroughTokenizer(List<TokenTransformer> tokenTransformerList) {
        this.tokenTransformerList = tokenTransformerList;
    }

    /**
     * Returns the input value unchanged (passthrough).
     * <p>
     * <code>
     *   Token = value
     * </code>
     * <p>
     * The token is optionally transformed with one or more transformers.
     * 
     * @param value the token signature value.
     * 
     * @return the token. If the token signature value is <code>null</code> or
     *         blank, {@link #EMPTY EMPTY} is returned.
     * 
     * @throws java.lang.Exception if an error is thrown by the transformer.
     */
    public String tokenize(String value) throws Exception {
        if (value == null || value.isBlank()) {
            return EMPTY;
        }

        String transformedToken = value;

        for (TokenTransformer tokenTransformer : tokenTransformerList) {
            transformedToken = tokenTransformer.transform(transformedToken);
        }

        return transformedToken;
    }
}
