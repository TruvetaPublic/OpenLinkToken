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
import org.openlinktoken.attributes.FieldRegistry;
import org.openlinktoken.tokens.tokenizer.PassthroughTokenizer;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokens.tokenizer.Tokenizer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Generates token signatures and transforms them into tokens.
 *
 * <p>The generator supports the legacy attribute-class API and the preferred field-ID API.
 * Inference providers may supply pre-hashed signatures; those signatures bypass the hash
 * transformer while still receiving any remaining transformations.
 */
@Getter
@Setter
public class TokenGenerator implements Serializable {
    private static final long serialVersionUID = 1L;
    private static final transient Logger logger = LoggerFactory.getLogger(TokenGenerator.class);

    private Tokenizer tokenizer;
    private BaseTokenDefinition tokenDefinition;

    private Map<Class<? extends Attribute>, Attribute> attributeInstanceMap;
    private FieldRegistry fieldRegistry;

    private static final Optional<InferenceSignatureProvider> PROVIDER =
            ServiceLoader.load(InferenceSignatureProvider.class).findFirst();

    /**
     * Returns the service-loaded inference provider, if one was discovered at class initialization.
     */
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
        this.fieldRegistry = FieldRegistry.createDefault();
    }

    /**
     * Initializes the token generator with a custom field registry.
     *
     * @param tokenDefinition the token definition.
     * @param tokenizer       the tokenizer implementation.
     * @param fieldRegistry   custom field registry for field-ID-based lookups.
     */
    public TokenGenerator(BaseTokenDefinition tokenDefinition, Tokenizer tokenizer, FieldRegistry fieldRegistry) {
        this.tokenDefinition = tokenDefinition;
        this.attributeInstanceMap = new HashMap<>();
        AttributeLoader.load().forEach(attribute -> attributeInstanceMap.put(attribute.getClass(), attribute));
        this.tokenizer = tokenizer;
        this.fieldRegistry = fieldRegistry;
    }

    /**
     * Gets a token signature for a token identifier using attribute classes.
     *
     * <p>If an enabled inference provider owns the identifier, the provider generates the
     * signature. Otherwise, the configured token definition resolves and normalizes each
     * required attribute, recording invalid attributes in {@code result}.
     *
     * @param tokenId          the token identifier
     * @param personAttributes the person attributes keyed by attribute class
     * @param result           the result object that receives invalid attribute names
     *
     * @return the normalized token signature, or {@code null} when required data is missing
     *         or invalid
     */
    @Deprecated(since = "2.1.0", forRemoval = false)
    protected String getTokenSignature(String tokenId, Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result) {
        if (personAttributes == null) {
            throw new IllegalArgumentException("Person attributes cannot be null.");
        }
        if (hasActiveInferenceProvider(tokenId)) {
            return getInferenceSignature(tokenId, toFieldIdMap(personAttributes));
        }

        var definition = tokenDefinition.getTokenDefinition(tokenId);
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

    /**
     * Generates tokens for every configured identifier except the supplied exclusions.
     *
     * @param personAttributes the person attributes keyed by attribute class
     * @param excludedTokenIds token identifiers to skip
     * @return generated tokens and any invalid attributes encountered
     */
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
     * {@code "ML1-R0"}, {@code "ML1-R1"}, …
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
     * @param tokenId   the token identifier (e.g. {@code "ML1"})
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
     * @deprecated Use {@link #getAllTokenSignaturesViaFieldId(Map)} instead.
     */
    @Deprecated(since = "2.1.0", forRemoval = false)
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
    @Deprecated(since = "2.1.0", forRemoval = false)
    protected String getToken(String tokenId, Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result)
            throws TokenGenerationException {
        var signature = getTokenSignature(tokenId, personAttributes, result);
        logger.debug("Token signature for token id {}: {}", tokenId, signature);

        return tokenizeSignature(tokenId, signature, result);
    }

    /**
     * Store a pre-hashed token value, applying only non-hash transformers (e.g. encryption).
     *
     * <p>Use for tokens that are already hashed (e.g. ML1 HMAC rotation values).
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

    /**
     * Keeps encryption and other post-hash transformations while preventing a pre-hashed value
     * from being hashed again.
     */
    private List<TokenTransformer> encryptOnlyTransformers() {
        return tokenizer.getTokenTransformerList().stream()
                .filter(t -> !(t instanceof HashTokenTransformer))
                .toList();
    }

    /**
     * Checks whether the discovered provider owns this token and is enabled for use.
     */
    private boolean hasActiveInferenceProvider(String tokenId) {
        Optional<InferenceSignatureProvider> provider = findProvider();
        return provider.isPresent() && provider.get().getTokenId().equals(tokenId) && provider.get().isEnabled();
    }

    /**
     * Delegates signature generation to the active provider while converting provider failures
     * into a missing signature so normal token generation can continue.
     */
    private String getInferenceSignature(String tokenId, Map<String, String> personAttributes) {
        Optional<InferenceSignatureProvider> provider = findProvider();
        if (!provider.isPresent() || !provider.get().getTokenId().equals(tokenId) || !provider.get().isEnabled()) {
            return null;
        }
        try {
            return provider.get().generateSignature(personAttributes);
        } catch (Exception e) {
            logger.error("Error generating token signature for token id: {}", tokenId, e);
            return null;
        }
    }

    /**
     * Applies the appropriate tokenizer and records blank output for the originating token rule.
     */
    private String tokenizeSignature(String tokenId, String signature, TokenGeneratorResult result)
            throws TokenGenerationException {
        try {
            String token = hasActiveInferenceProvider(tokenId)
                    ? new PassthroughTokenizer(encryptOnlyTransformers()).tokenize(signature)
                    : tokenizer.tokenize(signature);
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
     * Adapts the legacy class-keyed input to the field-keyed form used by inference providers.
     */
    private Map<String, String> toFieldIdMap(Map<Class<? extends Attribute>, String> personAttributes) {
        var fields = new HashMap<String, String>();
        for (Map.Entry<Class<? extends Attribute>, String> entry : personAttributes.entrySet()) {
            var attribute = attributeInstanceMap.get(entry.getKey());
            if (attribute != null) {
                fields.put(attribute.getName(), entry.getValue());
            }
        }
        return fields;
    }

    /**
     * Get the tokens for all token/rule identifiers.
     *
     * @param personAttributes the person attributes map, keyed by attribute class.
     *
     * @return A {@link TokenGeneratorResult} object containing the tokens and
     *         invalid attributes.
     * @deprecated Use {@link #getAllTokensViaFieldId(Map)} with a field-ID-keyed map instead.
     */
    @Deprecated(since = "2.1.0", forRemoval = false)
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
     * @param personAttributes the person attributes map, keyed by attribute class.
     *
     * @return A set of invalid person attribute names.
     * @deprecated Use field-ID-keyed person attributes with {@link #getAllTokensViaFieldId(Map)} instead.
     */
    @Deprecated(since = "2.1.0", forRemoval = false)
    public Set<String> getInvalidPersonAttributes(Map<Class<? extends Attribute>, String> personAttributes) {
        var response = new HashSet<String>();

        for (Map.Entry<Class<? extends Attribute>, String> entry : personAttributes.entrySet()) {
            if (!attributeInstanceMap.get(entry.getKey()).validate(entry.getValue())) {
                response.add(attributeInstanceMap.get(entry.getKey()).getName());
            }
        }

        return response;
    }

    // ===== Primary API =====

    /**
     * Get the token signature for a given token identifier.
     *
     * @param tokenId          the token identifier.
     * @param personAttributes person attributes keyed by field ID (e.g., "LastName" → "Smith").
     * @param result           the token generator result.
     *
     * @return the token signature, or null if required fields are missing or invalid.
     */
    protected String getTokenSignatureViaFieldId(String tokenId, Map<String, String> personAttributes,
            TokenGeneratorResult result) {
        if (personAttributes == null) {
            throw new IllegalArgumentException("Person attributes cannot be null.");
        }
        if (hasActiveInferenceProvider(tokenId)) {
            return getInferenceSignature(tokenId, personAttributes);
        }

        var definition = tokenDefinition.getTokenDefinition(tokenId);
        if (definition == null || definition.isEmpty()) {
            return null;
        }

        var values = new ArrayList<String>(definition.size());

        for (AttributeExpression attributeExpression : definition) {
            String resolvedFieldId = resolveFieldId(attributeExpression);
            if (resolvedFieldId == null || !personAttributes.containsKey(resolvedFieldId)) {
                return null;
            }

            var attribute = resolveAttribute(attributeExpression, resolvedFieldId);
            if (attribute == null) {
                return null;
            }

            String attributeValue = personAttributes.get(resolvedFieldId);
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

    /**
     * Get the tokens for all token/rule identifiers.
     *
     * <p>
     * This is the preferred API. It natively supports multiple fields sharing the same
     * attribute type (e.g., "MotherLastName" and "FatherLastName" both backed by StringAttribute).
     *
     * @param personAttributes person attributes keyed by field ID (e.g., "LastName" → "Smith").
     *
     * @return A {@link TokenGeneratorResult} object containing the tokens and invalid attributes.
     */
    public TokenGeneratorResult getAllTokensViaFieldId(Map<String, String> personAttributes) {
        TokenGeneratorResult result = new TokenGeneratorResult();

        for (String tokenId : tokenDefinition.getTokenIdentifiers()) {
            try {
                var definition = tokenDefinition.getTokenDefinition(tokenId);
                if ((definition == null || definition.isEmpty()) && !hasActiveInferenceProvider(tokenId)) {
                    continue;
                }
                var signature = getTokenSignatureViaFieldId(tokenId, personAttributes, result);
                logger.debug("Token signature for token id {}: {}", tokenId, signature);
                String token = tokenizeSignature(tokenId, signature, result);
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
     * Get the token signatures for all token/rule identifiers. Mostly useful for debugging.
     *
     * @param personAttributes person attributes keyed by field ID.
     *
     * @return A map of token/rule identifier to the token signature.
     */
    public Map<String, String> getAllTokenSignaturesViaFieldId(Map<String, String> personAttributes) {
        var signatures = new HashMap<String, String>();
        for (String tokenId : tokenDefinition.getTokenIdentifiers()) {
            try {
                var signature = getTokenSignatureViaFieldId(tokenId, personAttributes, new TokenGeneratorResult());
                if (signature != null) {
                    signatures.put(tokenId, signature);
                }
            } catch (Exception e) {
                logger.error("Error generating token signature for token id: " + tokenId, e);
            }
        }
        return signatures;
    }

    /**
     * Resolves an expression's explicit field ID, retaining the attribute-name fallback for
     * definitions created through the legacy class-based API.
     */
    private String resolveFieldId(AttributeExpression expression) {
        if (expression.getFieldId() != null) {
            return expression.getFieldId();
        }
        // Legacy fallback: derive field ID from attribute class name
        var attribute = attributeInstanceMap.get(expression.getAttributeClass());
        return attribute != null ? attribute.getName() : null;
    }

    /**
     * Resolves the attribute registered for a field, falling back to the expression's class
     * when the custom field registry has no entry.
     */
    private Attribute resolveAttribute(AttributeExpression expression, String resolvedFieldId) {
        // Try field registry first
        var fromRegistry = fieldRegistry.getAttribute(resolvedFieldId);
        if (fromRegistry.isPresent()) {
            return fromRegistry.get();
        }
        // Fallback to class-based lookup
        return attributeInstanceMap.get(expression.getAttributeClass());
    }
}
