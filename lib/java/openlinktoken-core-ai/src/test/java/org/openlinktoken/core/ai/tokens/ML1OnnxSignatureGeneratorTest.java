/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Tests ML1 generator behavior that does not require ONNX assets.
 */
class ML1OnnxSignatureGeneratorTest {

    @TempDir
    Path temporaryDirectory;

    private String originalUserHome;

    /**
     * Restores the original home-directory property after a test changes it.
     */
    @AfterEach
    void restoreUserHome() {
        if (originalUserHome != null) {
            System.setProperty("user.home", originalUserHome);
        }
    }

    /**
     * Verifies that a null inference batch produces an empty signatures-and-embeddings result.
     */
    @Test
    void nullBatchReturnsEmptyResult() {
        ML1OnnxSignatureGenerator.GenerationResult result =
                ML1OnnxSignatureGenerator.generateSignaturesAndEmbeddings(null);

        assertTrue(result.signatures().isEmpty());
        assertTrue(result.embeddings().isEmpty());
    }

    /**
     * Verifies that an empty inference batch produces no signatures.
     */
    @Test
    void emptyBatchReturnsEmptySignatures() {
        assertTrue(ML1OnnxSignatureGenerator.generateSignatures(List.of()).isEmpty());
    }

    /**
     * Verifies that a bundled tokenizer path resolves from the source checkout.
     */
    @Test
    void sourceCheckoutResolutionFindsTokenizerWithoutClasspathEmbedding() {
        Path resolved = ML1OnnxSignatureGenerator.resolvePath("classpath:/inferencing/ml1/tokenizer.json");

        assertTrue(Files.isRegularFile(resolved));
        assertTrue(resolved.toString().endsWith(
                Path.of("resources", "inferencing", "ml1", "tokenizer.json").toString()));
    }

    /**
     * Verifies that a missing explicit asset path reports why resolution failed.
     */
    @Test
    void missingExplicitPathHasClearError() {
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> ML1OnnxSignatureGenerator.resolvePath("/tmp/does-not-exist/model.onnx"));

        assertTrue(error.getMessage().contains("Configured ML1 asset path does not exist"));
    }

    /**
     * Verifies that a missing classpath asset explains where local assets belong.
     */
    @Test
    void missingClasspathAssetExplainsLocalPlacement() {
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> ML1OnnxSignatureGenerator.resolvePath("classpath:/inferencing/ml1/missing-tokenizer.json"));

        assertTrue(error.getMessage().contains("do not download"));
        assertTrue(error.getMessage().contains("inferencing/ml1"));
    }

    /**
     * Verifies that {@code ~/} paths use the configured user-home directory.
     *
     * @throws Exception if the temporary model file cannot be created
     */
    @Test
    void expandsHomeDirectoryForExplicitPaths() throws Exception {
        originalUserHome = System.getProperty("user.home");
        System.setProperty("user.home", temporaryDirectory.toString());
        Path modelPath = temporaryDirectory.resolve("model.onnx");
        Files.createFile(modelPath);

        assertEquals(modelPath, ML1OnnxSignatureGenerator.resolvePath("~/model.onnx"));
    }
}
