/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokens.definitions;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Tests the ML1 token definition metadata.
 */
class ML1TokenTest {

    /**
     * Verifies that the token exposes the stable ML1 identifier.
     */
    @Test
    void identifierIsMl1() {
        assertEquals("ML1", new ML1Token().getIdentifier());
    }

    /**
     * Verifies that ML1 has no attribute expressions in its definition.
     */
    @Test
    void definitionIsEmpty() {
        assertTrue(new ML1Token().getDefinition().isEmpty());
    }
}
