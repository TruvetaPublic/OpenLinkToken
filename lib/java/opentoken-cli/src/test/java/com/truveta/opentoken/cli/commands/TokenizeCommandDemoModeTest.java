/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truveta.opentoken.Metadata;

/**
 * Targeted tests for {@code tokenize --demo-mode} mode selection, validation,
 * and output shape.
 *
 * <p>Normal mode requires {@code --hashingsecret} and produces HMAC-SHA256 base64 tokens.
 * Demo mode skips all hashing (SHA-256 and HMAC), producing the raw pipe-separated
 * attribute signature strings and excluding the hashing-secret hash from metadata.
 */
class TokenizeCommandDemoModeTest {

    @TempDir
    Path tempDir;

    private Path inputCsv;
    private Path outputCsv;

    private static final String HASHING_SECRET = "TestHashingSecret";

    /** Two-record input covering all token-rule attributes. */
    private static final String CSV_CONTENT = """
            RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber
            test-001,John,Doe,98004,Male,2000-01-15,123-45-6789
            test-002,Jane,Smith,90210,Female,1985-07-22,234-56-7890
            """;

    /**
     * Pattern for HMAC-SHA256 base64 output produced in normal mode.
     * HMAC-SHA256 always produces 32 bytes → base64 → exactly 44 chars.
     */
    private static final int NORMAL_MODE_TOKEN_LENGTH = 44;

    /**
     * Sentinel value written by the tokenizer when no valid attributes are available
     * for a rule. Matches {@code Token.BLANK} in the core library.
     */
    private static final String BLANK_TOKEN = "0000000000000000000000000000000000000000000000000000000000000000";

    @BeforeEach
    void setUp() throws IOException {
        inputCsv = tempDir.resolve("input.csv");
        outputCsv = tempDir.resolve("output.csv");
        Files.writeString(inputCsv, CSV_CONTENT);
    }

    // -------------------------------------------------------------------------
    // Mode-selection: which transformer path is chosen
    // -------------------------------------------------------------------------

    @Test
    void testDemoMode_SucceedsWithoutHashingSecret() {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--demo-mode"
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertEquals(0, exitCode, "Demo mode should succeed without --hashingsecret");
        assertTrue(Files.exists(outputCsv), "Output file should be created in demo mode");
    }

    @Test
    void testNormalMode_SucceedsWithHashingSecret() {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertEquals(0, exitCode, "Normal mode should succeed with --hashingsecret");
        assertTrue(Files.exists(outputCsv), "Output file should be created in normal mode");
    }

    @Test
    void testDemoMode_AcceptsHashingSecretWithoutError() {
        // --hashingsecret is ignored in demo mode, but providing it must not fail
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--demo-mode",
                "--hashingsecret", HASHING_SECRET
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertEquals(0, exitCode, "Demo mode should accept a --hashingsecret without error");
    }

    // -------------------------------------------------------------------------
    // Validation: flag-combination guard
    // -------------------------------------------------------------------------

    @Test
    void testNormalMode_FailsWithoutHashingSecret() {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString()
                // --hashingsecret intentionally omitted
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertNotEquals(0, exitCode,
                "Normal mode must exit non-zero when --hashingsecret is missing");
    }

    @Test
    void testNormalMode_FailsWithBlankHashingSecret() {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", "   "
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertNotEquals(0, exitCode,
                "Normal mode must exit non-zero when --hashingsecret is blank");
    }

    @Test
    void testDemoMode_FailsWithInvalidInputType() {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "xml",
                "-o", outputCsv.toString(),
                "--demo-mode"
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertNotEquals(0, exitCode,
                "Demo mode should still reject an invalid --type value");
    }

    @Test
    void testDemoMode_FailsWithInvalidOutputType() {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "-ot", "json",
                "--demo-mode"
        };

