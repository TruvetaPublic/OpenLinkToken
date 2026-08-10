/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;

/**
 * Holds the results produced by a batched inference pass.
 *
 * <p>Each signature has the same index as its input row. Invalid rows are represented by
 * {@code null}, while valid signatures are hex-encoded token values.
 *
 * @param signatures signatures aligned with the input rows
 */
public record InferenceBatchResult(List<String> signatures) {}
