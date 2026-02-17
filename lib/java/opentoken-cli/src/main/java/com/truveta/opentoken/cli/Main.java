/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.beust.jcommander.JCommander;
import com.truveta.opentoken.Metadata;
import com.truveta.opentoken.cli.io.MetadataWriter;
import com.truveta.opentoken.cli.io.PersonAttributesReader;
import com.truveta.opentoken.cli.io.PersonAttributesWriter;
import com.truveta.opentoken.cli.io.TokenReader;
import com.truveta.opentoken.cli.io.TokenWriter;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVReader;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVWriter;
import com.truveta.opentoken.cli.io.csv.TokenCSVReader;
import com.truveta.opentoken.cli.io.csv.TokenCSVWriter;
import com.truveta.opentoken.cli.io.json.MetadataJsonWriter;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetReader;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetWriter;
import com.truveta.opentoken.cli.io.parquet.TokenParquetReader;
import com.truveta.opentoken.cli.io.parquet.TokenParquetWriter;
import com.truveta.opentoken.cli.processor.PersonAttributesProcessor;
import com.truveta.opentoken.cli.processor.TokenDecryptionProcessor;
import com.truveta.opentoken.tokentransformer.DecryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.HashTokenTransformer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

/**
 * Entry point for the OpenToken command-line application.
 * <p>
 * This class orchestrates two primary workflows:
 * <ul>
 *   <li><b>Encrypt mode</b>: Reads person attributes (CSV/Parquet), validates and
 *   normalizes them, generates tokens via HMAC-SHA256 hashing and AES-256 encryption,
 *   writes tokens to CSV/Parquet, and emits a metadata JSON file.</li>
 *   <li><b>Decrypt mode</b>: Reads encrypted tokens (CSV/Parquet) and writes
 *   decrypted tokens to CSV/Parquet.</li>
 * </ul>
 * Input and output formats support CSV and Parquet.
 */
public class Main {

    private static final Logger logger = LoggerFactory.getLogger(Main.class);

    /**
     * Application entry point. Parses command-line arguments, validates them, and
     * routes execution to encryption or decryption workflows.
     *
     * @param args command-line arguments
     * @throws IOException if an I/O error occurs while creating readers or writers
     */
    public static void main(String[] args) throws IOException {
        CommandLineArguments commandLineArguments = loadCommandLineArguments(args);
        String hashingSecret = commandLineArguments.getHashingSecret();
        String encryptionKey = commandLineArguments.getEncryptionKey();
        String inputPath = commandLineArguments.getInputPath();
        String inputType = commandLineArguments.getInputType();
        String outputPath = commandLineArguments.getOutputPath();
        String outputType = commandLineArguments.getOutputType();
        boolean decryptMode = commandLineArguments.isDecrypt();
        boolean hashOnlyMode = commandLineArguments.isHashOnly();
        String ringId = commandLineArguments.getRingId();

        if (outputType == null || outputType.isEmpty()) {
            outputType = inputType; // defaulting to input type if not provided
        }

        logger.info("Decrypt Mode: {}", decryptMode);
        logger.info("Hash-Only Mode: {}", hashOnlyMode);
        logger.info("Ring ID: {}", ringId);
        if (logger.isInfoEnabled()) {
            logger.info("Hashing Secret: {}", maskString(hashingSecret));
            logger.info("Encryption Key: {}", maskString(encryptionKey));
        }
        logger.info("Input Path: {}", inputPath);
        logger.info("Input Type: {}", inputType);
        logger.info("Output Path: {}", outputPath);
        logger.info("Output Type: {}", outputType);

        // Validate input and output types for both modes
        if (!(CommandLineArguments.TYPE_CSV.equals(inputType)
                || CommandLineArguments.TYPE_PARQUET.equals(inputType))) {
            logger.error("Only csv and parquet input types are supported!");
            return;
        }
        if (!(CommandLineArguments.TYPE_CSV.equals(outputType)
                || CommandLineArguments.TYPE_PARQUET.equals(outputType))) {
            logger.error("Only csv and parquet output types are supported!");
            return;
        }

        // Process based on mode
        if (decryptMode) {
            // Decrypt mode - process encrypted tokens
            if (encryptionKey == null || encryptionKey.isBlank()) {
                logger.error("Encryption key must be specified for decryption");
                return;
            }

            decryptTokens(inputPath, outputPath, inputType, outputType, encryptionKey);
            logger.info("Token decryption completed successfully.");
        } else {
            // Token generation mode - validate and process person attributes
            // Hashing secret is always required
            if (hashingSecret == null || hashingSecret.isBlank()) {
                logger.error("Hashing secret must be specified");
                return;
            }

            // Encryption key is only required when not in hash-only mode
            if (!hashOnlyMode && (encryptionKey == null || encryptionKey.isBlank())) {
                logger.error("Encryption key must be specified (or use --hash-only to skip encryption)");
                return;
            }

            processTokens(inputPath, outputPath, inputType, outputType, hashingSecret, encryptionKey, hashOnlyMode,
                    ringId);
        }
    }

