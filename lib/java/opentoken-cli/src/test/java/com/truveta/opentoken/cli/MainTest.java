/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import com.truveta.opentoken.cli.commands.OpenTokenCommand;

/**
 * Integration tests for {@link Main} class.
 * Tests the end-to-end workflows for token generation and decryption using new subcommand interface.
 */
class MainTest {

    @TempDir
    Path tempDir;

    private Path inputCsv;
    private Path outputCsv;
    private Path outputParquet;
    private PrintStream originalErr;

    private static final String HASHING_SECRET = "TestHashingSecret";
    private static final String ENCRYPTION_KEY = "TestEncryptionKeyValue1234567890"; // Must be exactly 32 chars

    @BeforeEach
    void setUp() throws IOException {
        // Create test input CSV
        inputCsv = tempDir.resolve("input.csv");
        outputCsv = tempDir.resolve("output.csv");
        outputParquet = tempDir.resolve("output.parquet");

        String csvContent = "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
                + "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n"
                + "test-002,Jane,Smith,12345,Female,1990-05-15,234-56-7890\n";
        Files.writeString(inputCsv, csvContent);

        // Capture stderr for error logging verification
        originalErr = System.err;
    }

    @AfterEach
    void tearDown() {
        System.setErr(originalErr);
    }

    @Test
    void testPackageCommandCsvToCsv() throws IOException {
        String[] args = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET,
                "--encryptionkey", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(args));

        assertTrue(Files.exists(outputCsv), "Output CSV should be created");
        assertTrue(Files.size(outputCsv) > 0, "Output CSV should not be empty");

        // Check metadata file
        Path metadataPath = tempDir.resolve("output.metadata.json");
        assertTrue(Files.exists(metadataPath), "Metadata file should be created");
    }

    @Test
    void testPackageCommandCsvToParquet() throws IOException {
        String[] args = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputParquet.toString(),
                "-ot", "parquet",
                "--hashingsecret", HASHING_SECRET,
                "--encryptionkey", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(args));

        assertTrue(Files.exists(outputParquet), "Output Parquet should be created");
        assertTrue(Files.size(outputParquet) > 0, "Output Parquet should not be empty");
    }

    @Test
    void testTokenizeCommand() throws IOException {
        String[] args = {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(args));

        assertTrue(Files.exists(outputCsv), "Output CSV should be created");
        assertTrue(Files.size(outputCsv) > 0, "Output CSV should not be empty");
    }

    @Test
    void testDecryptCommand() throws IOException {
        // First, generate encrypted tokens
        String[] encryptArgs = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET,
                "--encryptionkey", ENCRYPTION_KEY
        };
        OpenTokenCommand.execute(encryptArgs);

        // Now decrypt them
        Path decryptedCsv = tempDir.resolve("decrypted.csv");
        String[] decryptArgs = {
                "decrypt",
                "-i", outputCsv.toString(),
                "-t", "csv",
                "-o", decryptedCsv.toString(),
                "--encryptionkey", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(decryptArgs));

        assertTrue(Files.exists(decryptedCsv), "Decrypted CSV should be created");
        assertTrue(Files.size(decryptedCsv) > 0, "Decrypted CSV should not be empty");
    }

    @Test
    void testOutputTypeDefaultsToInputType() throws IOException {
        String[] args = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET,
                "--encryptionkey", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(args));

        // Verify CSV output was created (same as input type)
        assertTrue(Files.exists(outputCsv));
        String content = Files.readString(outputCsv);
        assertTrue(content.contains("RecordId"));
    }

    @Test
    void testParquetInputToParquetOutput() throws IOException {
        // First create a parquet file from CSV
        Path tempParquet = tempDir.resolve("temp.parquet");
        String[] createArgs = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", tempParquet.toString(),
                "-ot", "parquet",
                "--hashingsecret", HASHING_SECRET,
                "--encryptionkey", ENCRYPTION_KEY
        };
        OpenTokenCommand.execute(createArgs);

        // Now use parquet as input
        Path outputParquet2 = tempDir.resolve("output2.parquet");
        String[] args = {
                "decrypt",
                "-i", tempParquet.toString(),
                "-t", "parquet",
                "-o", outputParquet2.toString(),
                "--encryptionkey", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(args));
    }

    @Test
    void testDecryptCsvToParquet() throws IOException {
        // First generate encrypted tokens
        String[] encryptArgs = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET,
                "--encryptionkey", ENCRYPTION_KEY
        };
        OpenTokenCommand.execute(encryptArgs);

        // Decrypt CSV to Parquet
        Path decryptedParquet = tempDir.resolve("decrypted.parquet");
        String[] decryptArgs = {
                "decrypt",
                "-i", outputCsv.toString(),
                "-t", "csv",
                "-o", decryptedParquet.toString(),
                "-ot", "parquet",
                "--encryptionkey", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> OpenTokenCommand.execute(decryptArgs));
        assertTrue(Files.exists(decryptedParquet));
    }

    // ===== Negative Test Cases =====

    @Test
    void testMissingRequiredParameter_HashingSecret() {
        String[] args = {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString()
                // Missing --hashingsecret
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for missing required parameter");
    }

    @Test
    void testMissingRequiredParameter_EncryptionKey() {
        String[] args = {
                "encrypt",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString()
                // Missing --encryptionkey
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for missing required parameter");
    }

    @Test
    void testMissingRequiredParameter_Input() {
        String[] args = {
                "tokenize",
                // Missing -i/--input
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for missing required parameter");
    }

    @Test
    void testMissingRequiredParameter_Output() {
        String[] args = {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                // Missing -o/--output
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for missing required parameter");
    }

    @Test
    void testInvalidInputType() {
        String[] args = {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "invalid_type", // Invalid input type
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for invalid input type");
    }

    @Test
    void testInvalidOutputType() {
        String[] args = {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-ot", "invalid_type", // Invalid output type
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for invalid output type");
    }

    @Test
    void testNonExistentInputFile() {
        Path nonExistentFile = tempDir.resolve("nonexistent.csv");

        String[] args = {
                "tokenize",
                "-i", nonExistentFile.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for non-existent input file");
    }

    @Test
    void testPackageCommandMissingBothSecrets() {
        String[] args = {
                "package",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString()
                // Missing both --hashingsecret and --encryptionkey
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertTrue(exitCode != 0, "Command should exit with non-zero code for missing required parameters");
    }
}
