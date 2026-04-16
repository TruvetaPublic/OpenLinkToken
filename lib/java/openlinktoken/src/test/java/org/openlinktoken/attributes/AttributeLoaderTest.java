/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import org.openlinktoken.attributes.general.RecordIdAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;

class AttributeLoaderTest {

    @Test
    void loadAttributes_ShouldLoadAttributes() {
        var attributesSet = AttributeLoader.load();

        var recordIdAttribute = attributesSet.stream()
                .filter(RecordIdAttribute.class::isInstance)
                .findFirst();
        assertTrue(recordIdAttribute.isPresent(), "RecordIdAttribute should be loaded");

        var lastNameAttribute = attributesSet.stream()
                .filter(LastNameAttribute.class::isInstance)
                .findFirst();
        assertTrue(lastNameAttribute.isPresent(), "LastNameAttribute should be loaded");
    }
}
