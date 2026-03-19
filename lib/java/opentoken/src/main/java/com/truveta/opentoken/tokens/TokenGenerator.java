/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import lombok.Getter;
import lombok.Setter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.attributes.AttributeExpression;
import com.truveta.opentoken.attributes.AttributeLoader;
import com.truveta.opentoken.attributes.person.BirthDateAttribute;
import com.truveta.opentoken.attributes.person.FirstNameAttribute;
import com.truveta.opentoken.attributes.person.LastNameAttribute;
import com.truveta.opentoken.attributes.person.PostalCodeAttribute;
import com.truveta.opentoken.attributes.person.SexAttribute;
import com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer;
import com.truveta.opentoken.tokens.tokenizer.Tokenizer;
import com.truveta.opentoken.tokens.tokenizer.PassthroughTokenizer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

/**
 * Generates both the token signature and the token itself.
 */
@Getter
@Setter
public class TokenGenerator implements Serializable {
    private static final long serialVersionUID = 1L;
    private static final transient Logger logger = LoggerFactory.getLogger(TokenGenerator.class);
    private static final String T6_RULE_ID = "T6";

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
        if (T6_RULE_ID.equals(tokenId)) {
            return getT6Signature(personAttributes, result);
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

    private String getT6Signature(Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result) {
        if (!T6InferenceConfig.isEnabled()) {
            return null;
        }

        String payloadJson = buildT6Payload(personAttributes, result);
        if (payloadJson == null) {
            return null;
        }

        try {
            return T6OnnxSignatureGenerator.generateSignature(payloadJson);
        } catch (Exception e) {
            logger.error("Error generating token signature for token id: {}", T6_RULE_ID, e);
            return null;
        }
    }

    public String buildT6Payload(Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result) {
        if (personAttributes == null) {
            return null;
        }

        Map<String, String> payload = new LinkedHashMap<>();
        if (!addT6Field(PostalCodeAttribute.class, "PostalCode", personAttributes, result, payload)
                || !addT6Field(BirthDateAttribute.class, "Birthdate", personAttributes, result, payload)
                || !addT6Field(FirstNameAttribute.class, "GivenName", personAttributes, result, payload)
                || !addT6Field(LastNameAttribute.class, "Surname", personAttributes, result, payload)
                || !addT6Field(SexAttribute.class, "Gender", personAttributes, result, payload)) {
            return null;
        }

        return asJson(payload);
    }

    public TokenGeneratorResult getAllTokensExcludingT6(Map<Class<? extends Attribute>, String> personAttributes) {
        TokenGeneratorResult result = new TokenGeneratorResult();

        for (String tokenId : tokenDefinition.getTokenIdentifiers()) {
            if (T6_RULE_ID.equals(tokenId)) {
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

    public void applyT6SignatureToken(TokenGeneratorResult result, String signature) {
        try {
            String token = tokenizer.tokenize(signature);
            result.getTokens().put(T6_RULE_ID, token);
            if (Token.BLANK.equals(token)) {
                result.getBlankTokensByRule().add(T6_RULE_ID);
            }
        } catch (Exception e) {
            logger.error("Error generating token for token id: " + T6_RULE_ID, e);
            result.getTokens().put(T6_RULE_ID, Token.BLANK);
            result.getBlankTokensByRule().add(T6_RULE_ID);
        }
    }

    private boolean addT6Field(Class<? extends Attribute> attributeClass, String fieldName,
            Map<Class<? extends Attribute>, String> personAttributes, TokenGeneratorResult result,
            Map<String, String> payload) {
        if (!personAttributes.containsKey(attributeClass)) {
            return false;
        }

        Attribute attribute = attributeInstanceMap.get(attributeClass);
        if (attribute == null) {
            return false;
        }

        String value = personAttributes.get(attributeClass);
        if (!attribute.validate(value)) {
            result.getInvalidAttributes().add(attribute.getName());
            return false;
        }

        String normalized = attribute.normalize(value);
        if (normalized == null || normalized.isBlank()) {
            result.getInvalidAttributes().add(attribute.getName());
            return false;
        }

        payload.put(fieldName, normalized);
        return true;
    }

    private String asJson(Map<String, String> values) {
        StringBuilder builder = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, String> entry : values.entrySet()) {
            if (!first) {
                builder.append(", ");
            }
            builder.append("\"").append(escapeJson(entry.getKey())).append("\": ");
            builder.append("\"").append(escapeJson(entry.getValue())).append("\"");
            first = false;
        }
        builder.append("}");
        return builder.toString();
    }

    private String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
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
            if (!attributeInstanceMap.get(entry.getKey()).validate(entry.getValue())) {
                response.add(attributeInstanceMap.get(entry.getKey()).getName());
            }
        }

        return response;
    }
}
