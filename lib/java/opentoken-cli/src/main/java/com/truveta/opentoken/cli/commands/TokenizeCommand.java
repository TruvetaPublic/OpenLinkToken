/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.Metadata;
import com.truveta.opentoken.cli.io.MetadataWriter;
import com.truveta.opentoken.cli.io.PersonAttributesReader;
import com.truveta.opentoken.cli.io.PersonAttributesWriter;
import com.truveta.opentoken.cli.io.RecordIdMappingWriter;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVReader;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVWriter;
import com.truveta.opentoken.cli.io.json.MetadataJsonWriter;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetReader;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetWriter;
import com.truveta.opentoken.cli.processor.PersonAttributesProcessor;
import com.truveta.opentoken.cli.util.StringMaskingUtil;
import com.truveta.opentoken.tokentransformer.HashTokenTransformer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;
import com.truveta.opentoken.tokens.tokenizer.PassthroughTokenizer;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Tokenize command - generates tokens from person attributes.
 *
 * <p>Normal mode (default): applies SHA-256 then HMAC-SHA256 hashing on the token
 * signature, producing opaque base64 tokens. {@code --hashingsecret} is required.
 *
 * <p>Demo mode ({@code --demo-mode}): skips all hashing so tokens are the raw
 * pipe-separated attribute signature strings. No secret is needed, making it easy
 * to explore the output without managing secrets. Demo-mode output is
 * <strong>not</strong> suitable for production or cross-organisation exchange.
 */
@Command(name = "tokenize", description = {
        "Generate tokens from person attributes.",
        "",
        "Normal mode: tokens are HMAC-SHA256 hashed (--hashingsecret required).",
        "Demo mode (--demo-mode): tokens are plain attribute signature strings; no secret needed."
})
public class TokenizeCommand implements Callable<Integer> {

    private static final Logger logger = LoggerFactory.getLogger(TokenizeCommand.class);
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

    @Option(names = {
            "--demo-mode" }, description = "Enable demo mode: output raw pipe-separated attribute signature strings with no hashing."
                    + " --hashingsecret is not required in this mode."
                    + " Demo output is NOT suitable for production or cross-organisation exchange.")
    private boolean demoMode;

    @Option(names = { "-h",
            "--hashingsecret" }, description = "Hashing secret for HMAC-SHA256 token generation (required in normal mode)")
    private String hashingSecret;

    @Option(names = { "--help" }, usageHelp = true, description = "Show this help message and exit")
    private boolean helpRequested;

    @Option(names = { "-V", "--version" }, versionHelp = true, description = "Print version information and exit")
    private boolean versionRequested;

    @Option(names = {
            "--hash-record-ids" }, description = "Hash input RecordId values using SHA-256 before writing to output."
                    + " A mapping file (<output>.record-id-mapping.csv) is also written"
                    + " so that hashed IDs can be reconciled back to the originals.")
    private boolean hashRecordIds;

    @Override
    public Integer call() {
        if (demoMode) {
            logger.warn("Running in DEMO MODE - tokens are raw attribute signature strings with no hashing."
                    + " Do not use demo-mode output in production or share it externally.");
        } else {
            logger.info("Running tokenize command (normal mode)");
        }

        // Default output type to input type if not specified
        if (outputType == null || outputType.isEmpty()) {
            outputType = inputType;
        }

        // Log parameters (mask secret only when present)
        logger.info("Input: {} ({})", inputPath, inputType);
        logger.info("Output: {} ({})", outputPath, outputType);
        if (!demoMode && logger.isInfoEnabled()) {
            logger.info("Hashing Secret: {}", maskString(hashingSecret));
        }
        if (hashRecordIds) {
            logger.info("Record ID hashing enabled");
        }

        // Validate file types
        if (!isValidType(inputType)) {
            logger.error("Invalid input type: {}. Must be 'csv' or 'parquet'", inputType);
            return 1;
        }
        if (!isValidType(outputType)) {
            logger.error("Invalid output type: {}. Must be 'csv' or 'parquet'", outputType);
            return 1;
        }

        // --hashingsecret is required in normal mode only
        if (!demoMode && (hashingSecret == null || hashingSecret.isBlank())) {
            logger.error("--hashingsecret is required in normal mode. Use --demo-mode to skip hashing.");
            return 1;
        }

        try {
            processTokens();
            logger.info("Token generation completed successfully");
            return 0;
        } catch (Exception e) {
            logger.error("Error during token generation", e);
            return 1;
        }
    }

    private void processTokens() throws IOException {
        Metadata metadata = new Metadata();
        Map<String, Object> metadataMap = metadata.initialize();

        String mappingFilePath = hashRecordIds
                ? RecordIdMappingWriter.buildMappingFilePath(outputPath)
                : null;

        try (PersonAttributesReader reader = createReader(inputPath, inputType);
                PersonAttributesWriter writer = createWriter(outputPath, outputType);
                RecordIdMappingWriter mappingWriter = hashRecordIds
                        ? new RecordIdMappingWriter(mappingFilePath)
                        : null) {

            if (demoMode) {
                // Skip SHA-256 and HMAC: use PassthroughTokenizer so tokens are the
                // raw pipe-separated attribute signature strings.
                PersonAttributesProcessor.process(reader, writer,
                        new PassthroughTokenizer(List.of()), metadataMap);
            } else {
                // Only record the hashing-secret hash in normal mode
                metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, hashingSecret);
                PersonAttributesProcessor.process(reader, writer, buildHashTransformers(), metadataMap,
                        mappingWriter);
            }
            MetadataWriter metadataWriter = new MetadataJsonWriter(outputPath);
            metadataWriter.write(metadataMap);
        } catch (Exception e) {
            throw new IOException("Failed to process tokens", e);
        }

        if (hashRecordIds) {
            logger.info("Record ID mapping file written to: {}", mappingFilePath);
        }
    }

    private List<TokenTransformer> buildHashTransformers() throws IOException {
        List<TokenTransformer> transformers = new ArrayList<>();
        try {
            transformers.add(new HashTokenTransformer(hashingSecret));
        } catch (Exception e) {
            throw new IOException("Failed to initialize hash transformer", e);
        }
        return transformers;
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
