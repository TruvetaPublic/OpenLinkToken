/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.openlinktoken.core.ai.tokentransformer.rotation.RotationEmbeddingTransformer;
import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.core.ai.tokens.definitions.ML1Token;
import org.openlinktoken.tokens.Token;
import org.openlinktoken.tokens.TokenGeneratorResult;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Tests ML1 payload construction, signatures, rotation hashing, and batch behavior.
 */
class ML1OnnxSignatureProviderTest {

    private ML1OnnxSignatureProvider provider;

    @Test
    void getTokenId_matchesMl1TokenIdentifier() {
        assertEquals(ML1Token.TOKEN_ID, provider.getTokenId());
    }

    @BeforeEach
    void setUp() {
        provider = new ML1OnnxSignatureProvider();
    }

    @AfterEach
    void tearDown() throws Exception {
        RotationConfig.configure(
                true,
                RotationConfig.DEFAULT_IV,
                RotationConfig.DEFAULT_ROTATION_COUNT,
                RotationConfig.DEFAULT_HASH_DIMENSION,
                RotationConfig.DEFAULT_BIN_WIDTH,
                RotationConfig.DEFAULT_MIN_VAL,
                RotationConfig.DEFAULT_MAX_VAL);
        ML1InferenceConfig.configure(
                true,
                ML1InferenceConfig.DEFAULT_MODEL_PATH,
                ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
                ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
                ML1InferenceConfig.DEFAULT_BATCH_SIZE,
                ML1InferenceConfig.DEFAULT_NUM_THREADS);
        resetRotationTransformer();
    }

    // -----------------------------------------------------------------------
    // ML1 payload construction and provider state
    // -----------------------------------------------------------------------

    @Test
    void buildMl1Payload_validAttributes_preservesFieldOrderAndNormalization() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(PostalCodeAttribute.class, "95123");
        attrs.put(BirthDateAttribute.class, "1990-07-09");
        attrs.put(FirstNameAttribute.class, " Alice ");
        attrs.put(LastNameAttribute.class, " Smith ");
        attrs.put(SexAttribute.class, "female");

        String payload = provider.buildMl1Payload(attrs, new TokenGeneratorResult());

