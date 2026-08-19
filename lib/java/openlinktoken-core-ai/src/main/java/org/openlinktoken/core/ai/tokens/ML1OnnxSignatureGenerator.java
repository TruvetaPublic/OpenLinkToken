/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ForkJoinPool;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import org.apache.commons.codec.binary.Hex;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ai.djl.Device;
import ai.djl.ModelException;
import ai.djl.util.cuda.CudaUtils;
import ai.djl.huggingface.tokenizers.Encoding;
import ai.djl.huggingface.tokenizers.HuggingFaceTokenizer;
import ai.djl.inference.Predictor;
import ai.djl.ndarray.NDArray;
import ai.djl.ndarray.NDList;
import ai.djl.ndarray.NDManager;
import ai.djl.repository.zoo.Criteria;
import ai.djl.repository.zoo.ZooModel;
import ai.djl.translate.NoopTranslator;
import ai.djl.translate.TranslateException;

/**
 * Generates deterministic ML1 signatures from ONNX CLS embeddings using DJL.
 */
public final class ML1OnnxSignatureGenerator {
    private static final Logger LOGGER = LoggerFactory.getLogger(ML1OnnxSignatureGenerator.class);
    private static final String ASSET_RESOURCE_PREFIX = "inferencing/ml1/";
    private static ZooModel<NDList, NDList> model;
    private static Predictor<NDList, NDList> predictor;
    private static HuggingFaceTokenizer tokenizer;
    private static Set<String> modelInputNames;
    private static String activeModelPath;
    private static String activeTokenizerPath;
    private static final String PAD_INPUT_JSON = "{}";

    private ML1OnnxSignatureGenerator() {
    }

    /**
     * Generates a ML1 signature for the given JSON-formatted input row.
     *
     * @param inputJson JSON string representing a single person record
     * @return hex-encoded CLS embedding signature
     */
    public static synchronized String generateSignature(String inputJson) {
        List<String> signatures = generateSignatures(List.of(inputJson));
        if (signatures.isEmpty()) {
            throw new IllegalStateException("Failed to generate ONNX-based ML1 signature.");
        }
        return signatures.get(0);
    }

    /**
     * Generates ML1 signatures for multiple JSON-formatted input rows using batched ONNX inference.
     *
     * @param inputJsonRows list of JSON strings representing person records
     * @return list of hex-encoded CLS embedding signatures in the same order
     */
    public static List<String> generateSignatures(List<String> inputJsonRows) {
        return generateSignaturesAndEmbeddings(inputJsonRows).signatures();
    }

    /**
     * Generates both hex-encoded ML1 signatures and CLS embedding vectors in a single
     * inference pass.
     *
     * <p>The embeddings are retained internally for ML1 rotation.
     *
     * @param inputJsonRows list of JSON strings representing person records
     * @return a {@link GenerationResult} containing parallel lists of hex signatures and
     *         embeddings in the same order as the input
     */
    static GenerationResult generateSignaturesAndEmbeddings(List<String> inputJsonRows) {
        if (inputJsonRows == null || inputJsonRows.isEmpty()) {
            return new GenerationResult(List.of(), List.of());
        }

        try {
            initializeIfNeeded();

            int configuredBatchSize = ML1InferenceConfig.getBatchSize();
            List<String> signatures = new ArrayList<>(inputJsonRows.size());
            List<float[]> allEmbeddings = new ArrayList<>(inputJsonRows.size());
            double totalInferenceMillis = 0.0;

            for (int start = 0; start < inputJsonRows.size(); start += configuredBatchSize) {
                int end = Math.min(start + configuredBatchSize, inputJsonRows.size());
                List<String> realBatch = inputJsonRows.subList(start, end);
                List<String> inferenceBatch = new ArrayList<>(configuredBatchSize);
                inferenceBatch.addAll(realBatch);
                while (inferenceBatch.size() < configuredBatchSize) {
                    inferenceBatch.add(PAD_INPUT_JSON);
                }

                BatchRunResult batchRunResult = runBatchInference(inferenceBatch);
                float[][] embeddings = batchRunResult.embeddings();
                double inferenceElapsedMillis = batchRunResult.elapsedMillis();
                totalInferenceMillis += inferenceElapsedMillis;

                for (int i = 0; i < realBatch.size(); i++) {
                    signatures.add(serializeEmbedding(embeddings[i]));
                    allEmbeddings.add(embeddings[i]);
                }

                if (LOGGER.isInfoEnabled()) {
                    LOGGER.info(
                            "ML1 ONNX batch inference: requestedSize={}, inferenceSize={}, totalMs={}, avgMsPerRow={}",
                            realBatch.size(), inferenceBatch.size(), inferenceElapsedMillis,
                            inferenceElapsedMillis / realBatch.size());
                }
            }

            if (LOGGER.isInfoEnabled()) {
                LOGGER.info("ML1 ONNX batch inference summary: rowCount={}, totalMs={}, avgMsPerRow={}",
                        inputJsonRows.size(), totalInferenceMillis, totalInferenceMillis / inputJsonRows.size());
            }

            return new GenerationResult(signatures, allEmbeddings);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to generate ONNX-based ML1 signatures.", e);
        }
    }

