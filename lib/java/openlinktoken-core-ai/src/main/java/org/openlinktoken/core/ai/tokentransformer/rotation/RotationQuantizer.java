/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokentransformer.rotation;

import java.util.Arrays;

/**
 * Quantizes a float vector into a space-separated string of integer bin indices.
 *
 * <p>Each element of the input vector is mapped to a bin in the range
 * {@code [min, max]} using uniform bins of width {@code binWidth}. Values are
 * clamped to that range before their bin index is calculated with Python-compatible
 * floating-point floor division.
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
     * Quantize {@code x} using the default range [-5.0, 5.0] and bin width 0.05.
     *
     * @param x input float vector
     * @return space-separated string of integer bin indices
     */
    public static String quantize(float[] x) {
        return quantize(x, DEFAULT_MIN, DEFAULT_MAX, DEFAULT_BIN_WIDTH);
    }

    /**
     * Quantize {@code x} into uniform bins over the range {@code [min, max]}.
     *
     * <p>Each value is clamped to {@code [min, max]} and placed in the bin from
     * {@code int((value - min) // binWidth)}, reproducing Python float floor-division
     * semantics.
     *
     * @param x        input float vector
     * @param min      lower bound of the quantization range (inclusive)
     * @param max      upper bound of the quantization range (inclusive)
     * @param binWidth width of each bin; must be &gt; 0
     * @return space-separated string of integer bin indices, one per element of x
     */
    public static String quantize(float[] x, double min, double max, double binWidth) {
        int[] bins = new int[x.length];
        for (int i = 0; i < x.length; i++) {
            double clampedValue = Math.max(min, Math.min((double) x[i], max));
            bins[i] = (int) pythonFloorDivide(clampedValue - min, binWidth);
        }
        return String.join(" ", Arrays.stream(bins).mapToObj(String::valueOf).toArray(String[]::new));
    }

    /**
     * Perform floor division with the floating-point behavior used by Python.
     */
    private static double pythonFloorDivide(double dividend, double divisor) {
        double remainder = dividend % divisor;
        double quotient = (dividend - remainder) / divisor;
        if (remainder != 0.0 && (divisor < 0.0) != (remainder < 0.0)) {
            quotient -= 1.0;
        }

        if (quotient == 0.0) {
            return Math.copySign(0.0, dividend / divisor);
        }

        double flooredQuotient = Math.floor(quotient);
        return quotient - flooredQuotient > 0.5 ? flooredQuotient + 1.0 : flooredQuotient;
    }
}
