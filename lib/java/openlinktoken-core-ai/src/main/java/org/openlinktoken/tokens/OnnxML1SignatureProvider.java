/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.AttributeLoader;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.tokens.definitions.T1Token;
import org.openlinktoken.tokentransformer.rotation.RotationEmbeddingTransformer;
import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * {@link InferenceSignatureProvider} implementation that delegates to the ONNX-backed
 * {@link ML1OnnxSignatureGenerator} for ML1 token signature generation.
 *
 * <p>Registered via {@link java.util.ServiceLoader} so that the core module
 * discovers it at runtime when {@code openlinktoken-core-ai} is on the classpath.
 */
@Slf4j
public class OnnxML1SignatureProvider implements InferenceSignatureProvider {

    private static final String TOKEN_ID = "ML1";

    /**
     * Lazily initialized, cached rotation embedding transformer.
     * Volatile for double-checked locking.
     */
    private static volatile RotationEmbeddingTransformer rotationTransformer;

    private final Map<Class<? extends Attribute>, Attribute> attributeInstanceMap;

    /**
     * No-arg constructor required by {@link java.util.ServiceLoader}.
     */
    public OnnxML1SignatureProvider() {
        attributeInstanceMap = new HashMap<>();
        AttributeLoader.load().forEach(attribute -> attributeInstanceMap.put(attribute.getClass(), attribute));
    }

    @Override
    public String getTokenId() {
        return TOKEN_ID;
    }

    @Override
    public boolean isEnabled() {
        return ML1InferenceConfig.isEnabled();
    }

    @Override
    public String generateSignature(Map<Class<? extends Attribute>, String> personAttributes) {
        TokenGeneratorResult dummyResult = new TokenGeneratorResult();
        String payload = buildMl1Payload(personAttributes, dummyResult);
        if (payload == null) {
            return null;
        }
        try {
            if (RotationConfig.isEnabled()) {
                List<float[]> rawEmbeddings = ML1OnnxSignatureGenerator.generateRawEmbeddings(List.of(payload));
                float[] embedding = rawEmbeddings.get(0);
                List<String> rotationValues = getOrCreateTransformer(embedding.length).transform(embedding);
                String t1Sig = computeT1Signature(personAttributes);
                if (t1Sig != null) {
                    rotationValues = hashRotationValues(rotationValues, computeT1BlockingKey(t1Sig));
                }
                return String.join(",", rotationValues);
            }
            return ML1OnnxSignatureGenerator.generateSignature(payload);
        } catch (Exception e) {
            log.error("Error generating ML1 signature", e);
            return null;
        }
    }

    @Override
    public InferenceBatchResult generateBatch(List<Map<Class<? extends Attribute>, String>> rows) {
        List<String> payloads = new ArrayList<>(rows.size());
        List<Integer> validIndices = new ArrayList<>(rows.size());

        for (int i = 0; i < rows.size(); i++) {
            TokenGeneratorResult dummyResult = new TokenGeneratorResult();
            String payload = buildMl1Payload(rows.get(i), dummyResult);
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

        ML1OnnxSignatureGenerator.GenerationResult batchResult =
                ML1OnnxSignatureGenerator.generateSignaturesAndRawEmbeddings(validPayloads);

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
                String t1Sig = computeT1Signature(rows.get(originalIndex));
                if (t1Sig != null) {
                    rotationValues = hashRotationValues(rotationValues, computeT1BlockingKey(t1Sig));
                }
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
            synchronized (OnnxML1SignatureProvider.class) {
                if (rotationTransformer == null) {
                    float[] configuredBias = RotationConfig.getDimensionBias();
                    float[] effectiveBias = configuredBias == null ? new float[embeddingDim] : configuredBias;
                    rotationTransformer = new RotationEmbeddingTransformer(
                            RotationConfig.getRotationIv(),
                            RotationConfig.getRotationCount(),
                            embeddingDim,
                            RotationConfig.getHashDimension(),
                            effectiveBias,
                            RotationConfig.getMinVal(),
                            RotationConfig.getMaxVal(),
                            RotationConfig.getBinWidth());
                }
            }
        }
        return rotationTransformer;
    }

