/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.Metadata;
import com.truveta.opentoken.cli.io.MetadataWriter;
import com.truveta.opentoken.cli.io.PersonAttributesReader;
import com.truveta.opentoken.cli.io.PersonAttributesWriter;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVReader;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVWriter;
import com.truveta.opentoken.cli.io.json.MetadataJsonWriter;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetReader;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetWriter;
import com.truveta.opentoken.cli.processor.PersonAttributesProcessor;
import com.truveta.opentoken.cli.util.StringMaskingUtil;
import com.truveta.opentoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.HashTokenTransformer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Package command - combines tokenize and encrypt in one command.
 * This is the default workflow: hash + encrypt.
 */
@Command(name = "package", description = "Generate and encrypt tokens in one step (tokenize + encrypt)")
public class PackageCommand implements Callable<Integer> {

    private static final Logger logger = LoggerFactory.getLogger(PackageCommand.class);
    private static final String TYPE_CSV = "csv";
    private static final String TYPE_PARQUET = "parquet";

    @Option(names = { "-i", "--input" }, required = true, description = "Input file path")
    private String inputPath;

    @Option(names = { "-o", "--output" }, required = true, description = "Output file path")
    private String outputPath;

    @Option(names = { "-t", "--input-type" }, required = true, description = "Input file type: csv or parquet")
    private String inputType;

    @Option(names = { "-ot",
            "--output-type" }, description = "Output file type (defaults to input type): csv or parquet")
    private String outputType;

    @Option(names = { "-h", "--hashingsecret" }, required = true, description = "Hashing secret for token generation")
    private String hashingSecret;

    @Option(names = { "-e", "--encryptionkey" }, required = true, description = "Encryption key for token encryption")
    private String encryptionKey;

    @Option(names = {
            "--ring-id" }, description = "Ring identifier for key management. Defaults to a random UUID if not provided")
    private String ringId;

    @Option(names = { "--help" }, usageHelp = true, description = "Show this help message and exit")
    private boolean helpRequested;

    @Option(names = { "-V", "--version" }, versionHelp = true, description = "Print version information and exit")
    private boolean versionRequested;

    @Option(names = {
            "--hash-record-ids" }, description = "Hash input RecordId values using SHA-256 before writing to output."
                    + " The hashed value (not the original) appears in the output file."
                    + " This is a one-way operation with no traceability.")
    private boolean hashRecordIds;

    @Override
    public Integer call() {
        logger.info("Running package command (tokenize + encrypt)");

        // Default output type to input type if not specified
        if (outputType == null || outputType.isEmpty()) {
            outputType = inputType;
        }

        if (ringId == null || ringId.isBlank()) {
            ringId = UUID.randomUUID().toString();
        }

        // Log parameters (mask secrets)
        logger.info("Input: {} ({})", inputPath, inputType);
        logger.info("Output: {} ({})", outputPath, outputType);
        logger.info("Hashing Secret: {}", maskString(hashingSecret));
        logger.info("Encryption Key: {}", maskString(encryptionKey));
        logger.info("Ring ID: {}", ringId);
        if (hashRecordIds) {
            logger.info("Record ID hashing enabled");
        }

        // Validate types
        if (!isValidType(inputType)) {
            logger.error("Invalid input type: {}. Must be 'csv' or 'parquet'", inputType);
            return 1;
        }
        if (!isValidType(outputType)) {
            logger.error("Invalid output type: {}. Must be 'csv' or 'parquet'", outputType);
            return 1;
        }

        // Validate secrets
        if (hashingSecret == null || hashingSecret.isBlank()) {
            logger.error("Hashing secret is required");
            return 1;
        }
        if (encryptionKey == null || encryptionKey.isBlank()) {
            logger.error("Encryption key is required");
            return 1;
        }

        try {
            processTokens();
            logger.info("Token generation and encryption completed successfully");
            return 0;
        } catch (Exception e) {
            logger.error("Error during token processing", e);
            return 1;
        }
    }

    private void processTokens() throws IOException {
        List<TokenTransformer> transformers = new ArrayList<>();

        try {
            // Add both hash and encryption transformers
            transformers.add(new HashTokenTransformer(hashingSecret));
            transformers.add(new EncryptTokenTransformer(encryptionKey));
        } catch (Exception e) {
            logger.error("Error initializing transformers", e);
            throw new RuntimeException("Failed to initialize transformers", e);
        }

        try (PersonAttributesReader reader = createReader(inputPath, inputType);
                PersonAttributesWriter writer = createWriter(outputPath, outputType)) {

            // Create metadata
            Metadata metadata = new Metadata();
            Map<String, Object> metadataMap = metadata.initialize();
            metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, hashingSecret);
            metadata.addHashedSecret(Metadata.ENCRYPTION_SECRET_HASH, encryptionKey);

            // Process data with JWE wrapping support for v1 token format
            PersonAttributesProcessor.process(reader, writer, transformers, metadataMap, encryptionKey, ringId,
                    hashRecordIds);

            // Write metadata
            MetadataWriter metadataWriter = new MetadataJsonWriter(outputPath);
            metadataWriter.write(metadataMap);
        } catch (Exception e) {
            logger.error("Error processing tokens", e);
            throw new IOException("Failed to process tokens", e);
        }
    }

    private PersonAttributesReader createReader(String path, String type) throws IOException {
        return switch (type.toLowerCase()) {
            case TYPE_CSV -> new PersonAttributesCSVReader(path);
            case TYPE_PARQUET -> new PersonAttributesParquetReader(path);
            default -> throw new IllegalArgumentException("Unsupported input type: " + type);
        };
    }

    private PersonAttributesWriter createWriter(String path, String type) throws IOException {
        return switch (type.toLowerCase()) {
            case TYPE_CSV -> new PersonAttributesCSVWriter(path);
            case TYPE_PARQUET -> new PersonAttributesParquetWriter(path);
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
