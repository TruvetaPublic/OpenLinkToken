/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.io.IOException;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.cli.io.TokenReader;
import com.truveta.opentoken.cli.io.TokenWriter;
import com.truveta.opentoken.cli.io.csv.TokenCSVReader;
import com.truveta.opentoken.cli.io.csv.TokenCSVWriter;
import com.truveta.opentoken.cli.io.parquet.TokenParquetReader;
import com.truveta.opentoken.cli.io.parquet.TokenParquetWriter;
import com.truveta.opentoken.cli.processor.TokenTransformationProcessor;
import com.truveta.opentoken.cli.util.StringMaskingUtil;
import com.truveta.opentoken.tokentransformer.DecryptTokenTransformer;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Decrypt command - decrypts encrypted tokens.
 */
@Command(
    name = "decrypt",
    description = "Decrypt encrypted tokens using encryption key"
)
public class DecryptCommand implements Callable<Integer> {
    
    private static final Logger logger = LoggerFactory.getLogger(DecryptCommand.class);
    private static final String TYPE_CSV = "csv";
    private static final String TYPE_PARQUET = "parquet";
    
    @Option(names = {"-i", "--input"}, required = true,
            description = "Input file path with encrypted tokens")
    private String inputPath;
    
    @Option(names = {"-o", "--output"}, required = true,
            description = "Output file path for decrypted tokens")
    private String outputPath;
    
    @Option(names = {"-t", "--input-type"}, required = true,
            description = "Input file type: csv or parquet")
    private String inputType;
    
    @Option(names = {"-ot", "--output-type"},
            description = "Output file type (defaults to input type): csv or parquet")
    private String outputType;
    
    @Option(names = {"-e", "--encryptionkey"}, required = true,
            description = "Encryption key for token decryption")
    private String encryptionKey;
    
    @Option(names = {"--help"}, usageHelp = true,
            description = "Show this help message and exit")
    private boolean helpRequested;
    
    @Option(names = {"-V", "--version"}, versionHelp = true,
            description = "Print version information and exit")
    private boolean versionRequested;
    
    @Override
    public Integer call() {
        logger.info("Running decrypt command");
        
        // Default output type to input type if not specified
        if (outputType == null || outputType.isEmpty()) {
            outputType = inputType;
        }
        
        // Log parameters (mask key)
        logger.info("Input: {} ({})", inputPath, inputType);
        logger.info("Output: {} ({})", outputPath, outputType);
        logger.info("Encryption Key: {}", maskString(encryptionKey));
        
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
            decryptTokens();
            logger.info("Token decryption completed successfully");
            return 0;
        } catch (Exception e) {
            logger.error("Error during token decryption", e);
            return 1;
        }
    }
    
    private void decryptTokens() throws IOException {
        try {
            DecryptTokenTransformer decryptor = new DecryptTokenTransformer(encryptionKey);
            
            try (TokenReader reader = createTokenReader(inputPath, inputType);
                 TokenWriter writer = createTokenWriter(outputPath, outputType)) {
                TokenTransformationProcessor.process(reader, writer, decryptor, "decrypted");
            }
        } catch (Exception e) {
            logger.error("Error during token decryption", e);
            throw new RuntimeException("Failed to decrypt tokens", e);
        }
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