        assertEquals(
                "{\"PostalCode\": \"95123\", \"Birthdate\": \"1990-07-09\", "
                        + "\"GivenName\": \"Alice\", \"Surname\": \"Smith\", \"Gender\": \"Female\"}",
                payload);
    }

    @Test
    void buildMl1Payload_missingRequiredField_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(PostalCodeAttribute.class, "95123");
        attrs.put(BirthDateAttribute.class, "1990-07-09");
        attrs.put(FirstNameAttribute.class, "Alice");
        attrs.put(LastNameAttribute.class, "Smith");

        assertNull(provider.buildMl1Payload(attrs, new TokenGeneratorResult()));
    }

    @Test
    void buildMl1Payload_invalidRequiredField_recordsInvalidAttribute() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(PostalCodeAttribute.class, "95123");
        attrs.put(BirthDateAttribute.class, "1990-07-09");
        attrs.put(FirstNameAttribute.class, "Alice");
        attrs.put(LastNameAttribute.class, "Smith");
        attrs.put(SexAttribute.class, "unknown");
        TokenGeneratorResult result = new TokenGeneratorResult();

        assertNull(provider.buildMl1Payload(attrs, result));
        assertTrue(result.getInvalidAttributes().contains("Sex"), result.getInvalidAttributes().toString());
    }

    @Test
    void isEnabled_reflectsInferenceConfiguration() {
        ML1InferenceConfig.configure(false, "", "", 128, 64, 1);
        assertTrue(!provider.isEnabled());

        ML1InferenceConfig.configure(true, "", "", 128, 64, 1);
        assertTrue(provider.isEnabled());
    }

    @Test
    void generateBatch_allInvalidRows_returnsNullForEachRow() {
        List<Map<Class<? extends Attribute>, String>> rows = List.of(Map.of(), Map.of());

        List<String> signatures = provider.generateBatch(rows).signatures();

        assertEquals(Arrays.asList(null, null), signatures);
    }

    // -----------------------------------------------------------------------
    // computeT1Signature
    // -----------------------------------------------------------------------

    @Test
    void computeT1Signature_validAttributes_returnsExpectedSignature() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        // SexAttribute validates against ^([Mm](ale)?|[Ff](emale)?)$ — use mixed-case input
        attrs.put(SexAttribute.class, "Female");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        String sig = provider.computeT1Signature(attrs);

        // normalize("Female") → "Female"; T|U → "FEMALE"
        assertEquals("WRIGHT|R|FEMALE|1990-07-09", sig);
    }

    @Test
    void computeT1Signature_nullMap_returnsNull() {
        assertNull(provider.computeT1Signature(null));
    }

    @Test
    void computeT1Signature_missingLastName_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(SexAttribute.class, "FEMALE");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_missingFirstName_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(SexAttribute.class, "FEMALE");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_missingSex_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_missingBirthDate_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(SexAttribute.class, "Female");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_invalidBirthDate_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(SexAttribute.class, "Female");
        attrs.put(BirthDateAttribute.class, "not-a-date");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_lowercaseInputsAreNormalized() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "  smith  ");
        attrs.put(FirstNameAttribute.class, "  alice  ");
        attrs.put(SexAttribute.class, "male");
        attrs.put(BirthDateAttribute.class, "2000-01-15");

        String sig = provider.computeT1Signature(attrs);

        assertEquals("SMITH|A|MALE|2000-01-15", sig);
    }

    @Test
    void rotationConfig_defaultIv_matchesPythonParityValue() {
        assertEquals("openlinktoken-ml1-v1", RotationConfig.DEFAULT_IV);
    }

    @Test
    void getOrCreateTransformer_usesConfiguredRotationParameters() throws Exception {
        RotationConfig.configure(true, "", 3, 2, 0.25, -2.5, 2.5, new double[] { 1.5, -0.5, 0.0, 2.0 });
        resetRotationTransformer();

        RotationEmbeddingTransformer transformer = getRotationTransformer(4);

        assertEquals(RotationConfig.DEFAULT_IV, readField(transformer, "iv"));
        assertEquals(3, readField(transformer, "rotationCount"));
        assertEquals(2, readField(transformer, "hashDimension"));
        assertEquals(0.25d, (double) readField(transformer, "binWidth"));
        assertEquals(-2.5d, (double) readField(transformer, "minVal"));
        assertEquals(2.5d, (double) readField(transformer, "maxVal"));
        double[] bias = (double[]) readField(transformer, "bias");
        assertEquals(List.of(1.5, -0.5, 0.0, 2.0), List.of(bias[0], bias[1], bias[2], bias[3]));
    }

    // -----------------------------------------------------------------------
    // hashRotationValues
    // -----------------------------------------------------------------------

    @Test
    void hashRotationValues_returnsOneHexDigestPerInput() {
        List<String> rotationValues = List.of("94 104 96 97", "12 34 56 78");
        List<String> result = provider.hashRotationValues(rotationValues, "WRIGHT|R|FEMALE|1990-07-09");

        assertEquals(2, result.size());
        for (String digest : result) {
            // SHA-256 produces 32 bytes → 64 hex chars
            assertEquals(64, digest.length(), "Expected 64-char hex digest");
            assertTrue(digest.matches("[0-9a-f]+"), "Digest must be lowercase hex");
        }
    }

    @Test
    void hashRotationValues_deterministicOutput() {
        List<String> rotationValues = List.of("94 104 96 97");
        String key = "WRIGHT|R|FEMALE|1990-07-09";

        List<String> first = provider.hashRotationValues(rotationValues, key);
        List<String> second = provider.hashRotationValues(rotationValues, key);

        assertEquals(first, second, "Hash must be deterministic");
    }

    @Test
    void hashRotationValues_differentKeysProduceDifferentDigests() {
        List<String> rotationValues = List.of("94 104 96 97");

        String digest1 = provider.hashRotationValues(rotationValues, "WRIGHT|R|FEMALE|1990-07-09").get(0);
        String digest2 = provider.hashRotationValues(rotationValues, "SMITH|A|MALE|2000-01-15").get(0);

        assertTrue(!digest1.equals(digest2), "Different keys must produce different digests");
    }

    @Test
    void hashRotationValues_knownVector() {
        String rawT1 = "MEISTER|C|FEMALE|1989-05-25";
        String blockingKey = provider.computeT1BlockingKey(rawT1);

        assertEquals("f016a96ba8552da8c9d7ac327f91081e22740f0ddd71dc372fa4dbba2ca34253", blockingKey);
        assertEquals(
                List.of("4ff691600f8c2df6142c405cbcd6f166a588ba83bd93ba6f028e082ef99decd8"),
                provider.hashRotationValues(List.of("99 100 100 101"), blockingKey));
    }

    @Test
    void hashRotationValues_missingBlockingKey_returnsNull() {
        assertNull(provider.hashRotationValues(List.of("99 100 100 101"), null));
    }

    @Test
    void buildRotationSignature_missingBlockingKey_returnsBlankToken() {
        assertEquals(
                Token.BLANK,
                provider.buildRotationSignature(List.of("99 100 100 101"), null));
    }

    private static RotationEmbeddingTransformer getRotationTransformer(int embeddingDim) throws Exception {
        Method getOrCreateTransformer = ML1OnnxSignatureProvider.class.getDeclaredMethod(
                "getOrCreateTransformer",
                int.class);
        getOrCreateTransformer.setAccessible(true);
        return (RotationEmbeddingTransformer) getOrCreateTransformer.invoke(null, embeddingDim);
    }

    private static Object readField(Object target, String fieldName) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(target);
    }

    private static void resetRotationTransformer() throws Exception {
        Field transformerField = ML1OnnxSignatureProvider.class.getDeclaredField("rotationTransformer");
        transformerField.setAccessible(true);
        transformerField.set(null, null);
    }
}
