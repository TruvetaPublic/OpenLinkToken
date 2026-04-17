/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer.rotation;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Transforms a float embedding into a list of quantized rotation token strings.
 *
 * <p>The transformation pipeline for each configured rotation matrix is:
 * <ol>
 *   <li>Subtract per-dimension {@code bias} from the embedding (centring).</li>
 *   <li>Project the centred vector through the rotation matrix to obtain a
 *       {@code hashDimension}-dimensional float vector.</li>
 *   <li>Quantize the projected vector into a space-separated integer string.</li>
 * </ol>
 *
 * <p>Rotation matrices are generated lazily on the first call to
 * {@link #transform(float[])} and cached for subsequent calls.
 */
public final class RotationEmbeddingTransformer implements EmbeddingTransformer {

    private final String iv;
    private final int rotationCount;
    private final int dimension;
    private final int hashDimension;
    private final float[] bias;
    private final double minVal;
    private final double maxVal;
    private final double binWidth;

    /** Lazily initialized rotation matrices; volatile for double-checked locking. */
    private volatile List<double[][]> matrices;

    /**
     * Constructs a {@code RotationEmbeddingTransformer} with full parameter control.
     *
     * @param iv            initialization vector used to seed the rotation matrices
     * @param rotationCount number of rotation matrices (= number of output tokens)
     * @param dimension     dimension of the rotation matrices (must equal embedding.length)
     * @param hashDimension number of projected dimensions to quantize (k ≤ dimension)
     * @param bias          per-dimension bias subtracted before projection; length must equal dimension
     * @param minVal        quantizer lower bound
     * @param maxVal        quantizer upper bound
     * @param binWidth      quantizer bin width; must be &gt; 0
     * @throws IllegalArgumentException if any parameter is invalid
     */
    public RotationEmbeddingTransformer(
            String iv,
            int rotationCount,
            int dimension,
            int hashDimension,
            float[] bias,
            double minVal,
            double maxVal,
            double binWidth) {
        if (iv == null || iv.isBlank()) {
            throw new IllegalArgumentException("iv must not be null or blank");
        }
        if (rotationCount <= 0) {
            throw new IllegalArgumentException("rotationCount must be > 0");
        }
        if (dimension <= 0) {
            throw new IllegalArgumentException("dimension must be > 0");
        }
        if (hashDimension <= 0 || hashDimension > dimension) {
            throw new IllegalArgumentException("hashDimension must be in (0, dimension]");
        }
        if (bias == null || bias.length != dimension) {
            throw new IllegalArgumentException("bias must be non-null and have length == dimension");
        }
        if (binWidth <= 0) {
            throw new IllegalArgumentException("binWidth must be > 0");
        }

        this.iv = iv;
        this.rotationCount = rotationCount;
        this.dimension = dimension;
        this.hashDimension = hashDimension;
        this.bias = bias.clone();
        this.minVal = minVal;
        this.maxVal = maxVal;
        this.binWidth = binWidth;
        this.matrices = null;
    }

    /**
     * Creates a {@code RotationEmbeddingTransformer} with zero bias and default
     * quantizer parameters (range [-5.0, 5.0), bin width 0.05).
     *
     * @param iv            initialization vector
     * @param rotationCount number of rotation matrices
     * @param dimension     dimension of rotation matrices
     * @param hashDimension number of projected dimensions to quantize
     * @return new transformer instance
     */
    public static RotationEmbeddingTransformer withDefaults(
            String iv, int rotationCount, int dimension, int hashDimension) {
        float[] zeroBias = new float[dimension];
        return new RotationEmbeddingTransformer(
                iv, rotationCount, dimension, hashDimension, zeroBias,
                RotationQuantizer.DEFAULT_MIN, RotationQuantizer.DEFAULT_MAX, RotationQuantizer.DEFAULT_BIN_WIDTH);
    }

    /**
     * Transform an embedding into a list of quantized rotation token strings.
     *
     * <p>Returns {@code rotationCount} tokens, each a space-separated string of
     * {@code hashDimension} integer bin indices.
     *
     * @param embedding raw CLS float embedding vector; length must equal {@code dimension}
     * @return list of quantized token strings, one per rotation matrix
     */
    @Override
    public List<String> transform(float[] embedding) {
        ensureMatrices();
        List<float[]> projections = EmbeddingRotator.rotate(embedding, matrices, bias, hashDimension);
        return projections.stream()
                .map(p -> RotationQuantizer.quantize(p, minVal, maxVal, binWidth))
                .collect(Collectors.toList());
    }

    private synchronized void ensureMatrices() {
        if (matrices == null) {
            matrices = RotationMatrixGenerator.generate(iv, rotationCount, dimension, hashDimension);
        }
    }
}
