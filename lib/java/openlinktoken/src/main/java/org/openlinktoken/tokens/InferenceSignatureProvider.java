/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;
import java.util.Map;

/**
 * SPI for inference-based token signature generation.
 *
 * <p>Implementations are discovered at runtime via {@link java.util.ServiceLoader}.
 * When no implementation is on the classpath, inference-based tokens are silently
 * disabled and only standard attribute-expression tokens (T1–T5) are generated.
 *
 * <p>Each provider is responsible for one token identifier (e.g. "ML1") and reports
 * it via {@link #getTokenId()}.
 */
public interface InferenceSignatureProvider {

    /**
     * Return the token identifier this provider handles (e.g. {@code "ML1"}).
     */
    String getTokenId();

    /**
     * Return whether this provider is currently enabled and configured.
     */
    boolean isEnabled();

    /**
     * Generate a single inference-based token signature from the given field-ID values.
     *
     * @param personAttributes field-ID map for one record
     * @return hex-encoded signature string, or {@code null} if the record is invalid
     */
    String generateSignature(Map<String, String> personAttributes);

    /**
     * Generate inference-based token signatures for a batch of records in a single
     * inference pass.
     *
     * @param rows list of field-ID maps, one per record
     * @return {@link InferenceBatchResult} with signatures in input row order
     */
    InferenceBatchResult generateBatch(List<Map<String, String>> rows);
}
