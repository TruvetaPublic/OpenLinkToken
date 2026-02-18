/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens.tokenizer;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

import org.apache.commons.codec.binary.Hex;

import com.truveta.opentoken.tokens.Token;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

/**
 * Generates token using SHA256 digest.
 *
 * <p>
 * The token is generated using SHA256 digest and is hex encoded.
 * If token transformations are specified, the token is then transformed
 * by those transformers.
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

    /**
     * Initializes the tokenizer.
     * 
     * @param tokenTransformerList a list of token transformers.
     */
    public SHA256Tokenizer(List<TokenTransformer> tokenTransformerList) {
        this.tokenTransformerList = tokenTransformerList;
    }

    /**
     * Generates the token for the given token signature.
     * <p>
     * <code>
     *   Token = Hex(Sha256(token-signature))
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
     * @throws java.io.UnsupportedEncodingException   if the <code>utf-8</code>
     *                                                encoding is not supported.
     * @throws java.security.NoSuchAlgorithmException if the <code>SHA-256</code>
     *                                                algorithm is not supported.
     * @throws java.lang.Exception                    if an error is thrown by the
     *                                                transformer.
     */
    public String tokenize(String value) throws Exception {
        if (value == null || value.isBlank()) {
            return EMPTY;
        }
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8.name());

        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(bytes);
        String transformedToken = Hex.encodeHexString(hash);

        for (TokenTransformer tokenTransformer : tokenTransformerList) {
            transformedToken = tokenTransformer.transform(transformedToken);
        }

        return transformedToken;
    }
}
