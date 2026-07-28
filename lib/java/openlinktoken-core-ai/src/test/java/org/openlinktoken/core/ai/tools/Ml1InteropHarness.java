/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tools;

import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.tokens.InferenceBatchResult;
import org.openlinktoken.core.ai.tokens.ML1InferenceConfig;
import org.openlinktoken.core.ai.tokens.ML1OnnxSignatureProvider;
import org.openlinktoken.core.ai.tokens.RotationConfig;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Test-only command-line adapter for comparing Java and Python ML1 signatures.
 *
 * <p>The harness reads a person CSV containing a {@code RecordId} column and
 * the ML1 input fields ({@code BirthDate}, {@code FirstName}, {@code LastName},
 * {@code PostalCode}, and {@code Sex}). It converts each row into the
 * attribute map expected by {@link ML1OnnxSignatureProvider}, runs the Java
 * provider in batch mode, and writes a JSON object mapping each record ID to
 * its generated ML1 signature.
 *
 * <p>The JSON is consumed by the Python interoperability test, which processes
 * the same temporary CSV with the Python ML1 provider and compares the two
 * mappings exactly. This verifies the complete cross-language pipeline,
 * including attribute handling, ONNX inference, rotation quantization, and
 * blocking-key hashing. The class is kept under test sources because it is a
 * test boundary adapter, not part of the published Java API.
 */
public final class Ml1InteropHarness {

    private Ml1InteropHarness() {
    }

    /**
     * Runs the Java ML1 provider for every CSV row and writes the comparison
     * artifact consumed by the Python interoperability test.
     *
     * <p>Usage: {@code <input.csv> <output.json>}. The output preserves input
     * order and uses {@code null} for rows that fail ML1 validation.
     *
     * @param args input CSV path and output JSON path
     * @throws Exception if the harness cannot read input or write output
     */
    public static void main(String[] args) throws Exception {
        // Keep this harness deliberately small: the Python interoperability test
        // supplies the input and consumes the JSON, so there is no CLI framework
        // or configuration file to keep in sync.
        if (args.length != 2) {
            throw new IllegalArgumentException("Expected arguments: <input.csv> <output.json>");
        }

        Path inputPath = Path.of(args[0]);
        Path outputPath = Path.of(args[1]);
        // The test normally uses a temporary output path. Create its parent so
        // callers do not need a separate setup step before invoking Maven.
        if (outputPath.getParent() != null) {
            Files.createDirectories(outputPath.getParent());
        }

        // Keep record IDs and attribute rows in parallel lists. The provider
        // returns signatures in the same order as its input rows, allowing
        // invalid rows to remain represented by a null signature at their
        // original record ID.
        List<String> recordIds = new ArrayList<>();
        List<Map<Class<? extends Attribute>, String>> rows = new ArrayList<>();

        try (BufferedReader reader = Files.newBufferedReader(inputPath, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                throw new IllegalArgumentException("Input CSV is empty: " + inputPath);
            }

            String[] headers = parseCsvLine(headerLine).toArray(String[]::new);
            Map<String, Integer> headerIndexes = buildHeaderIndexes(headers);

            String line;
            while ((line = reader.readLine()) != null) {
                String[] values = parseCsvLine(line).toArray(String[]::new);
                // Read the ID separately because it is not an ML1 model input;
                // it is only the stable key used to compare Java and Python
                // results after both providers finish.
                recordIds.add(getValue(headerIndexes, values, "RecordId"));
                rows.add(buildPersonAttributes(headerIndexes, values));
            }
        }

        // Configure the same bundled assets and rotation defaults used by the
        // Python parity side. Explicit configuration prevents a future runtime
        // default change from silently changing this cross-language contract.
        ML1InferenceConfig.configure(
                true,
                ML1InferenceConfig.DEFAULT_MODEL_PATH,
                ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
                ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH);
        RotationConfig.configure(true, RotationConfig.DEFAULT_IV);

        ML1OnnxSignatureProvider provider = new ML1OnnxSignatureProvider();
        InferenceBatchResult result = provider.generateBatch(rows);
        Map<String, String> byRecordId = new LinkedHashMap<>();
        for (int index = 0; index < recordIds.size(); index++) {
            // LinkedHashMap preserves input order, which makes generated JSON
            // stable and easier to inspect when a parity assertion fails.
            byRecordId.put(recordIds.get(index), result.signatures().get(index));
        }

        // Pretty JSON is intentional: this file is a diagnostic interchange
        // artifact, not a compact production payload.
        new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(outputPath.toFile(), byRecordId);
    }

    private static Map<String, Integer> buildHeaderIndexes(String[] headers) {
        Map<String, Integer> indexes = new LinkedHashMap<>();
        for (int index = 0; index < headers.length; index++) {
            // Store column positions once so every row can be mapped without
            // repeatedly scanning the header array.
            indexes.put(headers[index], index);
        }
        return indexes;
    }

    private static Map<Class<? extends Attribute>, String> buildPersonAttributes(
            Map<String, Integer> headerIndexes,
            String[] values) {
        Map<Class<? extends Attribute>, String> personAttributes = new LinkedHashMap<>();
        addAttribute(personAttributes, headerIndexes, values, "BirthDate", BirthDateAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, "FirstName", FirstNameAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, "LastName", LastNameAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, "PostalCode", PostalCodeAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, "Sex", SexAttribute.class);
        return personAttributes;
    }

    private static void addAttribute(
            Map<Class<? extends Attribute>, String> personAttributes,
            Map<String, Integer> headerIndexes,
            String[] values,
            String columnName,
            Class<? extends Attribute> attributeClass) {
        // ML1 accepts a subset of person fields. Optional extra columns in the
        // CSV are ignored, while missing ML1 columns are left out so the
        // provider can return its normal invalid-input result.
        if (headerIndexes.containsKey(columnName)) {
            personAttributes.put(attributeClass, getValue(headerIndexes, values, columnName));
        }
    }

    private static String getValue(Map<String, Integer> headerIndexes, String[] values, String columnName) {
        Integer index = headerIndexes.get(columnName);
        // Treat a missing column or short row as an empty value. The provider
        // then applies the same validation path as any other missing field.
        if (index == null || index >= values.length) {
            return "";
        }
        return values[index];
    }

    private static List<String> parseCsvLine(String line) {
        List<String> values = new ArrayList<>();
        StringBuilder currentValue = new StringBuilder();
        boolean inQuotes = false;

        for (int index = 0; index < line.length(); index++) {
            char currentCharacter = line.charAt(index);
            if (currentCharacter == '"') {
                // CSV escapes a quote inside a quoted field as two quotes.
                if (inQuotes && index + 1 < line.length() && line.charAt(index + 1) == '"') {
                    currentValue.append('"');
                    index++;
                } else {
                    // Quotes only change parsing state; they are not part of
                    // the attribute value passed to the provider.
                    inQuotes = !inQuotes;
                }
            } else if (currentCharacter == ',' && !inQuotes) {
                // A comma inside quotes belongs to the current field; an
                // unquoted comma terminates it.
                values.add(currentValue.toString());
                currentValue.setLength(0);
            } else {
                currentValue.append(currentCharacter);
            }
        }

        values.add(currentValue.toString());
        return values;
    }
}
