/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tools;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import com.truveta.opentoken.tokentransformer.rotation.RotationMatrixGenerator;

/**
 * Thin harness that generates rotation matrices from an IV and serializes them
 * to a JSON file for cross-language interoperability testing.
 *
 * <p>Usage: {@code <iv> <rotation_count> <dimension> <output.json>}
 *
 * <p>Output format:
 * <pre>
 * {
 *   "iv": "...",
 *   "rotation_count": N,
 *   "dimension": D,
 *   "matrices": [
 *     [[row0col0, row0col1, ...], [row1col0, ...], ...],
 *     ...
 *   ]
 * }
 * </pre>
 */
public final class RotationMatrixInteropHarness {

    private RotationMatrixInteropHarness() {
    }

    /**
     * Entry point for the interop harness.
     *
     * @param args iv, rotation_count, dimension, output_path
     * @throws Exception if arguments are invalid or output cannot be written.
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException(
                    "Expected arguments: <iv> <rotation_count> <dimension> <output.json>");
        }

        String iv = args[0];
        int rotationCount = Integer.parseInt(args[1]);
        int dimension = Integer.parseInt(args[2]);
        Path outputPath = Path.of(args[3]);

        if (outputPath.getParent() != null) {
            Files.createDirectories(outputPath.getParent());
        }

        List<double[][]> matrices = RotationMatrixGenerator.generate(iv, rotationCount, dimension);

        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"iv\": \"").append(jsonEscape(iv)).append("\",\n");
        sb.append("  \"rotation_count\": ").append(rotationCount).append(",\n");
        sb.append("  \"dimension\": ").append(dimension).append(",\n");
        sb.append("  \"matrices\": [\n");

        for (int r = 0; r < matrices.size(); r++) {
            sb.append("    [\n");
            double[][] m = matrices.get(r);
            for (int row = 0; row < dimension; row++) {
                sb.append("      [");
                for (int col = 0; col < dimension; col++) {
                    sb.append(doubleToJson(m[row][col]));
                    if (col < dimension - 1) {
                        sb.append(", ");
                    }
                }
                sb.append("]");
                if (row < dimension - 1) {
                    sb.append(",");
                }
                sb.append("\n");
            }
            sb.append("    ]");
            if (r < matrices.size() - 1) {
                sb.append(",");
            }
            sb.append("\n");
        }

        sb.append("  ]\n");
        sb.append("}\n");

        Files.writeString(outputPath, sb.toString(), StandardCharsets.UTF_8);
    }

    /**
     * Serialize a double to its full-precision JSON representation.
     * Uses {@link Double#toString} which preserves all significant digits
     * for exact round-trip comparison.
     */
    private static String doubleToJson(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) {
            throw new IllegalArgumentException("Non-finite double cannot be serialized to JSON: " + value);
        }
        return Double.toString(value);
    }

    private static String jsonEscape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
