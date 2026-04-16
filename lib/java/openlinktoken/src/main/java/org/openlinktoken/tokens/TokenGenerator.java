/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.ServiceLoader;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import lombok.Getter;
import lombok.Setter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.AttributeLoader;
import org.openlinktoken.tokens.tokenizer.PassthroughTokenizer;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokens.tokenizer.Tokenizer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Generates both the token signature and the token itself.
 */
@Getter
@Setter
public class TokenGenerator implements Serializable {
    private static final long serialVersionUID = 1L;
    private static final transient Logger logger = LoggerFactory.getLogger(TokenGenerator.class);

    private Tokenizer tokenizer;
    private BaseTokenDefinition tokenDefinition;

    private Map<Class<? extends Attribute>, Attribute> attributeInstanceMap;

    private static final Optional<InferenceSignatureProvider> PROVIDER =
            ServiceLoader.load(InferenceSignatureProvider.class).findFirst();

    private static Optional<InferenceSignatureProvider> findProvider() {
        return PROVIDER;
    }

    /**
     * Initializes the token generator.
     *
     * @param tokenDefinition      the token definition.
     * @param tokenTransformerList a list of token transformers.
     * @deprecated Use {@link #TokenGenerator(BaseTokenDefinition, Tokenizer)} instead.
     *             This constructor will be removed in a future release.
     */
    @Deprecated(since = "1.12.0", forRemoval = true)
    public TokenGenerator(BaseTokenDefinition tokenDefinition, List<TokenTransformer> tokenTransformerList) {
        this(tokenDefinition, new SHA256Tokenizer(tokenTransformerList));
    }

    /**
     * Initializes the token generator with an explicit tokenizer.
     *
     * @param tokenDefinition      the token definition.
     * @param tokenizer            optional tokenizer implementation. Use
     *                             {@link PassthroughTokenizer} for plain mode.
     */
    public TokenGenerator(BaseTokenDefinition tokenDefinition, Tokenizer tokenizer) {
        this.tokenDefinition = tokenDefinition;
        this.attributeInstanceMap = new HashMap<>();
        AttributeLoader.load().forEach(attribute -> attributeInstanceMap.put(attribute.getClass(), attribute));
        this.tokenizer = tokenizer;
    }

    /*
     * Get the token signature for a given token identifier. Populates the
     * invalidAttributes list in the result object with the attributes that are
     * invalid.
     *
     * @param tokenId the token identifier.
     *
     * @param personAttributes The person attributes. It is a map of the person
     * attributes.
     *
     * @param result the token generator result.
     *
     * @return the token signature using the token definition for the given token
     * identifier.
     */
    protected String getTokenSignature(String tokenId, Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result) {
        Optional<InferenceSignatureProvider> provider = findProvider();
        if (provider.isPresent() && provider.get().getTokenId().equals(tokenId) && provider.get().isEnabled()) {
            try {
                return provider.get().generateSignature(personAttributes);
            } catch (Exception e) {
                logger.error("Error generating token signature for token id: {}", tokenId, e);
                return null;
            }
        }

        var definition = tokenDefinition.getTokenDefinition(tokenId);
        if (personAttributes == null) {
            throw new IllegalArgumentException("Person attributes cannot be null.");
        }
        if (definition == null) {
            return null;
        }

        var values = new ArrayList<String>(definition.size());

        for (AttributeExpression attributeExpression : definition) {
            if (!personAttributes.containsKey(attributeExpression.getAttributeClass())) {
                return null;
            }

            var attribute = attributeInstanceMap.get(attributeExpression.getAttributeClass());
            String attributeValue = personAttributes.get(attributeExpression.getAttributeClass());
            if (!attribute.validate(attributeValue)) {
                result.getInvalidAttributes().add(attribute.getName());
                return null;
            }

            attributeValue = attribute.normalize(attributeValue);

            try {
                attributeValue = attributeExpression.getEffectiveValue(attributeValue);
                values.add(attributeValue);
            } catch (IllegalArgumentException e) {
                logger.error(e.getMessage());
                return null;
            }

        }

        return Stream.of(values.toArray(new String[0])).filter(s -> null != s && !s.isBlank())
                .collect(Collectors.joining("|"));
    }

