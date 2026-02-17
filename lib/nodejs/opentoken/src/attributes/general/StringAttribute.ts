/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { SerializableAttribute } from '../SerializableAttribute';
import { AttributeValidator } from '../validation/AttributeValidator';

/**
 * Base class for string-based attributes.
 */
export class StringAttribute extends SerializableAttribute {
  /**
   * Constructs a new StringAttribute.
   *
   * @param name - The name of the attribute.
   * @param aliases - The aliases of the attribute.
   * @param validators - The validators for the attribute.
   */
  constructor(name: string, aliases: string[] = [], validators: AttributeValidator[] = []) {
    super(name, aliases, validators);
  }
}
