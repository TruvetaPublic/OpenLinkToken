/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/**
 * Tests ML1 generator behavior that does not require ONNX assets.
 */
class ML1OnnxSignatureGeneratorTest {

    @AfterEach
    void resetAssetStorage() {
        ML1InferenceConfig.configureAssetStorage(
                ML1InferenceConfig.DEFAULT_ASSET_REF,
                ML1InferenceConfig.DEFAULT_ASSET_CACHE_DIRECTORY);
    }

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

    @Test
    void buildsGithubLfsMediaUrlForConfiguredRef() {
        assertEquals(
                "https://media.githubusercontent.com/media/TruvetaPublic/OpenLinkToken/"
                        + "refs/test/resources/inferencing/ml1/model.onnx",
                ML1OnnxSignatureGenerator.buildAssetUrl("refs/test", "model.onnx"));
    }

    @Test
    void buildsRawGithubUrlForRegularTokenizerAsset() {
        assertEquals(
                "https://raw.githubusercontent.com/TruvetaPublic/OpenLinkToken/"
                        + "refs/test/resources/inferencing/ml1/tokenizer.json",
                ML1OnnxSignatureGenerator.buildAssetUrl("refs/test", "tokenizer.json"));
    }

    @Test
    void cachePathIsExplicitAndScopedToAssetRef() {
        ML1InferenceConfig.configureAssetStorage("refs/test", "/tmp/ml1-assets");

        assertEquals(
                Path.of("/tmp/ml1-assets", "refs", "test", "model.onnx"),
                ML1OnnxSignatureGenerator.assetCachePath("model.onnx"));
    }

    @Test
    void rejectsAssetRefsThatEscapeTheCacheDirectory() {
        ML1InferenceConfig.configureAssetStorage("release/../other", "/tmp/ml1-assets");

        assertThrows(
                IllegalArgumentException.class,
                () -> ML1OnnxSignatureGenerator.assetCachePath("model.onnx"));
    }

    @Test
    void readsSmallManifestWithoutLoadingModel() {
        Map<String, ML1OnnxSignatureGenerator.AssetManifestEntry> manifest =
                ML1OnnxSignatureGenerator.readAssetManifest();

        assertEquals(
                "9d3479558460ec499106c0fa5a1d2c004e158514436aeaef1156016e5890c4aa",
                manifest.get("model.onnx").sha256());
        assertEquals(226869L, manifest.get("model.onnx").size());
        assertFalse(manifest.containsKey("missing.onnx"));
    }

    @Test
    void sourceCheckoutResolutionFindsTokenizerWithoutClasspathEmbedding() {
        Path resolved = ML1OnnxSignatureGenerator.resolvePath("classpath:/inferencing/ml1/tokenizer.json");

        assertTrue(Files.isRegularFile(resolved));
        assertTrue(resolved.toString().endsWith(
                Path.of("resources", "inferencing", "ml1", "tokenizer.json").toString()));
    }

    @Test
    void missingExplicitPathHasClearError() {
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> ML1OnnxSignatureGenerator.resolvePath("/tmp/does-not-exist/model.onnx"));

        assertTrue(error.getMessage().contains("Configured ML1 asset path does not exist"));
    }

    @Test
    void offlineEnvironmentBlocksRemoteAssetResolution() {
        if (!ML1InferenceConfig.isOffline()) {
            return;
        }

        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> ML1OnnxSignatureGenerator.ensureDownloadedAsset("model.onnx"));

        assertTrue(error.getMessage().contains("OPENLINKTOKEN_ML1_OFFLINE=1"));
    }
}
