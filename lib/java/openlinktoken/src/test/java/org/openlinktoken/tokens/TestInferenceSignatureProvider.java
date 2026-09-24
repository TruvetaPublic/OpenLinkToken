/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;
import java.util.Map;

/** Provides deterministic ML1 signatures for token-generation tests. */
public class TestInferenceSignatureProvider implements InferenceSignatureProvider {

    /** Returns the inference rule identifier used by this test provider. */
    @Override
    public String getTokenId() {
        return "ML1";
    }

    /** Indicates that this test provider participates in inference. */
    @Override
    public boolean isEnabled() {
        return true;
    }

    /**
     * Builds a test signature from the last-name field.
     *
     * @param personAttributes person fields keyed by attribute name
     * @return the last name followed by {@code -provider}, or {@code null} if no last name is present
     */
    @Override
    public String generateSignature(Map<String, String> personAttributes) {
        String lastName = personAttributes.get("LastName");
        return lastName == null ? null : lastName + "-provider";
    }

    /**
     * Generates one test signature for each input row.
     *
     * @param rows person-field maps to process
     * @return signatures in the same order as the input rows
     */
    @Override
    public InferenceBatchResult generateBatch(List<Map<String, String>> rows) {
        return new InferenceBatchResult(rows.stream().map(this::generateSignature).toList());
    }
}
