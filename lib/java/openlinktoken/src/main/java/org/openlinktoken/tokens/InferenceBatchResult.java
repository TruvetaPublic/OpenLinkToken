/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;

/** Holds the signatures produced by a batched inference pass in input row order. */
public record InferenceBatchResult(List<String> signatures) {}
