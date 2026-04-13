/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes.validation;

import java.io.Serializable;

/**
 * An extension of the {@link AttributeValidator} interface that is also
 * serializable.
 *
 * <p>
 * This interface should be implemented by validator classes that need to be
 * serialized, such as when they are part of serializable attributes or need to
 * be
 * transmitted over a network.
 * </p>
 *
 * <p>
 * Implementing classes must ensure that all their fields are serializable or
 * marked as transient if they cannot be serialized.
 * </p>
 */
public interface SerializableAttributeValidator extends AttributeValidator, Serializable {
    // This is a marker interface that combines AttributeValidator and Serializable
    // No additional methods are required
}
