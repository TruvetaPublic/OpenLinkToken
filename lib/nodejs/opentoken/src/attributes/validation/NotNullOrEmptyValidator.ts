/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { SerializableAttributeValidator } from './SerializableAttributeValidator';

/**
 * A Validator that asserts the value is **NOT** `null` and blank.
 */
export class NotNullOrEmptyValidator implements SerializableAttributeValidator {
  /**
   * Validates that the attribute value is not `null` or blank.
   *
   * @param value - The value to validate.
   * @returns true if the value is not null and not blank; false otherwise.
   */
  validate(value: string | null | undefined): boolean {
    return value != null && value.trim() !== '';
  }
}
