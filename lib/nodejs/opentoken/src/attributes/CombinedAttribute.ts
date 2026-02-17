/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { SerializableAttribute } from './SerializableAttribute';

/**
 * Abstract base class for attributes that combine multiple attribute implementations.
 *
 * This class allows for combining multiple attribute implementations where each
 * implementation handles a specific subset of validation and normalization logic.
 * The combined attribute will iterate through all implementations until it finds
 * one that reports the string as valid for validation, and uses the first
 * implementation that can normalize the value for normalization.
 *
 * Subclasses must implement getAttributeImplementations() to provide
 * the list of attribute implementations to combine.
 */
export abstract class CombinedAttribute extends SerializableAttribute {
  /**
   * Gets the list of attribute implementations to combine.
   */
  protected abstract getAttributeImplementations(): SerializableAttribute[];

  /**
   * Validates the attribute value by checking if any of the combined
   * implementations consider the value valid.
   *
   * @param value - The attribute value to validate.
   * @returns true if any implementation validates the value successfully; false otherwise.
   */
  validate(value: string): boolean {
    if (!value) {
      return false;
    }

    return this.getAttributeImplementations().some((impl) => impl.validate(value));
  }

  /**
   * Normalizes the attribute value using the first implementation that
   * successfully validates the value.
   *
   * @param value - The attribute value to normalize.
   * @returns The normalized value from the first validating implementation,
   *          or the original trimmed value if no implementation validates it.
   */
  normalize(value: string): string {
    if (!value) {
      return value;
    }

    for (const impl of this.getAttributeImplementations()) {
      if (impl.validate(value)) {
        return impl.normalize(value);
      }
    }

    // If no implementation validates the value, return trimmed original
    return value.trim();
  }
}
