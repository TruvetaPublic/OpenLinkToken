/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeValidator } from './AttributeValidator';

/**
 * An extension of the {@link AttributeValidator} interface that is also serializable.
 *
 * This interface should be implemented by validator classes that need to be
 * serialized, such as when they are part of serializable attributes or need to be
 * transmitted over a network.
 *
 * Implementing classes must ensure that all their fields are serializable or
 * marked as transient if they cannot be serialized.
 *
 * Note: In TypeScript, this is primarily a marker interface since JavaScript
 * objects are inherently serializable to JSON.
 */
export interface SerializableAttributeValidator extends AttributeValidator {
  // This is a marker interface that combines AttributeValidator and Serializable
  // No additional methods are required
}
