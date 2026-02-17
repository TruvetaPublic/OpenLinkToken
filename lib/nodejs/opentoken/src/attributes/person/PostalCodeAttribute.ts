/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { CombinedAttribute } from '../CombinedAttribute';
import { SerializableAttribute } from '../SerializableAttribute';
import { USPostalCodeAttribute } from './USPostalCodeAttribute';
import { CanadianPostalCodeAttribute } from './CanadianPostalCodeAttribute';

/**
 * Represents the postal code of a person.
 *
 * This class combines US and Canadian postal code implementations to provide
 * functionality for working with postal code fields. It recognizes "PostalCode",
 * "ZipCode", "ZIP3", "ZIP4", and "ZIP5" as valid aliases for this attribute type.
 *
 * The attribute performs normalization on input values, converting them to a
 * standard format. Supports both US ZIP codes (3, 4, or 5 digits) and Canadian
 * postal codes (3, 4, 5, or 6 characters in A1A 1A1 format). ZIP-3 codes (3 digits/characters)
 * are automatically padded to full length during normalization.
 *
 * This class instantiates postal code attributes with minLength=3 to support
 * partial postal codes (ZIP-3, ZIP-4, and partial Canadian formats).
 */
export class PostalCodeAttribute extends CombinedAttribute {
  private static readonly NAME = 'PostalCode';
  private static readonly ALIASES = ['PostalCode', 'ZipCode', 'ZIP3', 'ZIP4', 'ZIP5'];

  private implementations: SerializableAttribute[];

  constructor() {
    super(PostalCodeAttribute.NAME, PostalCodeAttribute.ALIASES, []);
    this.implementations = [new USPostalCodeAttribute(3), new CanadianPostalCodeAttribute(3)];
  }

  getName(): string {
    return PostalCodeAttribute.NAME;
  }

  getAliases(): string[] {
    return PostalCodeAttribute.ALIASES;
  }

  protected getAttributeImplementations(): SerializableAttribute[] {
    return this.implementations;
  }
}
