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

/**
 * Integration tests for {@link Main} class.
 * Tests the end-to-end workflows for token generation and decryption.
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
    void testTokenGenerationCsvToCsv() throws IOException {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(args));

        assertTrue(Files.exists(outputCsv), "Output CSV should be created");
        assertTrue(Files.size(outputCsv) > 0, "Output CSV should not be empty");

        // Check metadata file
        Path metadataPath = tempDir.resolve("output.metadata.json");
        assertTrue(Files.exists(metadataPath), "Metadata file should be created");
    }

    @Test
    void testTokenGenerationCsvToParquet() throws IOException {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputParquet.toString(),
                "-ot", "parquet",
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(args));

        assertTrue(Files.exists(outputParquet), "Output Parquet should be created");
        assertTrue(Files.size(outputParquet) > 0, "Output Parquet should not be empty");
    }

    @Test
    void testHashOnlyMode() throws IOException {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "--hash-only"
        };

        assertDoesNotThrow(() -> Main.main(args));

        assertTrue(Files.exists(outputCsv), "Output CSV should be created");
        assertTrue(Files.size(outputCsv) > 0, "Output CSV should not be empty");
    }

    @Test
    void testDecryptMode() throws IOException {
        // First, generate encrypted tokens
        String[] encryptArgs = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };
        Main.main(encryptArgs);

        // Now decrypt them
        Path decryptedCsv = tempDir.resolve("decrypted.csv");
        String[] decryptArgs = {
                "-d",
                "-i", outputCsv.toString(),
                "-t", "csv",
                "-o", decryptedCsv.toString(),
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(decryptArgs));

        assertTrue(Files.exists(decryptedCsv), "Decrypted CSV should be created");
        assertTrue(Files.size(decryptedCsv) > 0, "Decrypted CSV should not be empty");
    }

    @Test
    void testInvalidInputType() throws IOException {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "invalid",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };

        // Should not throw, but should log error and return early
        assertDoesNotThrow(() -> Main.main(args));
        // Output should not exist due to early exit
        assertTrue(!Files.exists(outputCsv) || Files.size(outputCsv) == 0);
    }

    @Test
    void testInvalidOutputType() {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-ot", "invalid",
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };

        // Should not throw, but should log error and return early
        assertDoesNotThrow(() -> Main.main(args));
    }

    @Test
    void testMissingHashingSecret() {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-e", ENCRYPTION_KEY
        };

        // Should not throw, but should log error and return early
        assertDoesNotThrow(() -> Main.main(args));
    }

    @Test
    void testMissingEncryptionKeyWithoutHashOnly() {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET
        };

        // Should not throw, but should log error and return early
        assertDoesNotThrow(() -> Main.main(args));
    }

    @Test
    void testDecryptModeWithMissingEncryptionKey() throws IOException {
        // Create a dummy encrypted tokens file
        Path dummyTokens = tempDir.resolve("tokens.csv");
        Files.writeString(dummyTokens, "RecordId,RuleId,Token\ntest-001,T1,encrypted_token\n");

        String[] args = {
                "-d",
                "-i", dummyTokens.toString(),
                "-t", "csv",
                "-o", outputCsv.toString()
        };

        // Should not throw, but should log error and return early
        assertDoesNotThrow(() -> Main.main(args));
    }

    @Test
    void testOutputTypeDefaultsToInputType() throws IOException {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(args));

        // Verify CSV output was created (same as input type)
        assertTrue(Files.exists(outputCsv));
        String content = Files.readString(outputCsv);
        assertTrue(content.contains("RecordId"));
    }

    @Test
    void testResolveOutputPathDefaultsToTokenizedCsv() {
        String outputPath = Main.resolveOutputPath(inputCsv.toString(), "", "csv", false);
        assertTrue(outputPath.endsWith("input_tokenized.csv"));
    }

    @Test
    void testResolveOutputPathUsesRequestedExtension() {
        String outputPath = Main.resolveOutputPath(inputCsv.toString(), "", "parquet", false);
        assertTrue(outputPath.endsWith("input_tokenized.parquet"));
    }

    @Test
    void testTokenGenerationDefaultsOutputPath() throws IOException {
        String[] args = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(args));

        Path defaultOutput = tempDir.resolve("input_tokenized.csv");
        assertTrue(Files.exists(defaultOutput), "Derived output CSV should be created");
        assertTrue(Files.exists(tempDir.resolve("input_tokenized.metadata.json")), "Derived metadata file should be created");
    }

    @Test
    void testDecryptDefaultsOutputPath() throws IOException {
        String[] encryptArgs = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };
        Main.main(encryptArgs);

        String[] decryptArgs = {
                "-d",
                "-i", outputCsv.toString(),
                "-t", "csv",
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(decryptArgs));

        Path defaultOutput = tempDir.resolve("output_decrypted.csv");
        assertTrue(Files.exists(defaultOutput), "Derived decrypted CSV should be created");
    }

    @Test
    void testParquetInputToParquetOutput() throws IOException {
        // First create a parquet file from CSV
        Path tempParquet = tempDir.resolve("temp.parquet");
        String[] createArgs = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", tempParquet.toString(),
                "-ot", "parquet",
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };
        Main.main(createArgs);

        // Now use parquet as input
        Path outputParquet2 = tempDir.resolve("output2.parquet");
        String[] args = {
                "-d",
                "-i", tempParquet.toString(),
                "-t", "parquet",
                "-o", outputParquet2.toString(),
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(args));
    }

    @Test
    void testDecryptCsvToParquet() throws IOException {
        // First generate encrypted tokens
        String[] encryptArgs = {
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-h", HASHING_SECRET,
                "-e", ENCRYPTION_KEY
        };
        Main.main(encryptArgs);

        // Decrypt CSV to Parquet
        Path decryptedParquet = tempDir.resolve("decrypted.parquet");
        String[] decryptArgs = {
                "-d",
                "-i", outputCsv.toString(),
                "-t", "csv",
                "-o", decryptedParquet.toString(),
                "-ot", "parquet",
                "-e", ENCRYPTION_KEY
        };

        assertDoesNotThrow(() -> Main.main(decryptArgs));
        assertTrue(Files.exists(decryptedParquet));
    }
}