    private static void processTokens(String inputPath, String outputPath, String inputType, String outputType,
            String hashingSecret, String encryptionKey, boolean hashOnlyMode, String ringId) {
        List<TokenTransformer> tokenTransformerList = new ArrayList<>();
        try {
            // Always add hash transformer
            tokenTransformerList.add(new HashTokenTransformer(hashingSecret));

            // Only add encryption transformer if not in hash-only mode
            if (!hashOnlyMode) {
                tokenTransformerList.add(new EncryptTokenTransformer(encryptionKey));
            }
        } catch (Exception e) {
            logger.error("Error in initializing the transformer. Execution halted. ", e);
            return;
        }

        try (PersonAttributesReader reader = createPersonAttributesReader(inputPath, inputType);
                PersonAttributesWriter writer = createPersonAttributesWriter(outputPath, outputType)) {

            // Create initial metadata with system information
            Metadata metadata = new Metadata();
            Map<String, Object> metadataMap = metadata.initialize();

            // Set hashing secret
            metadata.addHashedSecret(Metadata.HASHING_SECRET_HASH, hashingSecret);

            // Set encryption secret if applicable
            if (!hashOnlyMode) {
                metadata.addHashedSecret(Metadata.ENCRYPTION_SECRET_HASH, encryptionKey);
            }

            // Process data and get updated metadata
            // Pass encryption key and ring ID for JWE wrapping (only if not in hash-only mode)
            PersonAttributesProcessor.process(reader, writer, tokenTransformerList, metadataMap,
                    hashOnlyMode ? null : encryptionKey, ringId);

            // Write the metadata to file
            MetadataWriter metadataWriter = new MetadataJsonWriter(outputPath);
            metadataWriter.write(metadataMap);

        } catch (Exception e) {
            logger.error("Error in processing the input file. Execution halted. ", e);
        }
    }

    /**
     * Creates a {@link PersonAttributesReader} for the given input type.
     *
     * @param inputPath path to the person attributes file
     * @param inputType input type ("csv" or "parquet")
     * @return a reader capable of streaming person attributes
     * @throws IOException if the reader cannot be created
     * @throws IllegalArgumentException if the input type is unsupported
     */
    private static PersonAttributesReader createPersonAttributesReader(String inputPath, String inputType)
            throws IOException {
        switch (inputType.toLowerCase()) {
            case CommandLineArguments.TYPE_CSV:
                return new PersonAttributesCSVReader(inputPath);
            case CommandLineArguments.TYPE_PARQUET:
                return new PersonAttributesParquetReader(inputPath);
            default:
                throw new IllegalArgumentException("Unsupported input type: " + inputType);
        }
    }

