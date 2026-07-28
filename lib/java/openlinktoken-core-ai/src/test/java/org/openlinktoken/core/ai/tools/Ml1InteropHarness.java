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
import org.openlinktoken.core.ai.tokens.ML1OnnxSignatureProvider;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Emits RecordId-to-ML1 JSON for interoperability checks.
 */
public final class Ml1InteropHarness {

    private Ml1InteropHarness() {
    }

    /**
     * @param args input CSV path and output JSON path
     * @throws Exception if the harness cannot read input or write output
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("Expected arguments: <input.csv> <output.json>");
        }

        Path inputPath = Path.of(args[0]);
        Path outputPath = Path.of(args[1]);
        if (outputPath.getParent() != null) {
            Files.createDirectories(outputPath.getParent());
        }

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
                recordIds.add(getValue(headerIndexes, values, "RecordId"));
                rows.add(buildPersonAttributes(headerIndexes, values));
            }
        }

        ML1OnnxSignatureProvider provider = new ML1OnnxSignatureProvider();
        InferenceBatchResult result = provider.generateBatch(rows);
        Map<String, String> byRecordId = new LinkedHashMap<>();
        for (int index = 0; index < recordIds.size(); index++) {
            byRecordId.put(recordIds.get(index), result.signatures().get(index));
        }

        new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(outputPath.toFile(), byRecordId);
    }

    private static Map<String, Integer> buildHeaderIndexes(String[] headers) {
        Map<String, Integer> indexes = new LinkedHashMap<>();
        for (int index = 0; index < headers.length; index++) {
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
        if (headerIndexes.containsKey(columnName)) {
            personAttributes.put(attributeClass, getValue(headerIndexes, values, columnName));
        }
    }

    private static String getValue(Map<String, Integer> headerIndexes, String[] values, String columnName) {
        Integer index = headerIndexes.get(columnName);
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
                if (inQuotes && index + 1 < line.length() && line.charAt(index + 1) == '"') {
                    currentValue.append('"');
                    index++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (currentCharacter == ',' && !inQuotes) {
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
