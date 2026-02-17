/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.cli.io.TokenReader;
import com.truveta.opentoken.cli.io.TokenWriter;
import com.truveta.opentoken.cli.io.csv.TokenCSVReader;
import com.truveta.opentoken.cli.io.csv.TokenCSVWriter;
import com.truveta.opentoken.cli.io.parquet.TokenParquetReader;
import com.truveta.opentoken.cli.io.parquet.TokenParquetWriter;
import com.truveta.opentoken.cli.processor.TokenConstants;
import com.truveta.opentoken.cli.util.StringMaskingUtil;
import com.truveta.opentoken.tokens.Token;
import com.truveta.opentoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.JweMatchTokenFormatter;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Encrypt command - encrypts hashed tokens.
 */
@Command(name = "encrypt", description = "Encrypt hashed tokens using encryption key")
public class EncryptCommand implements Callable<Integer> {

    private static final Logger logger = LoggerFactory.getLogger(EncryptCommand.class);
    private static final String TYPE_CSV = "csv";
    private static final String TYPE_PARQUET = "parquet";

    @Option(names = { "-i", "--input" }, required = true, description = "Input file path with hashed tokens")
    private String inputPath;

    @Option(names = { "-o", "--output" }, required = true, description = "Output file path for encrypted tokens")
    private String outputPath;

    @Option(names = { "-t", "--input-type" }, required = true, description = "Input file type: csv or parquet")
    private String inputType;

    @Option(names = { "-ot",
            "--output-type" }, description = "Output file type (defaults to input type): csv or parquet")
    private String outputType;

    @Option(names = { "-e", "--encryptionkey" }, required = true, description = "Encryption key for token encryption")
    private String encryptionKey;

    @Option(names = {
            "--ring-id" }, description = "Ring identifier for key management. Defaults to a random UUID if not provided")
    private String ringId;

    @Option(names = { "--help" }, usageHelp = true, description = "Show this help message and exit")
    private boolean helpRequested;

    @Option(names = { "-V", "--version" }, versionHelp = true, description = "Print version information and exit")
    private boolean versionRequested;

    @Override
    public Integer call() {
        logger.info("Running encrypt command");

        // Default output type to input type if not specified
        if (outputType == null || outputType.isEmpty()) {
            outputType = inputType;
        }

        if (ringId == null || ringId.isBlank()) {
            ringId = UUID.randomUUID().toString();
        }

        // Log parameters (mask key)
        logger.info("Input: {} ({})", inputPath, inputType);
        logger.info("Output: {} ({})", outputPath, outputType);
        logger.info("Encryption Key: {}", maskString(encryptionKey));
        logger.info("Ring ID: {}", ringId);

        // Validate types
        if (!isValidType(inputType)) {
            logger.error("Invalid input type: {}. Must be 'csv' or 'parquet'", inputType);
            return 1;
        }
        if (!isValidType(outputType)) {
            logger.error("Invalid output type: {}. Must be 'csv' or 'parquet'", outputType);
            return 1;
        }

        // Validate key
        if (encryptionKey == null || encryptionKey.isBlank()) {
            logger.error("Encryption key is required");
            return 1;
        }

        try {
            encryptTokens();
            logger.info("Token encryption completed successfully");
            return 0;
        } catch (Exception e) {
            logger.error("Error during token encryption", e);
            return 1;
        }
    }

    private void encryptTokens() throws IOException {
        try {
            EncryptTokenTransformer encryptor = new EncryptTokenTransformer(encryptionKey);
            Map<String, JweMatchTokenFormatter> jweFormatterCache = new HashMap<>();
            long rowCounter = 0;
            long encryptedCounter = 0;
            long errorCounter = 0;

            try (TokenReader reader = createTokenReader(inputPath, inputType);
                    TokenWriter writer = createTokenWriter(outputPath, outputType)) {
                while (reader.hasNext()) {
                    Map<String, String> row = reader.next();
                    rowCounter++;

                    String token = row.get(TokenConstants.TOKEN);
                    if (token != null && !token.isEmpty() && !Token.BLANK.equals(token)) {
                        try {
                            String encryptedToken = encryptor.transform(token);
                            String wrappedToken = wrapAsV1TokenIfConfigured(encryptedToken, row, jweFormatterCache);
                            row.put(TokenConstants.TOKEN, wrappedToken);
                            encryptedCounter++;
                        } catch (Exception e) {
                            logger.error("Failed to encrypt token for RecordId {}, RuleId {}: {}",
                                    row.get(TokenConstants.RECORD_ID), row.get(TokenConstants.RULE_ID),
                                    e.getMessage());
                            errorCounter++;
                        }
                    }

                    writer.writeToken(row);

                    if (rowCounter % 10000 == 0) {
                        logger.info(String.format("Processed \"%,d\" tokens", rowCounter));
                    }
                }
            }

            logger.info(String.format("Processed a total of %,d tokens", rowCounter));
            logger.info(String.format("Successfully encrypted %,d tokens", encryptedCounter));
            if (errorCounter > 0) {
                logger.warn(String.format("Failed to encrypt %,d tokens", errorCounter));
            }
        } catch (Exception e) {
            logger.error("Error during token encryption", e);
            throw new RuntimeException("Failed to encrypt tokens", e);
        }
    }

    private String wrapAsV1TokenIfConfigured(String encryptedToken,
            Map<String, String> row,
            Map<String, JweMatchTokenFormatter> jweFormatterCache) throws Exception {
        if (ringId == null || ringId.isBlank()) {
            return encryptedToken;
        }

        String ruleId = row.get(TokenConstants.RULE_ID);
        if (ruleId == null || ruleId.isBlank()) {
            return encryptedToken;
        }

        JweMatchTokenFormatter formatter = jweFormatterCache.get(ruleId);
        if (formatter == null) {
            formatter = new JweMatchTokenFormatter(encryptionKey, ringId, ruleId, "truveta.opentoken");
            jweFormatterCache.put(ruleId, formatter);
        }

        return formatter.transform(encryptedToken);
    }

    private TokenReader createTokenReader(String path, String type) throws IOException {
        return switch (type.toLowerCase()) {
            case TYPE_CSV -> new TokenCSVReader(path);
            case TYPE_PARQUET -> new TokenParquetReader(path);
            default -> throw new IllegalArgumentException("Unsupported input type: " + type);
        };
    }

    private TokenWriter createTokenWriter(String path, String type) throws IOException {
        return switch (type.toLowerCase()) {
            case TYPE_CSV -> new TokenCSVWriter(path);
            case TYPE_PARQUET -> new TokenParquetWriter(path);
            default -> throw new IllegalArgumentException("Unsupported output type: " + type);
        };
    }

    private boolean isValidType(String type) {
        return TYPE_CSV.equalsIgnoreCase(type) || TYPE_PARQUET.equalsIgnoreCase(type);
    }

    private String maskString(String input) {
        return StringMaskingUtil.maskString(input);
    }
}
