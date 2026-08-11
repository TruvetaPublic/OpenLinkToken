/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Tests ML1 generator behavior that does not require ONNX assets.
 */
class ML1OnnxSignatureGeneratorTest {

    @Test
    void nullBatchReturnsEmptyResult() {
        ML1OnnxSignatureGenerator.GenerationResult result =
                ML1OnnxSignatureGenerator.generateSignaturesAndEmbeddings(null);

        assertTrue(result.signatures().isEmpty());
        assertTrue(result.embeddings().isEmpty());
    }

    @Test
    void emptyBatchReturnsEmptySignatures() {
        assertTrue(ML1OnnxSignatureGenerator.generateSignatures(List.of()).isEmpty());
    }
}
