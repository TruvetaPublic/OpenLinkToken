/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import java.util.HashSet;
import java.util.ServiceLoader;
import java.util.Set;

/**
 * Discovers attribute implementations registered with {@link ServiceLoader}.
 */
public final class AttributeLoader {

    /** Prevents instantiation of this utility class. */
    private AttributeLoader() {
    }

    /**
     * Loads the registered attribute implementations.
     *
     * @return a set containing the discovered attributes
     */
    public static Set<Attribute> load() {
        Set<Attribute> attributes = new HashSet<>();
        ServiceLoader<Attribute> loader = ServiceLoader.load(Attribute.class);
        for (Attribute attribute : loader) {
            attributes.add(attribute);
        }
        return attributes;
    }
}