        int exitCode = OpenTokenCommand.execute(args);
        assertNotEquals(0, exitCode,
                "Demo mode should still reject an invalid --output-type value");
    }

    // -------------------------------------------------------------------------
    // Output shape: token value format
    // -------------------------------------------------------------------------

    @Test
    void testDemoMode_TokensArePlainSignatureStrings() throws IOException {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--demo-mode"
        };

        OpenTokenCommand.execute(args);

        List<String> nonBlankTokens = extractTokenValues(outputCsv);
        assertFalse(nonBlankTokens.isEmpty(), "Expected at least one non-blank token in demo mode");

        // Multi-attribute rules (T1-T4) produce pipe-separated signatures
        assertTrue(nonBlankTokens.stream().anyMatch(t -> t.contains("|")),
                "At least one demo-mode token must be a pipe-separated signature (T1-T4 rules)");

        // HMAC-SHA256 base64 output is always exactly 44 chars; raw signatures never are
        for (String token : nonBlankTokens) {
            assertNotEquals(NORMAL_MODE_TOKEN_LENGTH, token.length(),
                    "Demo-mode tokens must not be 44-char HMAC base64 strings, but got: " + token);
        }
    }

    @Test
    void testNormalMode_TokensAreBase64HmacStrings() throws IOException {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        OpenTokenCommand.execute(args);

        List<String> nonBlankTokens = extractTokenValues(outputCsv);
        assertFalse(nonBlankTokens.isEmpty(), "Expected at least one non-blank token in normal mode");
        for (String token : nonBlankTokens) {
            // HMAC-SHA256 base64 tokens are always exactly 44 chars
            assertEquals(NORMAL_MODE_TOKEN_LENGTH, token.length(),
                    "Normal-mode tokens must be 44-char HMAC base64 strings but got: " + token);
        }
    }

    @Test
    void testDemoMode_AndNormalMode_ProduceDifferentTokensForSameInput() throws IOException {
        Path outputDemo = tempDir.resolve("output_demo.csv");
        Path outputNormal = tempDir.resolve("output_normal.csv");

        OpenTokenCommand.execute(new String[] {
                "tokenize", "-i", inputCsv.toString(), "-t", "csv",
                "-o", outputDemo.toString(), "--demo-mode"
        });
        OpenTokenCommand.execute(new String[] {
                "tokenize", "-i", inputCsv.toString(), "-t", "csv",
                "-o", outputNormal.toString(), "--hashingsecret", HASHING_SECRET
        });

        List<String> demoTokens = extractTokenValues(outputDemo);
        List<String> normalTokens = extractTokenValues(outputNormal);

        assertFalse(demoTokens.isEmpty(), "Demo output must contain tokens");
        assertFalse(normalTokens.isEmpty(), "Normal output must contain tokens");
        assertNotEquals(demoTokens, normalTokens,
                "Demo-mode and normal-mode must produce different token values for the same input");
    }

    /**
     * Reads the output CSV at {@code path}, locates the "Token" column via the header row,
     * and returns all non-empty token values.
     */
    private List<String> extractTokenValues(Path path) throws IOException {
        String[] lines = Files.readString(path).strip().split("\n");
        assertTrue(lines.length > 1, "Output CSV should contain a header and at least one data row");

        // Locate the Token column index from the header row
        String[] headers = lines[0].split(",");
        int tokenColIdx = -1;
        for (int c = 0; c < headers.length; c++) {
            if ("Token".equalsIgnoreCase(headers[c].trim())) {
                tokenColIdx = c;
                break;
            }
        }
        assertTrue(tokenColIdx >= 0, "Output CSV header must contain a 'Token' column");

        List<String> tokens = new ArrayList<>();
        for (int i = 1; i < lines.length; i++) {
            String[] cols = lines[i].split(",");
            if (cols.length > tokenColIdx) {
                String token = cols[tokenColIdx].trim();
                // Skip empty strings and the BLANK sentinel (64-zero placeholder for
                // token rules where no valid attributes were available)
                if (!token.isEmpty() && !token.equals(BLANK_TOKEN)) {
                    tokens.add(token);
                }
            }
        }
        return tokens;
    }

    // -------------------------------------------------------------------------
    // Metadata: hashing-secret hash presence
    // -------------------------------------------------------------------------

    @Test
    void testDemoMode_MetadataOmitsHashingSecretHash() throws IOException {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--demo-mode"
        };

        OpenTokenCommand.execute(args);

        Path metadataPath = tempDir.resolve("output.metadata.json");
        assertTrue(Files.exists(metadataPath), "Metadata file should be created in demo mode");

        ObjectMapper mapper = new ObjectMapper();
        JsonNode root = mapper.readTree(metadataPath.toFile());

        assertFalse(root.has(Metadata.HASHING_SECRET_HASH),
                "Demo-mode metadata must not contain " + Metadata.HASHING_SECRET_HASH);
    }

    @Test
    void testNormalMode_MetadataContainsHashingSecretHash() throws IOException {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--hashingsecret", HASHING_SECRET
        };

        OpenTokenCommand.execute(args);

        Path metadataPath = tempDir.resolve("output.metadata.json");
        assertTrue(Files.exists(metadataPath), "Metadata file should be created in normal mode");

        ObjectMapper mapper = new ObjectMapper();
        JsonNode root = mapper.readTree(metadataPath.toFile());

        assertTrue(root.has(Metadata.HASHING_SECRET_HASH),
                "Normal-mode metadata must contain " + Metadata.HASHING_SECRET_HASH);
        assertFalse(root.get(Metadata.HASHING_SECRET_HASH).asText().isEmpty(),
                "HashingSecretHash must not be empty in normal mode");
    }

    @Test
    void testDemoMode_MetadataContainsProcessingCounters() throws IOException {
        var args = new String[] {
                "tokenize",
                "-i", inputCsv.toString(),
                "-t", "csv",
                "-o", outputCsv.toString(),
                "--demo-mode"
        };

        OpenTokenCommand.execute(args);

        Path metadataPath = tempDir.resolve("output.metadata.json");
        ObjectMapper mapper = new ObjectMapper();
        JsonNode root = mapper.readTree(metadataPath.toFile());

        // Processing counters must still be present regardless of mode
        assertTrue(root.has("TotalRows"), "Metadata must contain TotalRows");
        assertTrue(root.has("TotalRowsWithInvalidAttributes"),
                "Metadata must contain TotalRowsWithInvalidAttributes");
        assertTrue(root.has("InvalidAttributesByType"),
                "Metadata must contain InvalidAttributesByType");
        assertTrue(root.has("BlankTokensByRule"),
                "Metadata must contain BlankTokensByRule");

        assertEquals(2, root.get("TotalRows").asInt(),
                "TotalRows should match the number of rows in the input file");
    }
}
