/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import java.io.Serializable;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Registry mapping field identifiers to their corresponding {@link Attribute} instances.
 *
 * <p>
 * The {@code FieldRegistry} is the resolution layer that connects field identifiers
 * (string keys used in person-attribute maps) to the attribute instances that provide
 * normalization and validation behavior.
 *
 * <p>
 * Built-in attributes are auto-registered using their canonical name as the field ID.
 * Config-driven fields can register additional mappings (e.g., "MotherLastName" → StringAttribute).
 */
public final class FieldRegistry implements Serializable {

    private static final long serialVersionUID = 1L;

    private final Map<String, AttributeField> fields;
    private final Map<String, Attribute> fieldToAttribute;

    private FieldRegistry(Map<String, AttributeField> fields, Map<String, Attribute> fieldToAttribute) {
        this.fields = Collections.unmodifiableMap(new HashMap<>(fields));
        this.fieldToAttribute = Collections.unmodifiableMap(new HashMap<>(fieldToAttribute));
    }

    /**
     * Creates a default registry populated with all built-in attributes.
     *
     * <p>
     * Each attribute is registered using its canonical name (from {@link Attribute#getName()})
     * as the field ID.
     *
     * @return a new registry with built-in attribute registrations
     */
    public static FieldRegistry createDefault() {
        var builder = new Builder();
        for (Attribute attribute : AttributeLoader.load()) {
            builder.register(attribute.getName(), attribute.getClass(), attribute);
        }
        return builder.build();
    }

    /**
     * Resolves the attribute instance for a given field ID.
     *
     * @param fieldId the field identifier
     * @return an Optional containing the attribute if registered, empty otherwise
     */
    public Optional<Attribute> getAttribute(String fieldId) {
        return Optional.ofNullable(fieldToAttribute.get(fieldId));
    }

    /**
     * Resolves the attribute field definition for a given field ID.
     *
     * @param fieldId the field identifier
     * @return an Optional containing the AttributeField if registered, empty otherwise
     */
    public Optional<AttributeField> getField(String fieldId) {
        return Optional.ofNullable(fields.get(fieldId));
    }

    /**
     * Returns all registered field IDs.
     *
     * @return an unmodifiable set of field identifiers
     */
    public Set<String> getFieldIds() {
        return fields.keySet();
    }

    /**
     * Returns the number of registered fields.
     *
     * @return the registry size
     */
    public int size() {
        return fields.size();
    }

    /**
     * Builder for constructing a {@link FieldRegistry} with custom registrations.
     */
    public static final class Builder {

        private final Map<String, AttributeField> fields = new HashMap<>();
        private final Map<String, Attribute> fieldToAttribute = new HashMap<>();

        public Builder() {
        }

        /**
         * Creates a builder pre-populated with all built-in attribute registrations.
         *
         * @return a new builder with defaults loaded
         */
        public static Builder fromDefaults() {
            var builder = new Builder();
            for (Attribute attribute : AttributeLoader.load()) {
                builder.register(attribute.getName(), attribute.getClass(), attribute);
            }
            return builder;
        }

        /**
         * Registers a field ID with its attribute class and instance.
         *
         * @param fieldId        the unique field identifier
         * @param attributeClass the attribute class providing behavior
         * @param attribute      the attribute instance for normalization/validation
         * @return this builder for chaining
         */
        public Builder register(String fieldId, Class<? extends Attribute> attributeClass, Attribute attribute) {
            fields.put(fieldId, new AttributeField(fieldId, attributeClass));
            fieldToAttribute.put(fieldId, attribute);
            return this;
        }

        /**
         * Builds an immutable {@link FieldRegistry} from the current registrations.
         *
         * @return the constructed registry
         */
        public FieldRegistry build() {
            return new FieldRegistry(fields, fieldToAttribute);
        }
    }
}
