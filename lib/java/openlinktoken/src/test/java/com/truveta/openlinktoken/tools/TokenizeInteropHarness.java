/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tools;

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

import com.truveta.openlinktoken.attributes.Attribute;
import com.truveta.openlinktoken.attributes.person.BirthDateAttribute;
import com.truveta.openlinktoken.attributes.person.FirstNameAttribute;
import com.truveta.openlinktoken.attributes.person.LastNameAttribute;
import com.truveta.openlinktoken.attributes.person.PostalCodeAttribute;
import com.truveta.openlinktoken.attributes.person.SexAttribute;
import com.truveta.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import com.truveta.openlinktoken.tokens.TokenDefinition;
import com.truveta.openlinktoken.tokens.TokenGenerator;
import com.truveta.openlinktoken.tokens.TokenGeneratorResult;
import com.truveta.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import com.truveta.openlinktoken.tokentransformer.HashTokenTransformer;
import com.truveta.openlinktoken.tokentransformer.TokenTransformer;

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

    private TokenizeInteropHarness() {
    }

    /**
     * Generates tokenize-compatible CSV output using Java library APIs.
     *
     * @param args input CSV path, output CSV path, and hashing secret.
     * @throws Exception if the harness cannot read input or write output.
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

    private static TokenGenerator createTokenGenerator(String hashingSecret) throws Exception {
        List<TokenTransformer> tokenTransformers = new ArrayList<>();
        tokenTransformers.add(new HashTokenTransformer(hashingSecret));
        return new TokenGenerator(new TokenDefinition(), new SHA256Tokenizer(tokenTransformers));
    }

    private static Map<String, Integer> buildHeaderIndexes(String[] headers) {
        var indexes = new HashMap<String, Integer>();
        for (int index = 0; index < headers.length; index++) {
            indexes.put(headers[index], index);
        }
        return indexes;
    }

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
