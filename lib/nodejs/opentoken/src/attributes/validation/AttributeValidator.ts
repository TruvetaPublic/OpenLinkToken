/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Interface for validators.
 */
export interface AttributeValidator {
  /**
   * Validates the given value.
   *
   * @param value - The value to validate.
   * @returns true if the value is valid; false otherwise.
   */
  validate(value: string): boolean;
}
