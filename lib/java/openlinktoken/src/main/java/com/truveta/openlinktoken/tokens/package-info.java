/**
 * This package provides the ability to generate tokens.
 *
 * <p>
 * The <code>TokenGenerator</code> is the entry point for most
 * use cases. The <code>TokenGenerator</code> is initialized with
 * the <code>TokenDefinition</code> and <code>TokenTransformer</code>
 * list. The <code>ValidationRules</code> and <code>SHA256Tokenizer</code>
 * are set up at the time of initialization itself.
 *
 * <p>
 * When token generation is requested for a given set of person attributes,
 * a token signature is first calculated using the <code>TokenDefinition</code>
 * provided. The token signature is then passed on to <code>SHA256Tokenizer</code>
 * to get the token. If any token transformers were provided at the time of
 * initialization, those transformation are also applied in <code>SHA256Tokenizer</code>.
 *
 * <p>
 * The <code>TokenGenerator</code> is designed to be state-less. The idea is to
 * create a single instance of it and {@link com.truveta.openlinktoken.tokens.TokenGenerator#getToken getToken}
 * for every person record.
 */
package com.truveta.openlinktoken.tokens;
