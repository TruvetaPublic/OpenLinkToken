/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

/**
 * Runtime configuration for optional ONNX-backed ML1 token generation.
 */
public final class ML1InferenceConfig {

    public static final String DEFAULT_MODEL_PATH = "classpath:/inferencing/ml1/model.onnx";
    public static final String DEFAULT_TOKENIZER_PATH = "classpath:/inferencing/ml1/tokenizer.json";
    public static final int DEFAULT_MAX_SEQUENCE_LENGTH = 128;
    public static final int DEFAULT_BATCH_SIZE = 64;
    public static final int DEFAULT_NUM_THREADS = Runtime.getRuntime().availableProcessors();

    private static volatile boolean enabled = true;
    private static volatile String modelPath = DEFAULT_MODEL_PATH;
    private static volatile String tokenizerPath = DEFAULT_TOKENIZER_PATH;
    private static volatile int maxSequenceLength = DEFAULT_MAX_SEQUENCE_LENGTH;
    private static volatile int batchSize = DEFAULT_BATCH_SIZE;
    private static volatile int numThreads = DEFAULT_NUM_THREADS;

    private ML1InferenceConfig() {
    }

    /**
     * Configure ML1 inference with the default batch size and thread count.
     *
     * @param enableMl1 whether ML1 inference is enabled
     * @param configuredModelPath model path, or the bundled default when blank
     * @param configuredTokenizerPath tokenizer path, or the bundled default when blank
     * @param configuredMaxSequenceLength maximum number of tokenizer positions
     */
    public static synchronized void configure(boolean enableMl1, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength) {
        configure(enableMl1, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                DEFAULT_BATCH_SIZE);
    }

    /**
     * Configure ML1 inference with the default thread count.
     *
     * @param enableMl1 whether ML1 inference is enabled
     * @param configuredModelPath model path, or the bundled default when blank
     * @param configuredTokenizerPath tokenizer path, or the bundled default when blank
     * @param configuredMaxSequenceLength maximum number of tokenizer positions
     * @param configuredBatchSize number of rows processed per inference batch
     */
    public static synchronized void configure(boolean enableMl1, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength, int configuredBatchSize) {
        configure(enableMl1, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                configuredBatchSize, DEFAULT_NUM_THREADS);
    }

    /**
     * Configure all ML1 inference runtime parameters.
     *
     * @param enableMl1 whether ML1 inference is enabled
     * @param configuredModelPath model path, or the bundled default when blank
     * @param configuredTokenizerPath tokenizer path, or the bundled default when blank
     * @param configuredMaxSequenceLength maximum number of tokenizer positions
     * @param configuredBatchSize number of rows processed per inference batch
     * @param configuredNumThreads number of ONNX runtime threads
     * @throws IllegalArgumentException if a numeric parameter is not positive
     */
    public static synchronized void configure(boolean enableMl1, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength, int configuredBatchSize,
            int configuredNumThreads) {
        if (configuredMaxSequenceLength <= 0) {
            throw new IllegalArgumentException("ML1 max sequence length must be greater than zero.");
        }
        if (configuredBatchSize <= 0) {
            throw new IllegalArgumentException("ML1 batch size must be greater than zero.");
        }
        if (configuredNumThreads <= 0) {
            throw new IllegalArgumentException("ML1 num threads must be greater than zero.");
        }

        enabled = enableMl1;
        modelPath = configuredModelPath == null || configuredModelPath.isBlank()
                ? DEFAULT_MODEL_PATH
                : configuredModelPath;
        tokenizerPath = configuredTokenizerPath == null || configuredTokenizerPath.isBlank()
                ? DEFAULT_TOKENIZER_PATH
                : configuredTokenizerPath;
        maxSequenceLength = configuredMaxSequenceLength;
        batchSize = configuredBatchSize;
        numThreads = configuredNumThreads;
    }

    /**
     * Return whether ML1 inference is enabled.
     *
     * @return {@code true} when ML1 inference should be available
     */
    public static boolean isEnabled() {
        return enabled;
    }

    /**
     * Return the configured ONNX model path.
     *
     * @return configured model path
     */
    public static String getModelPath() {
        return modelPath;
    }

    /**
     * Return the configured tokenizer path.
     *
     * @return configured tokenizer path
     */
    public static String getTokenizerPath() {
        return tokenizerPath;
    }

    /**
     * Return the maximum tokenizer sequence length.
     *
     * @return configured maximum sequence length
     */
    public static int getMaxSequenceLength() {
        return maxSequenceLength;
    }

    /**
     * Return the number of rows used for each ONNX inference batch.
     *
     * @return configured batch size
     */
    public static int getBatchSize() {
        return batchSize;
    }

    /**
     * Return the number of ONNX runtime threads.
     *
     * @return configured thread count
     */
    public static int getNumThreads() {
        return numThreads;
    }
}
