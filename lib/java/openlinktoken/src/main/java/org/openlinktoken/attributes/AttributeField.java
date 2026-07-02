/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import java.io.Serializable;
import java.util.Objects;

import lombok.Getter;

/**
 * Represents a named field slot in a person record.
 *
 * <p>
 * An {@code AttributeField} separates two concerns that were previously conflated:
 * <ul>
 *   <li><b>Field identity</b> — "which value from the person record?" (the {@code fieldId})</li>
 *   <li><b>Attribute behavior</b> — "how to normalize/validate?" (the {@code attributeClass})</li>
 * </ul>
 *
 * <p>
 * This allows multiple fields to share the same attribute type (e.g., two fields both using
 * {@code StringAttribute} normalization) while remaining distinct keys in the person attributes map.
 */
@Getter
public final class AttributeField implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String fieldId;
    private final Class<? extends Attribute> attributeClass;

    /**
     * Creates an attribute field with the given identity and attribute type.
     *
     * @param fieldId        unique field identifier (e.g., "LastName", "MotherLastName")
     * @param attributeClass the attribute class providing normalization and validation behavior
     */
    public AttributeField(String fieldId, Class<? extends Attribute> attributeClass) {
        this.fieldId = Objects.requireNonNull(fieldId, "fieldId must not be null");
        this.attributeClass = Objects.requireNonNull(attributeClass, "attributeClass must not be null");
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof AttributeField other)) {
            return false;
        }
        return fieldId.equals(other.fieldId);
    }

    @Override
    public int hashCode() {
        return fieldId.hashCode();
    }

    @Override
    public String toString() {
        return "AttributeField{fieldId='" + fieldId + "', attributeClass=" + attributeClass.getSimpleName() + "}";
    }
}
