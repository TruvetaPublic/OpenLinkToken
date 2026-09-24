/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/**
 * Tests ML1 inference configuration defaults, updates, and validation.
 */
class ML1InferenceConfigTest {

    /**
     * Restores inference defaults so configuration changes do not leak between tests.
     */
    @AfterEach
    void resetConfiguration() {
        ML1InferenceConfig.configure(
                true,
                ML1InferenceConfig.DEFAULT_MODEL_PATH,
                ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
                ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
                ML1InferenceConfig.DEFAULT_BATCH_SIZE,
                ML1InferenceConfig.DEFAULT_NUM_THREADS);
    }

    /**
     * Verifies that blank and null asset paths select the bundled defaults.
     */
    @Test
    void blankAndNullPathsUseBundledDefaults() {
        ML1InferenceConfig.configure(true, " ", null, 32, 8, 2);

        assertTrue(ML1InferenceConfig.isEnabled());
        assertEquals(ML1InferenceConfig.DEFAULT_MODEL_PATH, ML1InferenceConfig.getModelPath());
        assertEquals(ML1InferenceConfig.DEFAULT_TOKENIZER_PATH, ML1InferenceConfig.getTokenizerPath());
        assertEquals(32, ML1InferenceConfig.getMaxSequenceLength());
        assertEquals(8, ML1InferenceConfig.getBatchSize());
        assertEquals(2, ML1InferenceConfig.getNumThreads());
    }

    /**
     * Verifies that the four-argument overload uses the default batch size and thread count.
     */
    @Test
    void fourArgumentConfigureUsesDefaultBatchAndThreads() {
        ML1InferenceConfig.configure(false, "model.onnx", "tokenizer.json", 16);

        assertTrue(!ML1InferenceConfig.isEnabled());
        assertEquals("model.onnx", ML1InferenceConfig.getModelPath());
        assertEquals("tokenizer.json", ML1InferenceConfig.getTokenizerPath());
        assertEquals(16, ML1InferenceConfig.getMaxSequenceLength());
        assertEquals(ML1InferenceConfig.DEFAULT_BATCH_SIZE, ML1InferenceConfig.getBatchSize());
        assertEquals(ML1InferenceConfig.DEFAULT_NUM_THREADS, ML1InferenceConfig.getNumThreads());
    }

    /**
     * Verifies that the five-argument overload uses the default thread count.
     */
    @Test
    void fiveArgumentConfigureUsesDefaultThreads() {
        ML1InferenceConfig.configure(true, "model.onnx", "tokenizer.json", 16, 4);

        assertEquals(4, ML1InferenceConfig.getBatchSize());
        assertEquals(ML1InferenceConfig.DEFAULT_NUM_THREADS, ML1InferenceConfig.getNumThreads());
    }

    /**
     * Verifies that non-positive maximum sequence lengths are rejected.
     */
    @Test
    void nonPositiveMaxSequenceLengthThrows() {
        assertThrows(
                IllegalArgumentException.class,
                () -> ML1InferenceConfig.configure(true, "", "", 0, 1, 1));
        assertThrows(
                IllegalArgumentException.class,
                () -> ML1InferenceConfig.configure(true, "", "", -1, 1, 1));
    }

    /**
     * Verifies that non-positive inference batch sizes are rejected.
     */
    @Test
    void nonPositiveBatchSizeThrows() {
        assertThrows(
                IllegalArgumentException.class,
                () -> ML1InferenceConfig.configure(true, "", "", 1, 0, 1));
        assertThrows(
                IllegalArgumentException.class,
                () -> ML1InferenceConfig.configure(true, "", "", 1, -1, 1));
    }

    /**
     * Verifies that non-positive ONNX runtime thread counts are rejected.
     */
    @Test
    void nonPositiveThreadCountThrows() {
        assertThrows(
                IllegalArgumentException.class,
                () -> ML1InferenceConfig.configure(true, "", "", 1, 1, 0));
        assertThrows(
                IllegalArgumentException.class,
                () -> ML1InferenceConfig.configure(true, "", "", 1, 1, -1));
    }

}
