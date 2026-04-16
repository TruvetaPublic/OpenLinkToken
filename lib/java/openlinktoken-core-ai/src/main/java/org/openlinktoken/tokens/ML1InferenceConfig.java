/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

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

    public static synchronized void configure(boolean enableMl1, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength) {
        configure(enableMl1, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                DEFAULT_BATCH_SIZE);
    }

    public static synchronized void configure(boolean enableMl1, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength, int configuredBatchSize) {
        configure(enableMl1, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                configuredBatchSize, DEFAULT_NUM_THREADS);
    }

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

    public static boolean isEnabled() {
        return enabled;
    }

    public static String getModelPath() {
        return modelPath;
    }

    public static String getTokenizerPath() {
        return tokenizerPath;
    }

    public static int getMaxSequenceLength() {
        return maxSequenceLength;
    }

    public static int getBatchSize() {
        return batchSize;
    }

    public static int getNumThreads() {
        return numThreads;
    }
}
