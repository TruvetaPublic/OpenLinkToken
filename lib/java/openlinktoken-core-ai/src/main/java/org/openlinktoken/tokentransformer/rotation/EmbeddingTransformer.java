/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer.rotation;

import java.util.List;

/**
 * Transforms a raw float embedding vector into a list of token strings.
 *
 * <p>Implementations may apply projection, quantization, or other
 * dimensionality-reduction steps to convert a high-dimensional embedding into
 * one or more compact token representations.
 */
public interface EmbeddingTransformer {

    /**
     * Transform an embedding vector into a list of token strings.
     *
     * @param embedding raw float embedding vector
     * @return list of token strings derived from the embedding; never {@code null}
     */
    List<String> transform(float[] embedding);
}
