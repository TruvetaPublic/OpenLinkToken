/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { SerializableAttribute } from '../SerializableAttribute';
import { AttributeValidator } from '../validation/AttributeValidator';

/**
 * Base class for date-based attributes.
 */
export class DateAttribute extends SerializableAttribute {
  // Supported date format patterns (currently not used, but kept for future validation)
  // private static readonly POSSIBLE_INPUT_FORMATS = [
  //   /^\d{4}-\d{2}-\d{2}$/,    // yyyy-MM-dd
  //   /^\d{4}\/\d{2}\/\d{2}$/,  // yyyy/MM/dd
  //   /^\d{2}\/\d{2}\/\d{4}$/,  // MM/dd/yyyy
  //   /^\d{2}-\d{2}-\d{4}$/,    // MM-dd-yyyy
  //   /^\d{2}\.\d{2}\.\d{4}$/,  // dd.MM.yyyy
  // ];

  /**
   * Constructs a new DateAttribute.
   *
   * @param name - The name of the attribute.
   * @param aliases - The aliases of the attribute.
   * @param validators - The validators for the attribute.
   */
  constructor(name: string, aliases: string[] = [], validators: AttributeValidator[] = []) {
    super(name, aliases, validators);
  }

  /**
   * Normalizes a date string to yyyy-MM-dd format.
   *
   * @param value - The date string to normalize.
   * @returns The normalized date string in yyyy-MM-dd format.
   */
  normalize(value: string): string {
    if (!value || value.trim().length === 0) {
      return value;
    }

    const trimmedValue = value.trim();

    // If already in yyyy-MM-dd format, return as-is
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmedValue)) {
      return trimmedValue;
    }

    // Try yyyy/MM/dd
    if (/^\d{4}\/\d{2}\/\d{2}$/.test(trimmedValue)) {
      return trimmedValue.replace(/\//g, '-');
    }

    // Try MM/dd/yyyy
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(trimmedValue)) {
      const parts = trimmedValue.split('/');
      return `${parts[2]}-${parts[0]}-${parts[1]}`;
    }

    // Try MM-dd-yyyy
    if (/^\d{2}-\d{2}-\d{4}$/.test(trimmedValue)) {
      const parts = trimmedValue.split('-');
      return `${parts[2]}-${parts[0]}-${parts[1]}`;
    }

    // Try dd.MM.yyyy
    if (/^\d{2}\.\d{2}\.\d{4}$/.test(trimmedValue)) {
      const parts = trimmedValue.split('.');
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }

    // If no format matches, return original value
    return trimmedValue;
  }
}
