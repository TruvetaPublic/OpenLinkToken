/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import com.truveta.openlinktoken.attributes.general.RecordIdAttribute;
import com.truveta.openlinktoken.attributes.person.LastNameAttribute;

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
