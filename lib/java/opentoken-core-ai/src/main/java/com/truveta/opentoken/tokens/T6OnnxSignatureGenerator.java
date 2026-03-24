/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

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
 * Generates deterministic T6 signatures from ONNX CLS embeddings using DJL.
 */
public final class T6OnnxSignatureGenerator {
    private static final Logger LOGGER = LoggerFactory.getLogger(T6OnnxSignatureGenerator.class);
    private static ZooModel<NDList, NDList> model;
    private static Predictor<NDList, NDList> predictor;
    private static HuggingFaceTokenizer tokenizer;
    private static Set<String> modelInputNames;
    private static String activeModelPath;
    private static String activeTokenizerPath;
    private static final String PAD_INPUT_JSON = "{}";

    private T6OnnxSignatureGenerator() {
    }

    /**
     * Generates a T6 signature for the given JSON-formatted input row.
     *
     * @param inputJson JSON string representing a single person record
     * @return hex-encoded CLS embedding signature
     */
    public static synchronized String generateSignature(String inputJson) {
        List<String> signatures = generateSignatures(List.of(inputJson));
        if (signatures.isEmpty()) {
            throw new IllegalStateException("Failed to generate ONNX-based T6 signature.");
        }
        return signatures.get(0);
    }

    /**
     * Generates T6 signatures for multiple JSON-formatted input rows using batched ONNX inference.
     *
     * @param inputJsonRows list of JSON strings representing person records
     * @return list of hex-encoded CLS embedding signatures in the same order
     */
    public static List<String> generateSignatures(List<String> inputJsonRows) {
        return generateSignaturesAndRawEmbeddings(inputJsonRows).signatures();
    }

    /**
     * Generates raw CLS embedding float vectors for multiple JSON-formatted input rows.
     *
     * <p>This performs the same batched ONNX inference as {@link #generateSignatures} but
     * returns raw {@code float[]} vectors instead of hex-encoded strings, suitable for
     * rotation-based token generation.
     *
     * @param inputJsonRows list of JSON strings representing person records
     * @return list of {@code float[]} CLS embedding vectors in the same order
     */
    public static List<float[]> generateRawEmbeddings(List<String> inputJsonRows) {
        return generateSignaturesAndRawEmbeddings(inputJsonRows).rawEmbeddings();
    }

    /**
     * Generates both hex-encoded T6 signatures and raw CLS embedding vectors in a single
     * inference pass.
     *
     * <p>Use this when both the T6 token and rotation tokens are needed to avoid
     * running ONNX inference twice.
     *
     * @param inputJsonRows list of JSON strings representing person records
     * @return a {@link GenerationResult} containing parallel lists of hex signatures and
     *         raw float embeddings in the same order as the input
     */
    public static GenerationResult generateSignaturesAndRawEmbeddings(List<String> inputJsonRows) {
        if (inputJsonRows == null || inputJsonRows.isEmpty()) {
            return new GenerationResult(List.of(), List.of());
        }

        try {
            initializeIfNeeded();

            int configuredBatchSize = T6InferenceConfig.getBatchSize();
            List<String> signatures = new ArrayList<>(inputJsonRows.size());
            List<float[]> rawEmbeddings = new ArrayList<>(inputJsonRows.size());
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
                        rawEmbeddings.add(embeddings[i]);
                    }

                if (LOGGER.isInfoEnabled()) {
                    LOGGER.info(
                            "T6 ONNX batch inference: requestedSize={}, inferenceSize={}, totalMs={}, avgMsPerRow={}",
                            realBatch.size(), inferenceBatch.size(), inferenceElapsedMillis,
                            inferenceElapsedMillis / realBatch.size());
                }
            }

            if (LOGGER.isInfoEnabled()) {
                LOGGER.info("T6 ONNX batch inference summary: rowCount={}, totalMs={}, avgMsPerRow={}",
                        inputJsonRows.size(), totalInferenceMillis, totalInferenceMillis / inputJsonRows.size());
            }

