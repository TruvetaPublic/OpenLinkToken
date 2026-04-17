/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer.rotation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.junit.jupiter.api.Test;

class RotationEmbeddingTransformerTest {

    private static final String IV = "rotation-embedding-test-iv-2024";

    @Test
    void testTransformReturnsRotationCountTokens() {
        int rotationCount = 4;
        int dimension = 8;
        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults(IV, rotationCount, dimension, 4);

        float[] embedding = { 0.1f, 0.2f, 0.3f, 0.4f, -0.1f, -0.2f, -0.3f, -0.4f };
        List<String> tokens = transformer.transform(embedding);

        assertEquals(rotationCount, tokens.size());
    }

    @Test
    void testEachTokenIsNonEmptySpaceSeparatedIntegers() {
        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults(IV, 3, 4, 4);

        float[] embedding = { 1.0f, -1.0f, 0.5f, -0.5f };
        List<String> tokens = transformer.transform(embedding);

        for (String token : tokens) {
            assertFalse(token.isBlank(), "Token should not be blank");
            for (String part : token.split(" ")) {
                Integer.parseInt(part); // must be a valid integer
            }
        }
    }

    @Test
    void testMatrixCachingProducesIdenticalResults() {
        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults(IV, 4, 8, 4);

        float[] embedding = { 0.5f, -0.5f, 1.0f, -1.0f, 0.25f, -0.25f, 0.75f, -0.75f };

        List<String> first = transformer.transform(embedding);
        List<String> second = transformer.transform(embedding);

        assertEquals(first, second, "Calling transform() twice must return identical results");
    }

    @Test
    void testDimension4HashDimension2RotationCount3() {
        int rotationCount = 3;
        int dimension = 4;
        int hashDimension = 2;

        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults(IV, rotationCount, dimension, hashDimension);

        float[] embedding = { 1.0f, 0.5f, -0.5f, -1.0f };
        List<String> tokens = transformer.transform(embedding);

        assertEquals(rotationCount, tokens.size(), "Should return rotationCount tokens");

        for (String token : tokens) {
            String[] parts = token.split(" ");
            assertEquals(hashDimension, parts.length,
                    "Each token should have hashDimension space-separated integers");
            for (String part : parts) {
                Integer.parseInt(part); // must parse as integer
            }
        }
    }

    @Test
    void testHashDimensionProjectionMatchesPythonParityFixture() {
        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults("openlinktoken-ml1-v1", 2, 8, 3);

        float[] embedding = { 0.125f, -0.25f, 0.375f, -0.5f, 0.625f, -0.75f, 0.875f, -1.0f };

        List<String> tokens = transformer.transform(embedding);

        assertEquals(List.of("98 111 102", "87 96 120"), tokens);
    }

    @Test
    void testThreadSafetyProducesConsistentResults() throws InterruptedException {
        int threadCount = 20;
        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults(IV, 4, 8, 4);

        float[] embedding = { 0.1f, 0.2f, 0.3f, 0.4f, -0.1f, -0.2f, -0.3f, -0.4f };

        @SuppressWarnings("unchecked")
        List<String>[] results = new List[threadCount];
        List<Exception> errors = new java.util.ArrayList<>();
        CountDownLatch latch = new CountDownLatch(threadCount);

        ExecutorService pool = Executors.newFixedThreadPool(threadCount);
        for (int i = 0; i < threadCount; i++) {
            final int idx = i;
            pool.submit(() -> {
                try {
                    results[idx] = transformer.transform(embedding);
                } catch (Exception e) {
                    synchronized (errors) {
                        errors.add(e);
                    }
                } finally {
                    latch.countDown();
                }
            });
        }
        latch.await();
        pool.shutdown();

        assertFalse(!errors.isEmpty(), "No thread errors expected, got: " + errors);

        List<String> reference = results[0];
        for (List<String> r : results) {
            assertEquals(reference, r, "All threads should produce identical outputs");
        }
    }

    @Test
    void testWithDefaultsCreatesZeroBias() {
        // A zero-bias transformer applied to the zero vector should project to zero,
        // and the zero vector should quantize to the midpoint bin (100 for [-5,5]/0.05).
        int dimension = 4;
        RotationEmbeddingTransformer transformer =
                RotationEmbeddingTransformer.withDefaults(IV, 2, dimension, dimension);

        float[] zeroEmbedding = new float[dimension];
        List<String> tokens = transformer.transform(zeroEmbedding);

        assertEquals(2, tokens.size());
        for (String token : tokens) {
            for (String part : token.split(" ")) {
                // Zero vector projected through any rotation is still zero; bin = 100
                assertEquals("100", part, "Zero embedding should map to midpoint bin");
            }
        }
    }

    @Test
    void testConstructorValidationNullIvThrows() {
        assertThrows(IllegalArgumentException.class,
                () -> RotationEmbeddingTransformer.withDefaults(null, 2, 4, 2));
    }

    @Test
    void testConstructorValidationZeroRotationCountThrows() {
        assertThrows(IllegalArgumentException.class,
                () -> RotationEmbeddingTransformer.withDefaults(IV, 0, 4, 2));
    }

    @Test
    void testConstructorValidationHashDimensionExceedsDimensionThrows() {
        assertThrows(IllegalArgumentException.class,
                () -> RotationEmbeddingTransformer.withDefaults(IV, 2, 4, 5));
    }
}