    public TokenGeneratorResult generateTokensExcluding(
            Map<Class<? extends Attribute>, String> personAttributes,
            Set<String> excludedTokenIds) {
        TokenGeneratorResult result = new TokenGeneratorResult();

        for (String tokenId : tokenDefinition.getTokenIdentifiers()) {
            if (excludedTokenIds.contains(tokenId)) {
                continue;
            }
            try {
                var token = getToken(tokenId, personAttributes, result);
                if (token != null) {
                    result.getTokens().put(tokenId, token);
                }
            } catch (Exception e) {
                logger.error("Error generating token for token id: " + tokenId, e);
            }
        }

        return result;
    }

    /**
     * Apply pre-computed embedding-derived tokens to the result.
     *
     * <p>Stores each token string under the key {@code tokenIdPrefix + i}, e.g.
     * {@code "T6-R0"}, {@code "T6-R1"}, …
     *
     * @param result         the result to update
     * @param tokenIdPrefix  prefix for the derived token keys
     * @param tokenStrings   pre-computed token strings from the embedding transformer
     */
    public void applyEmbeddingDerivedTokens(
            TokenGeneratorResult result,
            String tokenIdPrefix,
            List<String> tokenStrings) {
        for (int i = 0; i < tokenStrings.size(); i++) {
            result.getTokens().put(tokenIdPrefix + i, tokenStrings.get(i));
        }
    }

    /**
     * Apply a pre-computed inference signature as a token in the result.
     *
     * @param result    the token generator result to update
     * @param tokenId   the token identifier (e.g. {@code "T6"})
     * @param signature the pre-computed hex-encoded signature string
     */
    public void applyPrecomputedSignature(TokenGeneratorResult result, String tokenId, String signature) {
        try {
            String token = tokenizer.tokenize(signature);
            result.getTokens().put(tokenId, token);
            if (Token.BLANK.equals(token)) {
                result.getBlankTokensByRule().add(tokenId);
            }
        } catch (Exception e) {
            logger.error("Error generating token for token id: " + tokenId, e);
            result.getTokens().put(tokenId, Token.BLANK);
            result.getBlankTokensByRule().add(tokenId);
        }
    }

    /**
     * Get the token signatures for all token/rule identifiers. This is mostly a
     * debug/logging/test method.
     *
     * @param personAttributes the person attributes map.
     *
     * @return A map of token/rule identifier to the token signature.
     */
    public Map<String, String> getAllTokenSignatures(Map<Class<? extends Attribute>, String> personAttributes) {
        var signatures = new HashMap<String, String>();
        for (String tokenId : tokenDefinition.getTokenIdentifiers()) {
            try {
                var signature = getTokenSignature(tokenId, personAttributes, new TokenGeneratorResult());
                if (signature != null) {
                    signatures.put(tokenId, signature);
                }
            } catch (Exception e) {
                logger.error("Error generating token signature for token id: " + tokenId, e);
            }
        }
        return signatures;
    }

