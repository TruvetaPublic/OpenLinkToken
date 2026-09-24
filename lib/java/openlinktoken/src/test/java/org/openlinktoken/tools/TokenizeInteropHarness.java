/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tools;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import org.openlinktoken.tokens.TokenDefinition;
import org.openlinktoken.tokens.TokenGenerator;
import org.openlinktoken.tokens.TokenGeneratorResult;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

/**
 * Thin interoperability harness that emits tokenize-compatible CSV output using
 * the Java core library directly.
 */
public final class TokenizeInteropHarness {
    private static final String BIRTH_DATE_COLUMN = "BirthDate";
    private static final String FIRST_NAME_COLUMN = "FirstName";
    private static final String LAST_NAME_COLUMN = "LastName";
    private static final String POSTAL_CODE_COLUMN = "PostalCode";
    private static final String RECORD_ID_COLUMN = "RecordId";
    private static final String RULE_ID_COLUMN = "RuleId";
    private static final String SEX_COLUMN = "Sex";
    private static final String SOCIAL_SECURITY_NUMBER_COLUMN = "SocialSecurityNumber";
    private static final String TOKEN_COLUMN = "Token";

    /** Prevents instantiation of this command-line utility. */
    private TokenizeInteropHarness() {
    }

    /**
     * Generates tokenize-compatible CSV output using Java library APIs.
     *
     * @param args input CSV path, output CSV path, and hashing secret.
     * @throws IllegalArgumentException if the arguments are missing or the input CSV has no header
     * @throws Exception if the harness cannot initialize tokenization or read or write the CSV files
     */
    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            throw new IllegalArgumentException(
                    "Expected arguments: <input.csv> <output.csv> <hashing-secret>");
        }

        var inputPath = Path.of(args[0]);
        var outputPath = Path.of(args[1]);
        var hashingSecret = args[2];

        if (outputPath.getParent() != null) {
            Files.createDirectories(outputPath.getParent());
        }

        var tokenGenerator = createTokenGenerator(hashingSecret);

        try (BufferedReader reader = Files.newBufferedReader(inputPath, StandardCharsets.UTF_8);
                BufferedWriter writer = Files.newBufferedWriter(outputPath, StandardCharsets.UTF_8)) {
            var headerLine = reader.readLine();
            if (headerLine == null) {
                throw new IllegalArgumentException("Input CSV is empty: " + inputPath);
            }

            var headers = parseCsvLine(headerLine).toArray(String[]::new);
            var headerIndexes = buildHeaderIndexes(headers);

            writer.write(String.join(",", RULE_ID_COLUMN, TOKEN_COLUMN, RECORD_ID_COLUMN));
            writer.newLine();

            String line;
            while ((line = reader.readLine()) != null) {
                var values = parseCsvLine(line).toArray(String[]::new);
                var personAttributes = buildPersonAttributes(headerIndexes, values);
                var recordId = getValue(headerIndexes, values, RECORD_ID_COLUMN);
                TokenGeneratorResult result = tokenGenerator.getAllTokens(personAttributes);

                for (String tokenId : new TreeSet<>(result.getTokens().keySet())) {
                    writer.write(tokenId);
                    writer.write(",");
                    writer.write(result.getTokens().get(tokenId));
                    writer.write(",");
                    writer.write(recordId);
                    writer.newLine();
                }
            }
        }
    }

    /**
     * Creates the token generator used by the interoperability run.
     *
     * @param hashingSecret secret used by the hash transformer
     * @return a generator with the built-in token definitions and SHA-256 tokenizer
     * @throws Exception if the hashing transformer cannot be initialized
     */
    private static TokenGenerator createTokenGenerator(String hashingSecret) throws Exception {
        List<TokenTransformer> tokenTransformers = new ArrayList<>();
        tokenTransformers.add(new HashTokenTransformer(hashingSecret));
        return new TokenGenerator(new TokenDefinition(), new SHA256Tokenizer(tokenTransformers));
    }

    /**
     * Maps each CSV header name to its column index.
     *
     * @param headers parsed column names from the CSV header row
     * @return a map from header names to their indexes
     */
    private static Map<String, Integer> buildHeaderIndexes(String[] headers) {
        var indexes = new HashMap<String, Integer>();
        for (int index = 0; index < headers.length; index++) {
            indexes.put(headers[index], index);
        }
        return indexes;
    }

    /**
     * Builds the class-keyed person fields present in one CSV row.
     *
     * @param headerIndexes mapping from CSV column names to indexes
     * @param values parsed values for the current row
     * @return supported person attributes whose columns are present in the header
     */
    private static Map<Class<? extends Attribute>, String> buildPersonAttributes(
            Map<String, Integer> headerIndexes,
            String[] values) {
        var personAttributes = new HashMap<Class<? extends Attribute>, String>();
        addAttribute(personAttributes, headerIndexes, values, BIRTH_DATE_COLUMN, BirthDateAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, FIRST_NAME_COLUMN, FirstNameAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, LAST_NAME_COLUMN, LastNameAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, POSTAL_CODE_COLUMN, PostalCodeAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, SEX_COLUMN, SexAttribute.class);
        addAttribute(personAttributes, headerIndexes, values, SOCIAL_SECURITY_NUMBER_COLUMN,
                SocialSecurityNumberAttribute.class);
        return personAttributes;
    }

    /**
     * Adds a row value for a supported attribute when its CSV column exists.
     *
     * @param personAttributes destination map of class-keyed person fields
     * @param headerIndexes mapping from CSV column names to indexes
     * @param values parsed values for the current row
     * @param columnName CSV header to read
     * @param attributeClass attribute type used as the destination key
     */
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

    /**
     * Reads a value by its header name, returning an empty string when the column or row value is absent.
     *
     * @param headerIndexes mapping from CSV column names to indexes
     * @param values parsed values for the current row
     * @param columnName CSV header to read
     * @return the row value, or an empty string when no value is available
     */
    private static String getValue(Map<String, Integer> headerIndexes, String[] values, String columnName) {
        Integer index = headerIndexes.get(columnName);
        if (index == null || index >= values.length) {
            return "";
        }
        return values[index];
    }

    /**
     * Splits one CSV row while preserving commas inside quoted fields and unescaping doubled quotes.
     *
     * @param line CSV row to parse
     * @return the parsed field values in their original order
     */
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
