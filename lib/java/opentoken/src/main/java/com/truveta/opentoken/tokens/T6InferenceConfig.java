/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

/**
 * Runtime configuration for optional ONNX-backed T6 token generation.
 */
public final class T6InferenceConfig {

    public static final String DEFAULT_MODEL_PATH = "classpath:/t6/model_int8.onnx";
    public static final String DEFAULT_TOKENIZER_PATH = "classpath:/t6/tokenizer.json";
    public static final int DEFAULT_MAX_SEQUENCE_LENGTH = 128;
    public static final int DEFAULT_BATCH_SIZE = 64;
    public static final int DEFAULT_NUM_THREADS = Runtime.getRuntime().availableProcessors();

    private static volatile boolean enabled = true;
    private static volatile String modelPath = DEFAULT_MODEL_PATH;
    private static volatile String tokenizerPath = DEFAULT_TOKENIZER_PATH;
    private static volatile int maxSequenceLength = DEFAULT_MAX_SEQUENCE_LENGTH;
    private static volatile int batchSize = DEFAULT_BATCH_SIZE;
    private static volatile int numThreads = DEFAULT_NUM_THREADS;

    private T6InferenceConfig() {
    }

    public static synchronized void configure(boolean enableT6, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength) {
        configure(enableT6, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                DEFAULT_BATCH_SIZE);
    }

    public static synchronized void configure(boolean enableT6, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength, int configuredBatchSize) {
        configure(enableT6, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                configuredBatchSize, DEFAULT_NUM_THREADS);
    }

    public static synchronized void configure(boolean enableT6, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength, int configuredBatchSize,
            int configuredNumThreads) {
        if (configuredMaxSequenceLength <= 0) {
            throw new IllegalArgumentException("T6 max sequence length must be greater than zero.");
        }
        if (configuredBatchSize <= 0) {
            throw new IllegalArgumentException("T6 batch size must be greater than zero.");
        }
        if (configuredNumThreads <= 0) {
            throw new IllegalArgumentException("T6 num threads must be greater than zero.");
        }

        enabled = enableT6;
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
