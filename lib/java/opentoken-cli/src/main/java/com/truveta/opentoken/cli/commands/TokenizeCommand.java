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
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVReader;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVWriter;
import com.truveta.opentoken.cli.io.json.MetadataJsonWriter;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetReader;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetWriter;
import com.truveta.opentoken.cli.processor.PersonAttributesProcessor;
import com.truveta.opentoken.cli.util.StringMaskingUtil;
import com.truveta.opentoken.tokentransformer.HashTokenTransformer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Tokenize command - generates hashed tokens from person attributes.
 * This is hash-only mode without encryption.
 */
@Command(
    name = "tokenize",
    description = "Generate hashed tokens from person attributes (hash-only mode)"
)
public class TokenizeCommand implements Callable<Integer> {
    
    private static final Logger logger = LoggerFactory.getLogger(TokenizeCommand.class);
    private static final String TYPE_CSV = "csv";
    private static final String TYPE_PARQUET = "parquet";
    
    @Option(names = {"-i", "--input"}, required = true, 
            description = "Input file path")
    private String inputPath;
    
    @Option(names = {"-o", "--output"}, required = true,
            description = "Output file path")
    private String outputPath;
    
    @Option(names = {"-t", "--input-type"}, required = true,
            description = "Input file type: csv or parquet")
    private String inputType;
    
    @Option(names = {"-ot", "--output-type"}, 
            description = "Output file type (defaults to input type): csv or parquet")
    private String outputType;
    
    @Option(names = {"-h", "--hashingsecret"}, required = true,
            description = "Hashing secret for token generation")
    private String hashingSecret;
    
    @Option(names = {"--help"}, usageHelp = true,
            description = "Show this help message and exit")
    private boolean helpRequested;
    
    @Option(names = {"-V", "--version"}, versionHelp = true,
            description = "Print version information and exit")
    private boolean versionRequested;
    
    @Override
    public Integer call() {
        logger.info("Running tokenize command (hash-only mode)");
        
        // Default output type to input type if not specified
        if (outputType == null || outputType.isEmpty()) {
            outputType = inputType;
        }
        
        // Log parameters (mask secret)
        logger.info("Input: {} ({})", inputPath, inputType);
        logger.info("Output: {} ({})", outputPath, outputType);
        logger.info("Hashing Secret: {}", maskString(hashingSecret));
        
        // Validate types
        if (!isValidType(inputType)) {
            logger.error("Invalid input type: {}. Must be 'csv' or 'parquet'", inputType);
            return 1;
        }
        if (!isValidType(outputType)) {
            logger.error("Invalid output type: {}. Must be 'csv' or 'parquet'", outputType);
            return 1;
        }
        
        // Validate secret
        if (hashingSecret == null || hashingSecret.isBlank()) {
            logger.error("Hashing secret is required");
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
        List<TokenTransformer> transformers = new ArrayList<>();
        
        try {
            // Add only hash transformer (no encryption in tokenize mode)
            transformers.add(new HashTokenTransformer(hashingSecret));
        } catch (Exception e) {
            logger.error("Error initializing hash transformer", e);
            throw new RuntimeException("Failed to initialize transformer", e);
        }
        
        try (PersonAttributesReader reader = createReader(inputPath, inputType);
             PersonAttributesWriter writer = createWriter(outputPath, outputType)) {
            
            // Create metadata
            Metadata metadata = new Metadata();
            Map<String, Object> metadataMap = metadata.initialize();
            metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, hashingSecret);
            
            // Process data
            PersonAttributesProcessor.process(reader, writer, transformers, metadataMap);
            
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
