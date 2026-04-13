/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes;

import java.util.HashSet;
import java.util.ServiceLoader;
import java.util.Set;

public final class AttributeLoader {

    private AttributeLoader() {
    }

    public static Set<Attribute> load() {
        Set<Attribute> attributes = new HashSet<>();
        ServiceLoader<Attribute> loader = ServiceLoader.load(Attribute.class);
        for (Attribute attribute : loader) {
            attributes.add(attribute);
        }
        return attributes;
    }
}
