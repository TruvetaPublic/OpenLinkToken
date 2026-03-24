/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.attributes.AttributeLoader;
import com.truveta.opentoken.attributes.person.BirthDateAttribute;
import com.truveta.opentoken.attributes.person.FirstNameAttribute;
import com.truveta.opentoken.attributes.person.LastNameAttribute;
import com.truveta.opentoken.attributes.person.PostalCodeAttribute;
import com.truveta.opentoken.attributes.person.SexAttribute;
import com.truveta.opentoken.tokentransformer.rotation.RotationEmbeddingTransformer;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * {@link InferenceSignatureProvider} implementation that delegates to the ONNX-backed
 * {@link T6OnnxSignatureGenerator} for T6 token signature generation.
 *
 * <p>Registered via {@link java.util.ServiceLoader} so that the core module
 * discovers it at runtime when {@code opentoken-core-ai} is on the classpath.
 */
@Slf4j
public class OnnxT6SignatureProvider implements InferenceSignatureProvider {

    private static final String TOKEN_ID = "T6";
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    /**
     * Lazily initialized, cached rotation embedding transformer.
     * Volatile for double-checked locking.
     */
    private static volatile RotationEmbeddingTransformer rotationTransformer;

    private final Map<Class<? extends Attribute>, Attribute> attributeInstanceMap;

    /**
     * No-arg constructor required by {@link java.util.ServiceLoader}.
     */
    public OnnxT6SignatureProvider() {
        attributeInstanceMap = new HashMap<>();
        AttributeLoader.load().forEach(attribute -> attributeInstanceMap.put(attribute.getClass(), attribute));
    }

    @Override
    public String getTokenId() {
        return TOKEN_ID;
    }

    @Override
    public boolean isEnabled() {
        return T6InferenceConfig.isEnabled();
    }

    @Override
    public String generateSignature(Map<Class<? extends Attribute>, String> personAttributes) {
        TokenGeneratorResult dummyResult = new TokenGeneratorResult();
        String payload = buildT6Payload(personAttributes, dummyResult);
        if (payload == null) {
            return null;
        }
        try {
            if (RotationConfig.isEnabled()) {
                List<float[]> rawEmbeddings = T6OnnxSignatureGenerator.generateRawEmbeddings(List.of(payload));
                float[] embedding = rawEmbeddings.get(0);
                List<String> rotationValues = getOrCreateTransformer(embedding.length).transform(embedding);
                return String.join(",", rotationValues);
            }
            return T6OnnxSignatureGenerator.generateSignature(payload);
        } catch (Exception e) {
            log.error("Error generating T6 signature", e);
            return null;
        }
    }

    @Override
    public InferenceBatchResult generateBatch(List<Map<Class<? extends Attribute>, String>> rows) {
        List<String> payloads = new ArrayList<>(rows.size());
        List<Integer> validIndices = new ArrayList<>(rows.size());

        for (int i = 0; i < rows.size(); i++) {
            TokenGeneratorResult dummyResult = new TokenGeneratorResult();
            String payload = buildT6Payload(rows.get(i), dummyResult);
            payloads.add(payload); // may be null for invalid rows
            if (payload != null) {
                validIndices.add(i);
            }
        }

        // Collect valid payloads for batch inference
        List<String> validPayloads = validIndices.stream()
                .map(payloads::get)
                .toList();

        if (validPayloads.isEmpty()) {
            List<String> emptySigs = new ArrayList<>();
            List<float[]> emptyEmbs = new ArrayList<>();
            for (int i = 0; i < rows.size(); i++) {
                emptySigs.add(null);
                emptyEmbs.add(null);
            }
            return new InferenceBatchResult(emptySigs, emptyEmbs);
        }

        T6OnnxSignatureGenerator.GenerationResult batchResult =
                T6OnnxSignatureGenerator.generateSignaturesAndRawEmbeddings(validPayloads);

        // Map results back to original row indices (null for invalid rows)
        List<String> signatures = new ArrayList<>(rows.size());
        List<float[]> embeddings = new ArrayList<>(rows.size());
        for (int i = 0; i < rows.size(); i++) {
            signatures.add(null);
            embeddings.add(null);
        }

        if (RotationConfig.isEnabled()) {
            for (int vi = 0; vi < validIndices.size(); vi++) {
                int originalIndex = validIndices.get(vi);
                float[] embedding = batchResult.rawEmbeddings().get(vi);
                List<String> rotationValues = getOrCreateTransformer(embedding.length).transform(embedding);
                signatures.set(originalIndex, String.join(",", rotationValues));
                embeddings.set(originalIndex, embedding);
            }
        } else {
            for (int vi = 0; vi < validIndices.size(); vi++) {
                int originalIndex = validIndices.get(vi);
                signatures.set(originalIndex, batchResult.signatures().get(vi));
                embeddings.set(originalIndex, batchResult.rawEmbeddings().get(vi));
            }
        }

        return new InferenceBatchResult(signatures, embeddings);
    }

    /**
     * Returns the cached {@link RotationEmbeddingTransformer}, creating it on first call.
     *
     * <p>Uses double-checked locking so that the expensive matrix generation only runs once,
     * even under concurrent access.
     *
     * @param embeddingDim dimension of the raw CLS embedding from ONNX
     * @return cached transformer configured from {@link RotationConfig}
     */
    private static RotationEmbeddingTransformer getOrCreateTransformer(int embeddingDim) {
        if (rotationTransformer == null) {
            synchronized (OnnxT6SignatureProvider.class) {
                if (rotationTransformer == null) {
                    rotationTransformer = RotationEmbeddingTransformer.withDefaults(
                            RotationConfig.getRotationIv(),
                            RotationConfig.getRotationCount(),
                            embeddingDim,
                            RotationConfig.getHashDimension());
                }
            }
        }
        return rotationTransformer;
    }

    /**
     * Builds the deterministic JSON payload for T6 inference from person attributes.
     * Returns {@code null} if any required field is missing or invalid.
     *
     * @param personAttributes normalised attribute map for one record
     * @param result           result object to record invalid attributes into
     * @return JSON string payload, or {@code null} if any required field is missing/invalid
     */
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
        try {
            return OBJECT_MAPPER.writeValueAsString(values);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to serialize T6 payload to JSON", e);
        }
    }
}
