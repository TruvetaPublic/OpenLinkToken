/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.AttributeLoader;
import org.openlinktoken.tokens.tokenizer.PassthroughTokenizer;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokens.tokenizer.Tokenizer;
import org.openlinktoken.tokentransformer.TokenTransformer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import lombok.Getter;
import lombok.Setter;

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

    private Attribute resolveAttributeInstance(Class<? extends Attribute> attributeClass) {
        Attribute attribute = attributeInstanceMap.get(attributeClass);
        if (attribute != null) {
            return attribute;
        }

        int bestDistance = Integer.MAX_VALUE;
        Attribute bestMatch = null;

        for (Map.Entry<Class<? extends Attribute>, Attribute> entry : attributeInstanceMap.entrySet()) {
            Class<? extends Attribute> baseClass = entry.getKey();
            if (!baseClass.isAssignableFrom(attributeClass)) {
                continue;
            }

            int distance = inheritanceDistance(attributeClass, baseClass);
            if (distance >= 0 && distance < bestDistance) {
                bestDistance = distance;
                bestMatch = entry.getValue();
            }
        }

        if (bestMatch != null) {
            attributeInstanceMap.put(attributeClass, bestMatch);
        }
        return bestMatch;
    }

    private static int inheritanceDistance(Class<?> derivedClass, Class<?> baseClass) {
        int distance = 0;
        Class<?> current = derivedClass;
        while (current != null) {
            if (current.equals(baseClass)) {
                return distance;
            }
            current = current.getSuperclass();
            distance++;
        }
        return -1;
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
        var definition = tokenDefinition.getTokenDefinition(tokenId);
        if (personAttributes == null) {
            throw new IllegalArgumentException("Person attributes cannot be null.");
        }

        var values = new ArrayList<String>(definition.size());

        for (AttributeExpression attributeExpression : definition) {
            if (!personAttributes.containsKey(attributeExpression.getAttributeClass())) {
                return null;
            }

            var attribute = resolveAttributeInstance(attributeExpression.getAttributeClass());
            if (attribute == null) {
                return null;
            }
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
            Attribute attribute = resolveAttributeInstance(entry.getKey());
            if (attribute != null && !attribute.validate(entry.getValue())) {
                response.add(attribute.getName());
            }
        }

        return response;
    }
}
