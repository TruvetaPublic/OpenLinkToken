/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import java.nio.file.Path;

/**
 * Runtime configuration for optional ONNX-backed ML1 token generation.
 */
public final class ML1InferenceConfig {

    public static final String DEFAULT_MODEL_PATH = "classpath:/inferencing/ml1/model.onnx";
    public static final String DEFAULT_TOKENIZER_PATH = "classpath:/inferencing/ml1/tokenizer.json";
    public static final String DEFAULT_ASSET_MANIFEST_PATH =
            "classpath:/inferencing/ml1/asset-manifest.json";
    public static final String DEFAULT_ASSET_REPOSITORY = "TruvetaPublic/OpenLinkToken";
    public static final String DEFAULT_ASSET_BASE_URL =
            "https://media.githubusercontent.com/media/" + DEFAULT_ASSET_REPOSITORY;
    public static final String DEFAULT_ASSET_RAW_BASE_URL =
            "https://raw.githubusercontent.com/" + DEFAULT_ASSET_REPOSITORY;
    public static final String DEFAULT_ASSET_REF = "release/2.1.1";
    public static final String ASSET_CACHE_DIR_ENVIRONMENT_VARIABLE = "OPENLINKTOKEN_ML1_CACHE_DIR";
    public static final String ASSET_REF_ENVIRONMENT_VARIABLE = "OPENLINKTOKEN_ML1_ASSET_REF";
    public static final String OFFLINE_ENVIRONMENT_VARIABLE = "OPENLINKTOKEN_ML1_OFFLINE";
    public static final String DEFAULT_ASSET_CACHE_DIRECTORY = Path.of(
            System.getProperty("user.home", "."),
            ".openlinktoken",
            "ml1").toAbsolutePath().normalize().toString();
    public static final int DEFAULT_MAX_SEQUENCE_LENGTH = 128;
    public static final int DEFAULT_BATCH_SIZE = 64;
    public static final int DEFAULT_NUM_THREADS = Runtime.getRuntime().availableProcessors();

    private static volatile boolean enabled = true;
    private static volatile String modelPath = DEFAULT_MODEL_PATH;
    private static volatile String tokenizerPath = DEFAULT_TOKENIZER_PATH;
    private static volatile String assetRef = environmentOrDefault(
            ASSET_REF_ENVIRONMENT_VARIABLE,
            DEFAULT_ASSET_REF);
    private static volatile String assetCacheDirectory = absoluteCacheDirectory(environmentOrDefault(
            ASSET_CACHE_DIR_ENVIRONMENT_VARIABLE,
            DEFAULT_ASSET_CACHE_DIRECTORY));
    private static volatile int maxSequenceLength = DEFAULT_MAX_SEQUENCE_LENGTH;
    private static volatile int batchSize = DEFAULT_BATCH_SIZE;
    private static volatile int numThreads = DEFAULT_NUM_THREADS;

    private ML1InferenceConfig() {
    }

    /**
     * Configure ML1 inference with the default batch size and thread count.
     *
     * @param enableMl1 whether ML1 inference is enabled
     * @param configuredModelPath model path, or the configured default when blank
     * @param configuredTokenizerPath tokenizer path, or the configured default when blank
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
     * @param configuredModelPath model path, or the configured default when blank
     * @param configuredTokenizerPath tokenizer path, or the configured default when blank
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
     * @param configuredModelPath model path, or the configured default when blank
     * @param configuredTokenizerPath tokenizer path, or the configured default when blank
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
     * Configure all ML1 runtime parameters, including optional asset storage overrides.
     *
     * @param enableMl1 whether ML1 inference is enabled
     * @param configuredModelPath model path, or the configured default when blank
     * @param configuredTokenizerPath tokenizer path, or the configured default when blank
     * @param configuredMaxSequenceLength maximum number of tokenizer positions
     * @param configuredBatchSize number of rows processed per inference batch
     * @param configuredNumThreads number of ONNX runtime threads
     * @param configuredAssetRef Git ref containing the ML1 assets, or null for the environment default
     * @param configuredCacheDirectory local cache directory, or null for the environment default
     */
    public static synchronized void configure(boolean enableMl1, String configuredModelPath,
            String configuredTokenizerPath, int configuredMaxSequenceLength, int configuredBatchSize,
            int configuredNumThreads, String configuredAssetRef, String configuredCacheDirectory) {
        configure(enableMl1, configuredModelPath, configuredTokenizerPath, configuredMaxSequenceLength,
                configuredBatchSize, configuredNumThreads);
        configureAssetStorage(configuredAssetRef, configuredCacheDirectory);
    }

    /**
     * Configure the ref and local cache used for lazy ML1 asset downloads.
     *
     * @param configuredAssetRef Git ref containing the ML1 assets
     * @param configuredAssetCacheDirectory local directory for downloaded assets
     */
    public static synchronized void configureAssetStorage(String configuredAssetRef,
            String configuredAssetCacheDirectory) {
        assetRef = configuredAssetRef == null || configuredAssetRef.isBlank()
                ? environmentOrDefault(ASSET_REF_ENVIRONMENT_VARIABLE, DEFAULT_ASSET_REF)
                : configuredAssetRef.trim();
        assetCacheDirectory = absoluteCacheDirectory(configuredAssetCacheDirectory == null
                || configuredAssetCacheDirectory.isBlank()
                ? environmentOrDefault(ASSET_CACHE_DIR_ENVIRONMENT_VARIABLE, DEFAULT_ASSET_CACHE_DIRECTORY)
                : configuredAssetCacheDirectory.trim());
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
     * Return the Git ref used for lazy ML1 asset downloads.
     *
     * @return configured asset ref
     */
    public static String getAssetRef() {
        return assetRef;
    }

    /**
     * Return the local directory used for lazy ML1 asset downloads.
     *
     * @return absolute asset cache directory
     */
    public static String getAssetCacheDirectory() {
        return assetCacheDirectory;
    }

    /**
     * Return whether remote ML1 asset downloads are disabled.
     *
     * @return {@code true} when {@code OPENLINKTOKEN_ML1_OFFLINE=1}
     */
    public static boolean isOffline() {
        String value = System.getenv(OFFLINE_ENVIRONMENT_VARIABLE);
        return value != null && "1".equals(value.trim());
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

    private static String environmentOrDefault(String variableName, String defaultValue) {
        String value = System.getenv(variableName);
        return value == null || value.isBlank() ? defaultValue : value.trim();
    }

    private static String absoluteCacheDirectory(String configuredDirectory) {
        String expanded = configuredDirectory.equals("~")
                ? System.getProperty("user.home", ".")
                : configuredDirectory.startsWith("~/")
                        ? Path.of(System.getProperty("user.home", "."))
                                .resolve(configuredDirectory.substring(2)).toString()
                        : configuredDirectory;
        return Path.of(expanded).toAbsolutePath().normalize().toString();
    }
}
