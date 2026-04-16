/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes;

import java.io.Serializable;

/**
 * An extension of the {@link Attribute} interface that is also serializable.
 *
 * <p>
 * This interface should be implemented by attribute classes that need to be
 * serialized, such as when they are transmitted over a network or stored in a
 * persistent data store.
 * </p>
 *
 * <p>
 * Implementing classes must ensure that all their fields are serializable or
 * marked as transient if they cannot be serialized.
 * </p>
 */
public interface SerializableAttribute extends Attribute, Serializable {
    // This is a marker interface that combines Attribute and Serializable
    // No additional methods are required
}