    /**
     * Computes the T1 raw signature from the given person attributes using the T1 token definition.
     *
     * <p>The T1 signature is {@code LASTNAME|FIRSTINITIAL|SEX|BIRTHDATE}, produced by applying
     * each attribute expression from {@link T1Token#getDefinition()} in order.
     *
     * @param personAttributes normalised attribute map for one record
     * @return pipe-delimited T1 signature string, or {@code null} if any field is missing or invalid
     */
    String computeT1Signature(Map<Class<? extends Attribute>, String> personAttributes) {
        if (personAttributes == null) {
            return null;
        }
        List<AttributeExpression> t1Definition = new T1Token().getDefinition();
        List<String> parts = new ArrayList<>(t1Definition.size());
        for (AttributeExpression attrExpr : t1Definition) {
            Class<? extends Attribute> attrClass = attrExpr.getAttributeClass();
            String raw = personAttributes.get(attrClass);
            if (raw == null || raw.isBlank()) {
                return null;
            }
            Attribute attr = attributeInstanceMap.get(attrClass);
            if (attr == null || !attr.validate(raw)) {
                return null;
            }
            String normalized = attr.normalize(raw);
            try {
                String effective = attrExpr.getEffectiveValue(normalized);
                if (effective == null || effective.isBlank()) {
                    return null;
                }
                parts.add(effective);
            } catch (IllegalArgumentException e) {
                return null;
            }
        }
        return parts.isEmpty() ? null : String.join("|", parts);
    }

    /**
     * Computes the PersonMatching T1 blocking key from the raw T1 signature.
     *
     * @param t1Signature raw pipe-delimited T1 signature
     * @return lowercase hex-encoded SHA-256 T1 blocking key
     */
    String computeT1BlockingKey(String t1Signature) {
        return sha256Hex(t1Signature);
    }

    /**
     * SHA-256 hash each rotation value string concatenated with the T1 blocking key.
     *
     * @param rotationValues list of space-separated bin index strings from the rotation pipeline
     * @param t1BlockingKey  SHA-256 hex of the raw T1 signature appended to each rotation value
     * @return list of lowercase hex-encoded SHA-256 digests, one per rotation value
     */
    List<String> hashRotationValues(List<String> rotationValues, String t1BlockingKey) {
        List<String> result = new ArrayList<>(rotationValues.size());
        for (String rotationValue : rotationValues) {
            result.add(sha256Hex(rotationValue + t1BlockingKey));
        }
        return result;
    }

    private static String sha256Hex(String value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is unavailable", e);
        }
    }

    /**
     * Builds the deterministic JSON payload for ML1 inference from person attributes.
     * Returns {@code null} if any required field is missing or invalid.
     *
     * @param personAttributes normalised attribute map for one record
     * @param result           result object to record invalid attributes into
     * @return JSON string payload, or {@code null} if any required field is missing/invalid
     */
    public String buildMl1Payload(Map<Class<? extends Attribute>, String> personAttributes,
            TokenGeneratorResult result) {
        if (personAttributes == null) {
            return null;
        }

        // Field order matches generate_embeddings.py: PostalCode, Birthdate, GivenName, Surname, Gender
        Map<String, String> payload = new LinkedHashMap<>();
        if (!addMl1Field(PostalCodeAttribute.class, "PostalCode", personAttributes, result, payload)
                || !addMl1Field(BirthDateAttribute.class, "Birthdate", personAttributes, result, payload)
                || !addMl1Field(FirstNameAttribute.class, "GivenName", personAttributes, result, payload)
                || !addMl1Field(LastNameAttribute.class, "Surname", personAttributes, result, payload)
                || !addMl1Field(SexAttribute.class, "Gender", personAttributes, result, payload)) {
            return null;
        }

        return asJson(payload);
    }

    private boolean addMl1Field(Class<? extends Attribute> attributeClass, String fieldName,
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

    /**
     * Serializes a string map to JSON matching Python's json.dumps() default format:
     * space after colon and comma, non-ASCII characters escaped as unicode escapes.
     */
    private String asJson(Map<String, String> values) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, String> entry : values.entrySet()) {
            if (!first) {
                sb.append(", ");
            }
            sb.append('"');
            appendJsonString(sb, entry.getKey());
            sb.append("\": \"");
            appendJsonString(sb, entry.getValue());
            sb.append('"');
            first = false;
        }
        return sb.append('}').toString();
    }

    private static void appendJsonString(StringBuilder sb, String value) {
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '"') {
                sb.append("\\\"");
            } else if (c == '\\') {
                sb.append("\\\\");
            } else if (c == '\n') {
                sb.append("\\n");
            } else if (c == '\r') {
                sb.append("\\r");
            } else if (c == '\t') {
                sb.append("\\t");
            } else if (c < 0x20) {
                sb.append(String.format("\\u%04x", (int) c));
            } else if (c > 0x7E) {
                // Encode non-ASCII as unicode escape to match Python json.dumps ensure_ascii=True
                sb.append(String.format("\\u%04x", (int) c));
            } else {
                sb.append(c);
            }
        }
    }
}