            return new GenerationResult(signatures, rawEmbeddings);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to generate ONNX-based T6 signatures.", e);
        }
    }

    /**
     * Bundles T6 hex signatures and raw float embeddings generated in one inference pass.
     *
     * <p>{@code signatures} and {@code rawEmbeddings} are parallel lists: index {@code i}
     * of each list corresponds to the same input row.
     *
     * @param signatures    hex-encoded CLS embedding signatures
     * @param rawEmbeddings raw CLS embedding float vectors
     */
    public record GenerationResult(List<String> signatures, List<float[]> rawEmbeddings) {
    }

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

    private static void initializeIfNeeded() throws IOException, ModelException {
        String modelPath = T6InferenceConfig.getModelPath();
        String tokenizerPath = T6InferenceConfig.getTokenizerPath();
        boolean alreadyInitialized = model != null
                && tokenizer != null
                && modelPath.equals(activeModelPath)
                && tokenizerPath.equals(activeTokenizerPath);
        if (alreadyInitialized) {
            return;
        }

        closeModel();
        Path resolvedModelPath = resolvePath(modelPath);
        Path resolvedTokenizerPath = resolvePath(tokenizerPath);

        int numThreads = T6InferenceConfig.getNumThreads();
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
        tokenizerOptions.put("maxLength", String.valueOf(T6InferenceConfig.getMaxSequenceLength()));
        tokenizer = HuggingFaceTokenizer.newInstance(resolvedTokenizerPath, tokenizerOptions);
        activeModelPath = modelPath;
        activeTokenizerPath = tokenizerPath;
    }

    private static Device selectInferenceDevice() {
        if (CudaUtils.getGpuCount() > 0) {
            LOGGER.info("T6 inference: CUDA GPU available, using GPU acceleration");
            return Device.gpu();
        }
        String osName = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        if (osName.contains("mac")) {
            LOGGER.info("T6 inference: macOS detected, OnnxRuntime will use CoreML execution provider where available");
        } else {
            LOGGER.info("T6 inference: No GPU detected, using CPU");
        }
        return Device.cpu();
    }

    private static float[][] generateEmbeddings(List<String> inputJsonRows) throws TranslateException {
        int maxSequenceLength = T6InferenceConfig.getMaxSequenceLength();

        // Tokenize in parallel across available processors
        Encoding[] encodings = new Encoding[inputJsonRows.size()];
        ForkJoinPool.commonPool()
                .submit(() -> java.util.stream.IntStream.range(0, inputJsonRows.size()).parallel().forEach(i -> {
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

    private static long[] toFixedLength(long[] values, int maxSequenceLength) {
        long[] response = new long[maxSequenceLength];
        if (values == null || values.length == 0) {
            return response;
        }
        int copyLength = Math.min(values.length, maxSequenceLength);
        System.arraycopy(values, 0, response, 0, copyLength);
        return response;
    }

    private static long[] createPositionIds(int maxSequenceLength) {
        long[] positionIds = new long[maxSequenceLength];
        for (int i = 0; i < maxSequenceLength; i++) {
            positionIds[i] = i;
        }
        return positionIds;
    }

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

    private static Path resolvePath(String configuredPath) {
        if (configuredPath != null && configuredPath.startsWith("classpath:")) {
            return extractClasspathResource(configuredPath.substring("classpath:".length()));
        }
        return Paths.get(configuredPath);
    }

    private static Path extractClasspathResource(String resourcePath) {
        String normalized = resourcePath.startsWith("/") ? resourcePath.substring(1) : resourcePath;

        // Try bundled classpath first (packaged JARs with embedded resources)
        try (InputStream stream = T6OnnxSignatureGenerator.class.getClassLoader().getResourceAsStream(normalized)) {
            if (stream != null) {
                Path tempDir = Files.createTempDirectory("t6-assets-");
                tempDir.toFile().deleteOnExit();
                Path target = tempDir.resolve(Paths.get(normalized).getFileName().toString());
                Files.copy(stream, target, StandardCopyOption.REPLACE_EXISTING);
                target.toFile().deleteOnExit();

                if (normalized.endsWith(".onnx")) {
                    String dataResource = normalized + ".data";
                    try (InputStream dataStream = T6OnnxSignatureGenerator.class.getClassLoader()
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

        // Filesystem fallback: walk up from the working directory to find resources/<normalized>
        Path current = Paths.get(System.getProperty("user.dir"));
        while (current != null) {
            Path candidate = current.resolve("resources").resolve(normalized);
            if (Files.exists(candidate)) {
                return candidate;
            }
            current = current.getParent();
        }

        throw new IllegalStateException(
                "T6 resource not found on classpath or filesystem. "
                        + "Configure an explicit path or place the file at: resources/" + normalized);
    }

    private static String serializeEmbedding(float[] embedding) {
        ByteBuffer buffer = ByteBuffer.allocate(embedding.length * Float.BYTES).order(ByteOrder.BIG_ENDIAN);
        for (float value : embedding) {
            buffer.putInt(Float.floatToIntBits(value));
        }
        return Hex.encodeHexString(buffer.array());
    }
}