    /**
     * Bundles ML1 hex signatures and embeddings generated in one inference pass.
     *
     * <p>{@code signatures} and {@code embeddings} are parallel lists: index {@code i}
     * of each list corresponds to the same input row.
     *
     * @param signatures    hex-encoded CLS embedding signatures
     * @param embeddings CLS embedding float vectors
     */
    record GenerationResult(List<String> signatures, List<float[]> embeddings) {
    }

    /**
     * Run one padded inference batch and record its elapsed time.
     */
    private static BatchRunResult runBatchInference(List<String> inferenceBatch) throws TranslateException {
        long inferenceStartNanos = System.nanoTime();
        float[][] embeddings = generateEmbeddings(inferenceBatch);
        long inferenceElapsedNanos = System.nanoTime() - inferenceStartNanos;
        double inferenceElapsedMillis = inferenceElapsedNanos / 1_000_000.0;
        return new BatchRunResult(embeddings, inferenceElapsedMillis);
    }

    private record BatchRunResult(float[][] embeddings, double elapsedMillis) {
        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof BatchRunResult that)) {
                return false;
            }
            return Double.compare(that.elapsedMillis, elapsedMillis) == 0
                    && Arrays.deepEquals(embeddings, that.embeddings);
        }

        @Override
        public int hashCode() {
            int result = Arrays.deepHashCode(embeddings);
            result = 31 * result + Objects.hash(elapsedMillis);
            return result;
        }

        @Override
        public String toString() {
            return "BatchRunResult[embeddings=" + Arrays.deepToString(embeddings)
                    + ", elapsedMillis=" + elapsedMillis + "]";
        }
    }

    /**
     * Load the configured ONNX model and tokenizer when they are not already active.
     */
    private static void initializeIfNeeded() throws IOException, ModelException {
        String modelPath = ML1InferenceConfig.getModelPath();
        String tokenizerPath = ML1InferenceConfig.getTokenizerPath();
        boolean alreadyInitialized = model != null
                && tokenizer != null
                && modelPath.equals(activeModelPath)
                && tokenizerPath.equals(activeTokenizerPath);
        if (alreadyInitialized) {
            return;
        }

        closeModel();
        Path resolvedModelPath = resolvePath(modelPath);
        if (resolvedModelPath.getFileName().toString().equals("model.onnx")) {
            Path dataPath = resolvedModelPath.resolveSibling("model.onnx.data");
            if (!Files.isRegularFile(dataPath)) {
                throw new IllegalStateException(
                        "ML1 model data file not found beside the model: " + dataPath
                                + ". Place model.onnx.data beside model.onnx.");
            }
        }
        Path resolvedTokenizerPath = resolvePath(tokenizerPath);

        int numThreads = ML1InferenceConfig.getNumThreads();
        String modelName = resolvedModelPath.getFileName().toString().replaceFirst("\\.onnx$", "");

        Criteria<NDList, NDList> criteria = Criteria.builder()
                .setTypes(NDList.class, NDList.class)
                .optModelPath(resolvedModelPath.getParent())
                .optModelName(modelName)
                .optEngine("OnnxRuntime")
                .optDevice(selectInferenceDevice())
                .optOption("intraOpNumThreads", String.valueOf(numThreads))
                .optOption("interOpNumThreads", String.valueOf(numThreads))
                .optOption("executionMode", "PARALLEL")
                .optOption("optimizeLevel", "ALL_OPT")
                .optTranslator(new NoopTranslator())
                .build();

        model = criteria.loadModel();
        predictor = model.newPredictor();

        modelInputNames = model.describeInput().stream()
                .map(pair -> pair.getKey())
                .collect(Collectors.toSet());

        Map<String, String> tokenizerOptions = new HashMap<>();
        tokenizerOptions.put("maxLength", String.valueOf(ML1InferenceConfig.getMaxSequenceLength()));
        tokenizer = HuggingFaceTokenizer.newInstance(resolvedTokenizerPath, tokenizerOptions);
        activeModelPath = modelPath;
        activeTokenizerPath = tokenizerPath;
    }

    /**
     * Select CUDA when available and otherwise use the CPU execution device.
     */
    private static Device selectInferenceDevice() {
        if (CudaUtils.getGpuCount() > 0) {
            LOGGER.info("ML1 inference: CUDA GPU available, using GPU acceleration");
            return Device.gpu();
        }
        String osName = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        if (osName.contains("mac")) {
            LOGGER.info("ML1 inference: macOS detected, OnnxRuntime will use CoreML execution provider where available");
        } else {
            LOGGER.info("ML1 inference: No GPU detected, using CPU");
        }
        return Device.cpu();
    }

    /**
     * Tokenize rows, build model inputs, run ONNX inference, and extract CLS embeddings.
     */
    private static float[][] generateEmbeddings(List<String> inputJsonRows) throws TranslateException {
        int maxSequenceLength = ML1InferenceConfig.getMaxSequenceLength();

        // Tokenize in parallel across available processors
        Encoding[] encodings = new Encoding[inputJsonRows.size()];
        ForkJoinPool.commonPool()
                .submit(() -> IntStream.range(0, inputJsonRows.size()).parallel().forEach(i -> {
                    try {
                        encodings[i] = tokenizer.encode(inputJsonRows.get(i));
                    } catch (Exception e) {
                        throw new RuntimeException("Tokenization failed for index " + i, e);
                    }
                })).join();

        // Dynamic padding: pad only to the actual max token length in this batch
        int dynamicMax = 1;
        for (Encoding enc : encodings) {
            dynamicMax = Math.max(dynamicMax, enc.getIds().length);
        }
        int seqLen = Math.min(dynamicMax, maxSequenceLength);

        long[][] inputIdsBatch = new long[inputJsonRows.size()][seqLen];
        long[][] attentionMaskBatch = new long[inputJsonRows.size()][seqLen];
        long[][] tokenTypeIdsBatch = new long[inputJsonRows.size()][seqLen];
        long[][] positionIdsBatch = new long[inputJsonRows.size()][seqLen];

        for (int i = 0; i < inputJsonRows.size(); i++) {
            inputIdsBatch[i] = toFixedLength(encodings[i].getIds(), seqLen);
            attentionMaskBatch[i] = toFixedLength(encodings[i].getAttentionMask(), seqLen);
            tokenTypeIdsBatch[i] = toFixedLength(encodings[i].getTypeIds(), seqLen);
            positionIdsBatch[i] = createPositionIds(seqLen);
        }

        try (NDManager manager = NDManager.newBaseManager("OnnxRuntime")) {
            NDList inputs = new NDList();

            NDArray inputIdsArray = manager.create(inputIdsBatch);
            inputIdsArray.setName("input_ids");
            inputs.add(inputIdsArray);

            NDArray attentionMaskArray = manager.create(attentionMaskBatch);
            attentionMaskArray.setName("attention_mask");
            inputs.add(attentionMaskArray);

            if (modelInputNames.contains("token_type_ids")) {
                NDArray tokenTypeIdsArray = manager.create(tokenTypeIdsBatch);
                tokenTypeIdsArray.setName("token_type_ids");
                inputs.add(tokenTypeIdsArray);
            }
            if (modelInputNames.contains("position_ids")) {
                NDArray positionIdsArray = manager.create(positionIdsBatch);
                positionIdsArray.setName("position_ids");
                inputs.add(positionIdsArray);
            }

            try (NDList output = predictor.predict(inputs)) {
                NDArray outputArray = output.get(0);
                int batchSize = inputJsonRows.size();
                float[][] result = new float[batchSize][];

                // Output shape [batch, seq_len, hidden]: extract CLS token (index 0)
                if (outputArray.getShape().dimension() == 3) {
                    for (int i = 0; i < batchSize; i++) {
                        result[i] = outputArray.get(i).get(0).toFloatArray();
                    }
                } else {
                    // Output shape [batch, hidden]: use directly
                    for (int i = 0; i < batchSize; i++) {
                        result[i] = outputArray.get(i).toFloatArray();
                    }
                }

                return result;
            }
        }
    }

    /**
     * Copy values into a zero-padded array truncated to the requested length.
     */
    private static long[] toFixedLength(long[] values, int maxSequenceLength) {
        long[] response = new long[maxSequenceLength];
        if (values == null || values.length == 0) {
            return response;
        }
        int copyLength = Math.min(values.length, maxSequenceLength);
        System.arraycopy(values, 0, response, 0, copyLength);
        return response;
    }

    /**
     * Create sequential position IDs from zero through {@code maxSequenceLength - 1}.
     */
    private static long[] createPositionIds(int maxSequenceLength) {
        long[] positionIds = new long[maxSequenceLength];
        for (int i = 0; i < maxSequenceLength; i++) {
            positionIds[i] = i;
        }
        return positionIds;
    }

    /**
     * Close the active predictor and model before re-initialization.
     */
    private static void closeModel() {
        if (predictor != null) {
            try {
                predictor.close();
            } catch (Exception ignored) {
                // Best-effort close before re-initialization.
            } finally {
                predictor = null;
            }
        }
        if (model != null) {
            try {
                model.close();
            } catch (Exception ignored) {
                // Best-effort close before re-initialization.
            } finally {
                model = null;
            }
        }
    }

    /**
     * Resolve a configured filesystem or classpath resource path.
     */
    static Path resolvePath(String configuredPath) {
        if (configuredPath == null || configuredPath.isBlank()) {
            throw new IllegalArgumentException("ML1 asset path must not be blank.");
        }
        if (configuredPath != null && configuredPath.startsWith("classpath:")) {
            return extractClasspathResource(configuredPath.substring("classpath:".length()));
        }
        Path resolved = Paths.get(configuredPath).toAbsolutePath().normalize();
        if (!Files.isRegularFile(resolved)) {
            throw new IllegalStateException("Configured ML1 asset path does not exist: " + resolved);
        }
        return resolved;
    }

    /**
     * Resolve a classpath resource, extracting it to a temporary file when necessary.
     */
    private static Path extractClasspathResource(String resourcePath) {
        String normalized = resourcePath.startsWith("/") ? resourcePath.substring(1) : resourcePath;

        // Try bundled classpath first (packaged JARs with embedded resources)
        try (InputStream stream = ML1OnnxSignatureGenerator.class.getClassLoader().getResourceAsStream(normalized)) {
            if (stream != null) {
                Path tempDir = Files.createTempDirectory("ml1-assets-");
                tempDir.toFile().deleteOnExit();
                Path target = tempDir.resolve(Paths.get(normalized).getFileName().toString());
                Files.copy(stream, target, StandardCopyOption.REPLACE_EXISTING);
                target.toFile().deleteOnExit();

                if (normalized.endsWith(".onnx")) {
                    String dataResource = normalized + ".data";
                    try (InputStream dataStream = ML1OnnxSignatureGenerator.class.getClassLoader()
                            .getResourceAsStream(dataResource)) {
                        if (dataStream != null) {
                            Path dataTarget = tempDir.resolve(Paths.get(dataResource).getFileName().toString());
                            Files.copy(dataStream, dataTarget, StandardCopyOption.REPLACE_EXISTING);
                            dataTarget.toFile().deleteOnExit();
                        }
                    }
                }

                return target;
            }
        } catch (IOException e) {
            throw new IllegalStateException("Failed to extract classpath resource: " + normalized, e);
        }

        Path sourceCheckoutPath = findSourceCheckoutPath(normalized);
        if (sourceCheckoutPath != null) {
            return sourceCheckoutPath;
        }

        throw new IllegalStateException(
                "ML1 resource not found on the classpath or filesystem: " + normalized
                        + ". Core-AI packages do not download ML1 assets. Add the file to "
                        + "inferencing/ml1/ on the application classpath, place it at "
                        + "resources/" + normalized + " in a source checkout, or configure an explicit "
                        + "filesystem path.");
    }

    private static Path findSourceCheckoutPath(String normalized) {
        Path current = Paths.get(System.getProperty("user.dir")).toAbsolutePath().normalize();
        while (current != null) {
            Path candidate = current.resolve("resources").resolve(normalized);
            if (Files.isRegularFile(candidate)) {
                return candidate;
            }
            current = current.getParent();
        }
        return null;
    }

    /**
     * Serialize an embedding as a big-endian, IEEE-754 float bit-pattern hex string.
     */
    private static String serializeEmbedding(float[] embedding) {
        ByteBuffer buffer = ByteBuffer.allocate(embedding.length * Float.BYTES).order(ByteOrder.BIG_ENDIAN);
        for (float value : embedding) {
            buffer.putInt(Float.floatToIntBits(value));
        }
        return Hex.encodeHexString(buffer.array());
    }
}
