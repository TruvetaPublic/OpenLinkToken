/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

import java.util.List;
import java.util.Map;

public class TestInferenceSignatureProvider implements InferenceSignatureProvider {

    @Override
    public String getTokenId() {
        return "ML1";
    }

    @Override
    public boolean isEnabled() {
        return true;
    }

    @Override
    public String generateSignature(Map<String, String> personAttributes) {
        String lastName = personAttributes.get("LastName");
        return lastName == null ? null : lastName + "-provider";
    }

    @Override
    public InferenceBatchResult generateBatch(List<Map<String, String>> rows) {
        return new InferenceBatchResult(rows.stream().map(this::generateSignature).toList());
    }
}
