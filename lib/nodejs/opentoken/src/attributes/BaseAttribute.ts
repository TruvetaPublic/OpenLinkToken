/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { Attribute } from './Attribute';
import { AttributeValidator } from './validation/AttributeValidator';

/**
 * Base class for all attributes.
 */
export abstract class BaseAttribute implements Attribute {
  protected name: string;
  protected aliases: string[];
  protected validators: AttributeValidator[];

  /**
   * Constructs a new BaseAttribute.
   *
   * @param name - The name of the attribute.
   * @param aliases - The aliases of the attribute.
   * @param validators - The validators for the attribute.
   */
  constructor(name: string, aliases: string[] = [], validators: AttributeValidator[] = []) {
    this.name = name;
    this.aliases = aliases;
    this.validators = validators;
  }

  getName(): string {
    return this.name;
  }

  getAliases(): string[] {
    return this.aliases;
  }

  /**
   * Normalizes the attribute value.
   * Default implementation returns the value as-is.
   * Subclasses should override this method to provide custom normalization.
   *
   * @param value - The attribute value.
   * @returns The normalized attribute value.
   */
  normalize(value: string): string {
    return value;
  }

  /**
   * Validates the attribute value using all configured validators.
   *
   * @param value - The attribute value.
   * @returns true if the value passes all validators; false otherwise.
   */
  validate(value: string): boolean {
    if (!value || value.trim().length === 0) {
      return false;
    }

    // Run all validators
    for (const validator of this.validators) {
      if (!validator.validate(value)) {
        return false;
      }
    }

    return true;
  }
}
