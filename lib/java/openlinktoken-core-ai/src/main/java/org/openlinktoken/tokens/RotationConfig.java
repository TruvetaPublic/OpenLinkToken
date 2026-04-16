/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

/**
 * Runtime configuration for rotation-based T6 token generation.
 *
 * <p>This is a static thread-safe configuration class that mirrors the pattern
 * established by {@link T6InferenceConfig}.  All setters are {@code synchronized}
 * and all getters read {@code volatile} fields so that configuration changes are
 * immediately visible to reader threads without additional locking.
 */
public final class RotationConfig {

    /** Default number of rotation matrices (= number of rotation tokens per record). */
    public static final int DEFAULT_ROTATION_COUNT = 30;

    /** Default number of projected dimensions fed to the quantizer. */
    public static final int DEFAULT_HASH_DIMENSION = 4;

    /** Default quantizer bin width. */
    public static final double DEFAULT_BIN_WIDTH = 0.05;

    /** Default quantizer lower bound. */
    public static final double DEFAULT_MIN_VAL = -5.0;

    /** Default quantizer upper bound. */
    public static final double DEFAULT_MAX_VAL = 5.0;

    /** Default initialization vector used when rotation is enabled without an explicit IV. */
    public static final String DEFAULT_IV = "opentoken-t6-v1";

    private static volatile boolean enabled = true;
    private static volatile String rotationIv = DEFAULT_IV;
    private static volatile int rotationCount = DEFAULT_ROTATION_COUNT;
    private static volatile int hashDimension = DEFAULT_HASH_DIMENSION;
    private static volatile double binWidth = DEFAULT_BIN_WIDTH;
    private static volatile double minVal = DEFAULT_MIN_VAL;
    private static volatile double maxVal = DEFAULT_MAX_VAL;

    private RotationConfig() {
    }

    /**
     * Apply rotation configuration using default quantizer parameters.
     *
     * <p>When {@code enable} is {@code true} and {@code iv} is {@code null} or blank,
     * the IV falls back to {@link #DEFAULT_IV}.
     *
     * @param enable whether rotation tokens are active
     * @param iv     initialization vector used to seed rotation matrices;
     *               may be {@code null} or blank when {@code enable} is {@code false},
     *               or to accept the default IV when {@code enable} is {@code true}
     */
    public static synchronized void configure(boolean enable, String iv) {
        enabled = enable;
        if (enable && (iv == null || iv.isBlank())) {
            rotationIv = DEFAULT_IV;
        } else {
            rotationIv = iv;
        }
        rotationCount = DEFAULT_ROTATION_COUNT;
        hashDimension = DEFAULT_HASH_DIMENSION;
        binWidth = DEFAULT_BIN_WIDTH;
        minVal = DEFAULT_MIN_VAL;
        maxVal = DEFAULT_MAX_VAL;
    }

    /**
     * Apply rotation configuration with full parameter control.
     *
     * <p>When {@code enable} is {@code true} and {@code iv} is {@code null} or blank,
     * the IV falls back to {@link #DEFAULT_IV}.
     *
     * @param enable               whether rotation tokens are active
     * @param iv                   initialization vector; may be {@code null} or blank when
     *                             {@code enable} is {@code false}, or to accept the default IV
     * @param configuredRotationCount number of rotation matrices; must be &gt; 0
     * @param configuredHashDimension number of projected dimensions; must be &gt; 0
     * @param configuredBinWidth   quantizer bin width; must be &gt; 0
     * @param configuredMinVal     quantizer lower bound
     * @param configuredMaxVal     quantizer upper bound
     * @throws IllegalArgumentException if any numeric parameter violates its constraint
     */
    public static synchronized void configure(
            boolean enable,
            String iv,
            int configuredRotationCount,
            int configuredHashDimension,
            double configuredBinWidth,
            double configuredMinVal,
            double configuredMaxVal) {
        if (configuredRotationCount <= 0) {
            throw new IllegalArgumentException("rotationCount must be greater than zero.");
        }
        if (configuredHashDimension <= 0) {
            throw new IllegalArgumentException("hashDimension must be greater than zero.");
        }
        if (configuredBinWidth <= 0) {
            throw new IllegalArgumentException("binWidth must be greater than zero.");
        }

        enabled = enable;
        if (enable && (iv == null || iv.isBlank())) {
            rotationIv = DEFAULT_IV;
        } else {
            rotationIv = iv;
        }
        rotationCount = configuredRotationCount;
        hashDimension = configuredHashDimension;
        binWidth = configuredBinWidth;
        minVal = configuredMinVal;
        maxVal = configuredMaxVal;
    }

    /**
     * Return whether rotation token generation is active.
     *
     * @return {@code true} if rotation tokens should be generated
     */
    public static boolean isEnabled() {
        return enabled;
    }

    /**
     * Return the configured initialization vector.
     *
     * @return rotation IV, or {@code null} if not configured
     */
    public static String getRotationIv() {
        return rotationIv;
    }

    /**
     * Return the configured number of rotation matrices.
     *
     * @return rotation count
     */
    public static int getRotationCount() {
        return rotationCount;
    }

    /**
     * Return the configured number of projected dimensions.
     *
     * @return hash dimension
     */
    public static int getHashDimension() {
        return hashDimension;
    }

    /**
     * Return the configured quantizer bin width.
     *
     * @return bin width
     */
    public static double getBinWidth() {
        return binWidth;
    }

    /**
     * Return the configured quantizer lower bound.
     *
     * @return min value
     */
    public static double getMinVal() {
        return minVal;
    }

    /**
     * Return the configured quantizer upper bound.
     *
     * @return max value
     */
    public static double getMaxVal() {
        return maxVal;
    }
}