    /*
     * Get token for a given token identifier.
     *
     * @param tokenId the token identifier.
     *
     * @param personAttributes the person attributes map.
     *
     * @param result the token generator result.
     *
     * @return the token using the token definition for the given token identifier.
     *
     * @throws TokenGenerationException in case of failure to generate the token.
     */
    protected String getToken(String tokenId, Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result)
            throws TokenGenerationException {
        var signature = getTokenSignature(tokenId, personAttributes, result);
        logger.debug("Token signature for token id {}: {}", tokenId, signature);

        // Tokens from inference providers (e.g. T6) are pre-hashed; skip SHA-256 re-hashing
        // but still apply any remaining transformers (e.g. encryption) via PassthroughTokenizer.
        Optional<InferenceSignatureProvider> provider = findProvider();
        if (provider.isPresent() && provider.get().getTokenId().equals(tokenId) && provider.get().isEnabled()) {
            if (signature == null || Token.BLANK.equals(signature)) {
                result.getBlankTokensByRule().add(tokenId);
                return Token.BLANK;
            }
            try {
                return new PassthroughTokenizer(encryptOnlyTransformers()).tokenize(signature);
            } catch (Exception e) {
                logger.error("Error applying transformers to inference token for token id: " + tokenId, e);
                throw new TokenGenerationException("Error applying transformers to inference token", e);
            }
        }

        try {
            String token = tokenizer.tokenize(signature);
            // Track blank tokens by rule
            if (Token.BLANK.equals(token)) {
                result.getBlankTokensByRule().add(tokenId);
            }
            return token;
        } catch (Exception e) {
            logger.error("Error generating token for token id: " + tokenId, e);
            throw new TokenGenerationException("Error generating token", e);
        }
    }

    /**
     * Store a pre-hashed token value, applying only non-hash transformers (e.g. encryption).
     *
     * <p>Use for tokens that are already hashed (e.g. T6 HMAC rotation values).
     * {@link HashTokenTransformer} is skipped to avoid re-hashing; all other
     * transformers (e.g. {@code EncryptTokenTransformer}) are still applied via
     * {@link PassthroughTokenizer}.
     *
     * @param result     the token generator result to update
     * @param tokenId    the token identifier key to store the result under
     * @param tokenValue the pre-hashed token value, or {@code null}/blank to record blank
     */
    public void storeRawToken(TokenGeneratorResult result, String tokenId, String tokenValue) {
        if (tokenValue == null || Token.BLANK.equals(tokenValue)) {
            result.getTokens().put(tokenId, Token.BLANK);
            result.getBlankTokensByRule().add(tokenId);
            return;
        }
        try {
            String token = new PassthroughTokenizer(encryptOnlyTransformers()).tokenize(tokenValue);
            result.getTokens().put(tokenId, token);
            if (Token.BLANK.equals(token)) {
                result.getBlankTokensByRule().add(tokenId);
            }
        } catch (Exception e) {
            logger.error("Error storing raw token for token id: " + tokenId, e);
            result.getTokens().put(tokenId, Token.BLANK);
            result.getBlankTokensByRule().add(tokenId);
        }
    }

    private List<TokenTransformer> encryptOnlyTransformers() {
        if (tokenizer instanceof SHA256Tokenizer sha256) {
            return sha256.getTokenTransformerList().stream()
                    .filter(t -> !(t instanceof HashTokenTransformer))
                    .toList();
        }
        return List.of();
    }

    /**
     * Get the tokens for all token/rule identifiers.
     *
     * @param personAttributes the person attributes map.
     *
     * @return A {@link TokenGeneratorResult} object containing the tokens and
     *         invalid attributes.
     */
    public TokenGeneratorResult getAllTokens(Map<Class<? extends Attribute>, String> personAttributes) {
        TokenGeneratorResult result = new TokenGeneratorResult();

        for (String tokenId : tokenDefinition.getTokenIdentifiers()) {
            try {
                var token = getToken(tokenId, personAttributes, result);
                if (token != null) {
                    result.getTokens().put(tokenId, token);
                }
            } catch (Exception e) {
                logger.error("Error generating token for token id: " + tokenId, e);
            }
        }

        return result;
    }

    /**
     * Get invalid person attribute names.
     *
     * @param personAttributes the person attributes map.
     *
     * @return A set of invalid person attribute names.
     */
    public Set<String> getInvalidPersonAttributes(Map<Class<? extends Attribute>, String> personAttributes) {
        var response = new HashSet<String>();

        for (Map.Entry<Class<? extends Attribute>, String> entry : personAttributes.entrySet()) {
            if (!attributeInstanceMap.get(entry.getKey()).validate(entry.getValue())) {
                response.add(attributeInstanceMap.get(entry.getKey()).getName());
            }
        }

        return response;
    }
}
