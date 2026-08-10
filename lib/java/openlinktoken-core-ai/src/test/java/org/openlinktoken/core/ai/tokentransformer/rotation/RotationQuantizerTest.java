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

    @Test
    void testZeroMapsToMidpointBin() {
        // 0.0 is the midpoint of [-5, 5].
        // Python float floor division gives (0.0 - (-5.0)) // 0.05 = 99.0.
        String result = RotationQuantizer.quantize(new float[] { 0.0f });
        assertEquals("99", result);
    }

    @Test
    void testClampingBelowMin() {
        // Values below min should clamp to bin 0
        String result = RotationQuantizer.quantize(new float[] { -10.0f });
        assertEquals("0", result);
    }

    @Test
    void testClampingAboveMax() {
        // Values above max clamp to max; Python's 10.0 // 0.05 is 199.0.
        String result = RotationQuantizer.quantize(new float[] { 10.0f });
        assertEquals(String.valueOf(NUM_BINS - 1), result);
    }

    @Test
    void testClampingAtExactMax() {
        // Python float floor division gives (5.0 - (-5.0)) // 0.05 = 199.0.
        String result = RotationQuantizer.quantize(new float[] { 5.0f });
        assertEquals(String.valueOf(NUM_BINS - 1), result);
    }

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

    @Test
    void testKnownValueMinBoundary() {
        // -5.0 → bin 0
        String result = RotationQuantizer.quantize(new float[] { -5.0f });
        assertEquals("0", result);
    }

    @Test
    void testKnownValueNearMax() {
        // 4.975 → floor((4.975 - (-5.0)) / 0.05) = floor(199.5) = 199 (last bin)
        String result = RotationQuantizer.quantize(new float[] { 4.975f });
        assertEquals(String.valueOf(NUM_BINS - 1), result);
    }

    @Test
    void testNumBinsIs200WithDefaults() {
        // Verify the total number of bins is correct with default parameters.
        // Values at (max - binWidth + epsilon) should land in last bin.
        // Values just below max (4.99) should map to bin 199.
        int expectedLastBin = NUM_BINS - 1;
        String result = RotationQuantizer.quantize(new float[] { 4.99f });
        assertEquals(String.valueOf(expectedLastBin), result);
    }

    @Test
    void testCustomRange() {
        // Range [0, 1), binWidth 0.1 → numBins = 10
        // 0.35 → floor(0.35 / 0.1) = 3
        String result = RotationQuantizer.quantize(new float[] { 0.35f }, 0.0, 1.0, 0.1);
        assertEquals("3", result);
    }

    @Test
    void testCustomRangeClamping() {
        // Python float floor division maps 1.0 // 0.1 to 9.
        String belowMin = RotationQuantizer.quantize(new float[] { -1.0f }, 0.0, 1.0, 0.1);
        assertEquals("0", belowMin);

        String aboveMax = RotationQuantizer.quantize(new float[] { 2.0f }, 0.0, 1.0, 0.1);
        assertEquals("9", aboveMax);
    }

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

    @Test
    void testSingleElementOutput() {
        String result = RotationQuantizer.quantize(new float[] { 2.5f });
        // Python float floor division gives (2.5 - (-5.0)) // 0.05 = 149.0.
        assertEquals("149", result);
    }

    @Test
    void testPythonFloorDivisionBoundaryFixtures() {
        String result = RotationQuantizer.quantize(new float[] { -2.5f, 0.0f, 2.5f, 5.0f });
        assertEquals("49 99 149 199", result);
    }
}