    /**
     * Creates a {@link PersonAttributesWriter} for the given output type.
     *
     * @param outputPath path to write the transformed tokens file
     * @param outputType output type ("csv" or "parquet")
     * @return a writer capable of streaming tokens
     * @throws IOException if the writer cannot be created
     * @throws IllegalArgumentException if the output type is unsupported
     */
    private static PersonAttributesWriter createPersonAttributesWriter(String outputPath,
            String outputType) throws IOException {
        switch (outputType.toLowerCase()) {
            case CommandLineArguments.TYPE_CSV:
                return new PersonAttributesCSVWriter(outputPath);
            case CommandLineArguments.TYPE_PARQUET:
                return new PersonAttributesParquetWriter(outputPath);
            default:
                throw new IllegalArgumentException("Unsupported output type: " + outputType);
        }
    }

    /**
     * Parses and loads command-line arguments using JCommander.
     *
     * @param args raw command-line arguments
     * @return populated {@link CommandLineArguments}
     */
    private static CommandLineArguments loadCommandLineArguments(String[] args) {
        logger.debug("Processing command line arguments. {}", String.join("|", args));
        CommandLineArguments commandLineArguments = new CommandLineArguments();
        JCommander.newBuilder().addObject(commandLineArguments).build().parse(args);
        logger.info("Command line arguments processed.");
        return commandLineArguments;
    }

    /**
     * Masks a sensitive string by preserving the first three characters and
     * replacing the remainder with asterisks. Returns the input unchanged if the
     * input is {@code null} or has length less than or equal to three.
     *
     * @param input the original sensitive string
     * @return a masked representation suitable for logs
     */
    private static String maskString(String input) {
        if (input == null || input.length() <= 3) {
            return input;
        }
        return input.substring(0, 3) + "*".repeat(input.length() - 3);
    }

    /**
     * Executes the decryption workflow for tokens.
     * <p>
     * Reads encrypted tokens from the specified input, decrypts them using the
     * provided encryption key, and writes the result to the specified output.
     *
     * @param inputPath     path to the input file containing encrypted tokens
     * @param outputPath    path to the output file for decrypted tokens
     * @param inputType     input type ("csv" or "parquet")
     * @param outputType    output type ("csv" or "parquet")
     * @param encryptionKey secret key used for AES-based decryption
     */
    private static void decryptTokens(String inputPath, String outputPath, String inputType, String outputType,
            String encryptionKey) {
        try {
            DecryptTokenTransformer decryptor = new DecryptTokenTransformer(encryptionKey);

            try (TokenReader reader = createTokenReader(inputPath, inputType);
                    TokenWriter writer = createTokenWriter(outputPath, outputType)) {
                TokenDecryptionProcessor.process(reader, writer, decryptor, encryptionKey);
            }
        } catch (Exception e) {
            logger.error("Error during token decryption: ", e);
        }
    }

    /**
     * Creates a {@link TokenReader} for the given input type.
     *
     * @param inputPath path to the token file
     * @param inputType input type ("csv" or "parquet")
     * @return a reader capable of streaming tokens
     * @throws IOException if the reader cannot be created
     * @throws IllegalArgumentException if the input type is unsupported
     */
    private static TokenReader createTokenReader(String inputPath, String inputType) throws IOException {
        switch (inputType.toLowerCase()) {
            case CommandLineArguments.TYPE_CSV:
                return new TokenCSVReader(inputPath);
            case CommandLineArguments.TYPE_PARQUET:
                return new TokenParquetReader(inputPath);
            default:
                throw new IllegalArgumentException("Unsupported input type: " + inputType);
        }
    }

    /**
     * Creates a {@link TokenWriter} for the given output type.
     *
     * @param outputPath path to write tokens
     * @param outputType output type ("csv" or "parquet")
     * @return a writer capable of streaming tokens
     * @throws IOException if the writer cannot be created
     * @throws IllegalArgumentException if the output type is unsupported
     */
    private static TokenWriter createTokenWriter(String outputPath, String outputType) throws IOException {
        switch (outputType.toLowerCase()) {
            case CommandLineArguments.TYPE_CSV:
                return new TokenCSVWriter(outputPath);
            case CommandLineArguments.TYPE_PARQUET:
                return new TokenParquetWriter(outputPath);
            default:
                throw new IllegalArgumentException("Unsupported output type: " + outputType);
        }
    }
}
