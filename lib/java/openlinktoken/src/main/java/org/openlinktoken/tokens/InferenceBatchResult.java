/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;

/**
 * Holds the results of a batched inference pass: parallel lists of hex-encoded
 * signatures and raw float embedding vectors in the same order as the input rows.
 */
public record InferenceBatchResult(List<String> signatures, List<float[]> rawEmbeddings) {}
