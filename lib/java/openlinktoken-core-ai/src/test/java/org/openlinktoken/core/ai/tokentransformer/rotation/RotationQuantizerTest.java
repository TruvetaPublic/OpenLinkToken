/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokentransformer.rotation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Tests quantization boundaries, clamping, and Python-compatible binning.
 */
class RotationQuantizerTest {

    private static final double DEFAULT_MIN = -5.0;
    private static final double DEFAULT_MAX = 5.0;
    private static final double DEFAULT_BIN_WIDTH = 0.05;
    // numBins = ceil(10.0 / 0.05) = 200
    private static final int NUM_BINS = 200;

    /**
     * Verifies that zero maps to the midpoint bin under the default quantization.
     */
    @Test
    void testZeroMapsToMidpointBin() {
        // 0.0 is the midpoint of [-5, 5].
        // Python float floor division gives (0.0 - (-5.0)) // 0.05 = 99.0.
        String result = RotationQuantizer.quantize(new float[] { 0.0f });
        assertEquals("99", result);
    }

    /**
     * Verifies that values below the default range are clamped to its first bin.
     */
    @Test
    void testClampingBelowMin() {
        // Values below min should clamp to bin 0
        String result = RotationQuantizer.quantize(new float[] { -10.0f });
        assertEquals("0", result);
    }

    /**
     * Verifies that values above the default range are clamped to its last bin.
     */
    @Test
    void testClampingAboveMax() {
        // Values above max clamp to max; Python's 10.0 // 0.05 is 199.0.
        String result = RotationQuantizer.quantize(new float[] { 10.0f });
        assertEquals(String.valueOf(NUM_BINS - 1), result);
    }

    /**
     * Verifies that the inclusive upper bound maps to the final bin.
     */
    @Test
    void testClampingAtExactMax() {
        // Python float floor division gives (5.0 - (-5.0)) // 0.05 = 199.0.
        String result = RotationQuantizer.quantize(new float[] { 5.0f });
        assertEquals(String.valueOf(NUM_BINS - 1), result);
    }

    /**
     * Verifies that default quantization returns one integer per vector element.
     */
    @Test
    void testOutputIsSpaceSeparatedIntegers() {
        float[] x = { -1.0f, 0.0f, 1.0f };
        String result = RotationQuantizer.quantize(x);
        String[] parts = result.split(" ");
        assertEquals(3, parts.length);
        for (String part : parts) {
            // Should parse as integer without exception
            int bin = Integer.parseInt(part);
            assertTrue(bin >= 0 && bin < NUM_BINS,
                    "Bin " + bin + " should be in range [0, " + (NUM_BINS - 1) + "]");
        }
    }

    /**
     * Verifies that the default minimum maps to bin zero.
     */
    @Test
    void testKnownValueMinBoundary() {
        // -5.0 → bin 0
        String result = RotationQuantizer.quantize(new float[] { -5.0f });
        assertEquals("0", result);
    }

    /**
     * Verifies the bin assigned to a value near the default upper bound.
     */
    @Test
    void testKnownValueNearMax() {
        // 4.975 → floor((4.975 - (-5.0)) / 0.05) = floor(199.5) = 199 (last bin)
        String result = RotationQuantizer.quantize(new float[] { 4.975f });
        assertEquals(String.valueOf(NUM_BINS - 1), result);
    }

    /**
     * Verifies that a value near the default upper bound maps to the final bin.
     */
    @Test
    void testNumBinsIs200WithDefaults() {
        // Verify the total number of bins is correct with default parameters.
        // Values at (max - binWidth + epsilon) should land in last bin.
        // Values just below max (4.99) should map to bin 199.
        int expectedLastBin = NUM_BINS - 1;
        String result = RotationQuantizer.quantize(new float[] { 4.99f });
        assertEquals(String.valueOf(expectedLastBin), result);
    }

    /**
     * Verifies quantization with a caller-supplied range and bin width.
     */
    @Test
    void testCustomRange() {
        // Range [0, 1), binWidth 0.1 → numBins = 10
        // 0.35 → floor(0.35 / 0.1) = 3
        String result = RotationQuantizer.quantize(new float[] { 0.35f }, 0.0, 1.0, 0.1);
        assertEquals("3", result);
    }

    /**
     * Verifies clamping at both ends of a caller-supplied range.
     */
    @Test
    void testCustomRangeClamping() {
        // Python float floor division maps 1.0 // 0.1 to 9.
        String belowMin = RotationQuantizer.quantize(new float[] { -1.0f }, 0.0, 1.0, 0.1);
        assertEquals("0", belowMin);

        String aboveMax = RotationQuantizer.quantize(new float[] { 2.0f }, 0.0, 1.0, 0.1);
        assertEquals("9", aboveMax);
    }

    /**
     * Verifies that a vector's values are quantized in their original order.
     */
    @Test
    void testMultipleElements() {
        float[] x = { -5.0f, 0.0f, 4.975f };
        String result = RotationQuantizer.quantize(x);
        String[] parts = result.split(" ");
        assertEquals(3, parts.length);
        assertEquals("0", parts[0]);
        assertEquals("99", parts[1]);
        assertEquals(String.valueOf(NUM_BINS - 1), parts[2]);
    }

    /**
     * Verifies the output format for a one-element vector.
     */
    @Test
    void testSingleElementOutput() {
        String result = RotationQuantizer.quantize(new float[] { 2.5f });
        // Python float floor division gives (2.5 - (-5.0)) // 0.05 = 149.0.
        assertEquals("149", result);
    }

    /**
     * Verifies the expected default bins at several Python-compatible boundaries.
     */
    @Test
    void testPythonFloorDivisionBoundaryFixtures() {
        String result = RotationQuantizer.quantize(new float[] { -2.5f, 0.0f, 2.5f, 5.0f });
        assertEquals("49 99 149 199", result);
    }
}
