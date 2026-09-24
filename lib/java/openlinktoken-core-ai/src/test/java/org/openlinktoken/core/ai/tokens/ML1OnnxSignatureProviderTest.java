/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.openlinktoken.core.ai.tokentransformer.rotation.RotationEmbeddingTransformer;
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

    /**
     * Verifies that the provider advertises the ML1 token identifier.
     */
    @Test
    void getTokenId_matchesMl1TokenIdentifier() {
        assertEquals(ML1Token.TOKEN_ID, provider.getTokenId());
    }

    /**
     * Creates a provider for each test.
     */
    @BeforeEach
    void setUp() {
        provider = new ML1OnnxSignatureProvider();
    }

    /**
     * Restores mutable inference and rotation state after each test.
     *
     * @throws Exception if the cached transformer cannot be reset reflectively
     */
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

    /**
     * Verifies that payload fields are normalized and emitted in model order.
     */
    @Test
    void buildMl1Payload_validAttributes_preservesFieldOrderAndNormalization() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("PostalCode", "95123");
        attrs.put("BirthDate", "1990-07-09");
        attrs.put("FirstName", " Alice ");
        attrs.put("LastName", " Smith ");
        attrs.put("Sex", "female");

        String payload = provider.buildMl1Payload(attrs, new TokenGeneratorResult());

        assertEquals(
                "{\"PostalCode\": \"95123\", \"Birthdate\": \"1990-07-09\", "
                        + "\"GivenName\": \"Alice\", \"Surname\": \"Smith\", \"Gender\": \"Female\"}",
                payload);
    }

    /**
     * Verifies that a payload is not built when a required field is absent.
     */
    @Test
    void buildMl1Payload_missingRequiredField_returnsNull() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("PostalCode", "95123");
        attrs.put("BirthDate", "1990-07-09");
        attrs.put("FirstName", "Alice");
        attrs.put("LastName", "Smith");

        assertNull(provider.buildMl1Payload(attrs, new TokenGeneratorResult()));
    }

    /**
     * Verifies that invalid required fields are recorded before payload creation fails.
     */
    @Test
    void buildMl1Payload_invalidRequiredField_recordsInvalidAttribute() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("PostalCode", "95123");
        attrs.put("BirthDate", "1990-07-09");
        attrs.put("FirstName", "Alice");
        attrs.put("LastName", "Smith");
        attrs.put("Sex", "unknown");
        TokenGeneratorResult result = new TokenGeneratorResult();

        assertNull(provider.buildMl1Payload(attrs, result));
        assertTrue(result.getInvalidAttributes().contains("Sex"), result.getInvalidAttributes().toString());
    }

    /**
     * Verifies that provider availability follows the inference configuration.
     */
    @Test
    void isEnabled_reflectsInferenceConfiguration() {
        ML1InferenceConfig.configure(false, "", "", 128, 64, 1);
        assertTrue(!provider.isEnabled());

        ML1InferenceConfig.configure(true, "", "", 128, 64, 1);
        assertTrue(provider.isEnabled());
    }

    /**
     * Verifies that an all-invalid batch preserves one null signature per row.
     */
    @Test
    void generateBatch_allInvalidRows_returnsNullForEachRow() {
        List<Map<String, String>> rows = List.of(Map.of(), Map.of());

        List<String> signatures = provider.generateBatch(rows).signatures();

        assertEquals(Arrays.asList(null, null), signatures);
    }

    // -----------------------------------------------------------------------
    // computeT1Signature
    // -----------------------------------------------------------------------

    /**
     * Verifies the T1 signature produced from valid person attributes.
     */
    @Test
    void computeT1Signature_validAttributes_returnsExpectedSignature() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("LastName", "Wright");
        attrs.put("FirstName", "Robert");
        // SexAttribute validates against ^([Mm](ale)?|[Ff](emale)?)$ — use mixed-case input
        attrs.put("Sex", "Female");
        attrs.put("BirthDate", "1990-07-09");

        String sig = provider.computeT1Signature(attrs);

        // normalize("Female") → "Female"; T|U → "FEMALE"
        assertEquals("WRIGHT|R|FEMALE|1990-07-09", sig);
    }

    /**
     * Verifies that a null attribute map cannot produce a T1 signature.
     */
    @Test
    void computeT1Signature_nullMap_returnsNull() {
        assertNull(provider.computeT1Signature(null));
    }

    /**
     * Verifies that a missing last name prevents T1 signature creation.
     */
    @Test
    void computeT1Signature_missingLastName_returnsNull() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("FirstName", "Robert");
        attrs.put("Sex", "FEMALE");
        attrs.put("BirthDate", "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    /**
     * Verifies that a missing first name prevents T1 signature creation.
     */
    @Test
    void computeT1Signature_missingFirstName_returnsNull() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("LastName", "Wright");
        attrs.put("Sex", "FEMALE");
        attrs.put("BirthDate", "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    /**
     * Verifies that a missing sex value prevents T1 signature creation.
     */
    @Test
    void computeT1Signature_missingSex_returnsNull() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("LastName", "Wright");
        attrs.put("FirstName", "Robert");
        attrs.put("BirthDate", "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    /**
     * Verifies that a missing birth date prevents T1 signature creation.
     */
    @Test
    void computeT1Signature_missingBirthDate_returnsNull() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("LastName", "Wright");
        attrs.put("FirstName", "Robert");
        attrs.put("Sex", "Female");

        assertNull(provider.computeT1Signature(attrs));
    }

    /**
     * Verifies that an invalid birth date prevents T1 signature creation.
     */
    @Test
    void computeT1Signature_invalidBirthDate_returnsNull() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("LastName", "Wright");
        attrs.put("FirstName", "Robert");
        attrs.put("Sex", "Female");
        attrs.put("BirthDate", "not-a-date");

        assertNull(provider.computeT1Signature(attrs));
    }

    /**
     * Verifies that lowercase and padded attributes are normalized before composition.
     */
    @Test
    void computeT1Signature_lowercaseInputsAreNormalized() {
        Map<String, String> attrs = new HashMap<>();
        attrs.put("LastName", "  smith  ");
        attrs.put("FirstName", "  alice  ");
        attrs.put("Sex", "male");
        attrs.put("BirthDate", "2000-01-15");

        String sig = provider.computeT1Signature(attrs);

        assertEquals("SMITH|A|MALE|2000-01-15", sig);
    }

    /**
     * Verifies that the configured default rotation IV matches the cross-language value.
     */
    @Test
    void rotationConfig_defaultIv_matchesPythonParityValue() {
        assertEquals("openlinktoken-ml1-v1", RotationConfig.DEFAULT_IV);
    }

    /**
     * Verifies that the cached transformer uses the configured rotation parameters.
     *
     * @throws Exception if the transformer cannot be inspected reflectively
     */
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

    /**
     * Verifies that each rotation value produces a lowercase SHA-256 digest.
     */
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

    /**
     * Verifies that hashing the same rotation values and key is deterministic.
     */
    @Test
    void hashRotationValues_deterministicOutput() {
        List<String> rotationValues = List.of("94 104 96 97");
        String key = "WRIGHT|R|FEMALE|1990-07-09";

        List<String> first = provider.hashRotationValues(rotationValues, key);
        List<String> second = provider.hashRotationValues(rotationValues, key);

        assertEquals(first, second, "Hash must be deterministic");
    }

    /**
     * Verifies that different T1 blocking keys produce different digests.
     */
    @Test
    void hashRotationValues_differentKeysProduceDifferentDigests() {
        List<String> rotationValues = List.of("94 104 96 97");

        String digest1 = provider.hashRotationValues(rotationValues, "WRIGHT|R|FEMALE|1990-07-09").get(0);
        String digest2 = provider.hashRotationValues(rotationValues, "SMITH|A|MALE|2000-01-15").get(0);

        assertTrue(!digest1.equals(digest2), "Different keys must produce different digests");
    }

    /**
     * Verifies the expected digest for the known rotation and blocking-key fixture.
     */
    @Test
    void hashRotationValues_knownVector() {
        String rawT1 = "MEISTER|C|FEMALE|1989-05-25";
        String blockingKey = provider.computeT1BlockingKey(rawT1);

        assertEquals("f016a96ba8552da8c9d7ac327f91081e22740f0ddd71dc372fa4dbba2ca34253", blockingKey);
        assertEquals(
                List.of("4ff691600f8c2df6142c405cbcd6f166a588ba83bd93ba6f028e082ef99decd8"),
                provider.hashRotationValues(List.of("99 100 100 101"), blockingKey));
    }

    /**
     * Verifies that rotation values are not hashed without a blocking key.
     */
    @Test
    void hashRotationValues_missingBlockingKey_returnsNull() {
        assertNull(provider.hashRotationValues(List.of("99 100 100 101"), null));
    }

    /**
     * Verifies that a missing blocking key yields the canonical blank token.
     */
    @Test
    void buildRotationSignature_missingBlockingKey_returnsBlankToken() {
        assertEquals(
                Token.BLANK,
                provider.buildRotationSignature(List.of("99 100 100 101"), null));
    }

    /**
     * Invokes the provider's lazy transformer factory for test inspection.
     *
     * @param embeddingDim dimension of the embedding used to configure the transformer
     * @return the cached rotation transformer
     * @throws Exception if reflective lookup or invocation fails
     */
    private static RotationEmbeddingTransformer getRotationTransformer(int embeddingDim) throws Exception {
        Method getOrCreateTransformer = ML1OnnxSignatureProvider.class.getDeclaredMethod(
                "getOrCreateTransformer",
                int.class);
        getOrCreateTransformer.setAccessible(true);
        return (RotationEmbeddingTransformer) getOrCreateTransformer.invoke(null, embeddingDim);
    }

    /**
     * Reads a named field from an object for configuration assertions.
     *
     * @param target object that declares the field
     * @param fieldName field to read
     * @return the field's current value
     * @throws Exception if the field cannot be accessed
     */
    private static Object readField(Object target, String fieldName) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(target);
    }

    /**
     * Clears the provider's cached transformer between tests.
     *
     * @throws Exception if the cache field cannot be reset reflectively
     */
    private static void resetRotationTransformer() throws Exception {
        Field transformerField = ML1OnnxSignatureProvider.class.getDeclaredField("rotationTransformer");
        transformerField.setAccessible(true);
        transformerField.set(null, null);
    }
}
