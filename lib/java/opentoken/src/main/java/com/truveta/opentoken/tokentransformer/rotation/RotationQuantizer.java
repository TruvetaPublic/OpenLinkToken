/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokentransformer.rotation;

import java.util.Arrays;

/**
 * Quantizes a float vector into a space-separated string of integer bin indices.
 *
 * <p>Each element of the input vector is mapped to a bin in the range
 * {@code [min, max)} using uniform bins of width {@code binWidth}.  Values
 * below {@code min} clamp to bin 0; values at or above {@code max} clamp to
 * the last bin.
 */
public final class RotationQuantizer {

    /** Default lower bound of the quantization range. */
    public static final double DEFAULT_MIN = -5.0;

    /** Default upper bound of the quantization range. */
    public static final double DEFAULT_MAX = 5.0;

    /** Default bin width. */
    public static final double DEFAULT_BIN_WIDTH = 0.05;

    private RotationQuantizer() {
    }

    /**
     * Quantize {@code x} using the default range [-5.0, 5.0) and bin width 0.05.
     *
     * @param x input float vector
     * @return space-separated string of integer bin indices
     */
    public static String quantize(float[] x) {
        return quantize(x, DEFAULT_MIN, DEFAULT_MAX, DEFAULT_BIN_WIDTH);
    }

    /**
     * Quantize {@code x} into uniform bins over the range {@code [min, max)}.
     *
     * <p>The number of bins is {@code ceil((max - min) / binWidth)}.  Each
     * value is floored into its bin and clamped to {@code [0, numBins - 1]}.
     *
     * @param x        input float vector
     * @param min      lower bound of the quantization range (inclusive)
     * @param max      upper bound of the quantization range (exclusive)
     * @param binWidth width of each bin; must be &gt; 0
     * @return space-separated string of integer bin indices, one per element of x
     */
    public static String quantize(float[] x, double min, double max, double binWidth) {
        int numBins = (int) Math.ceil((max - min) / binWidth);
        int[] bins = new int[x.length];
        for (int i = 0; i < x.length; i++) {
            int b = (int) Math.floor(((double) x[i] - min) / binWidth);
            bins[i] = Math.min(Math.max(b, 0), numBins - 1);
        }
        return String.join(" ", Arrays.stream(bins).mapToObj(String::valueOf).toArray(String[]::new));
    }
}
