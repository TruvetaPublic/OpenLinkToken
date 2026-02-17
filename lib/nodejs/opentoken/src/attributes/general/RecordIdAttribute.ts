/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { StringAttribute } from './StringAttribute';

/**
 * Represents an attribute for handling record identifiers.
 *
 * This class extends StringAttribute and provides functionality for working with
 * identifier fields. It recognizes "RecordId" and "Id" as valid aliases for
 * this attribute type.
 *
 * The attribute normalizes values by trimming leading and trailing whitespace.
 */
export class RecordIdAttribute extends StringAttribute {
  private static readonly NAME = 'RecordId';
  private static readonly ALIASES = ['RecordId', 'Id'];

  constructor() {
    super(RecordIdAttribute.NAME, RecordIdAttribute.ALIASES);
  }

  normalize(value: string): string {
    return value ? value.trim() : value;
  }
}
