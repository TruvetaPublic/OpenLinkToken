/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { Attribute } from './Attribute';
import { FirstNameAttribute } from './person/FirstNameAttribute';
import { LastNameAttribute } from './person/LastNameAttribute';
import { BirthDateAttribute } from './person/BirthDateAttribute';
import { BirthYearAttribute } from './person/BirthYearAttribute';
import { AgeAttribute } from './person/AgeAttribute';
import { SexAttribute } from './person/SexAttribute';
import { SocialSecurityNumberAttribute } from './person/SocialSecurityNumberAttribute';
import { PostalCodeAttribute } from './person/PostalCodeAttribute';
import { RecordIdAttribute } from './general/RecordIdAttribute';
import { StringAttribute } from './general/StringAttribute';
import { DateAttribute } from './general/DateAttribute';
import { YearAttribute } from './general/YearAttribute';

/**
 * Loader for all available attributes in the system.
 *
 * In Java, this uses ServiceLoader pattern. In Node.js/TypeScript,
 * we explicitly register attributes here.
 */
export class AttributeLoader {
  private constructor() {
    // Private constructor to prevent instantiation
  }

  /**
   * Load all available attributes.
   *
   * @returns A Set of all available attribute instances.
   */
  static load(): Set<Attribute> {
    const attributes = new Set<Attribute>();

    // Register all attribute implementations
    attributes.add(new FirstNameAttribute());
    attributes.add(new LastNameAttribute());
    attributes.add(new BirthDateAttribute());
    attributes.add(new BirthYearAttribute());
    attributes.add(new AgeAttribute());
    attributes.add(new SexAttribute());
    attributes.add(new SocialSecurityNumberAttribute());
    attributes.add(new PostalCodeAttribute());
    attributes.add(new RecordIdAttribute());

    // Generic attributes (usually not used directly in token generation)
    attributes.add(new StringAttribute('String', ['String']));
    attributes.add(new DateAttribute('Date', ['Date']));
    attributes.add(new YearAttribute());

    return attributes;
  }

  /**
   * Find an attribute by name or alias.
   *
   * @param nameOrAlias - The name or alias to search for.
   * @returns The matching attribute or undefined if not found.
   */
  static findByName(nameOrAlias: string): Attribute | undefined {
    const attributes = this.load();

    for (const attr of attributes) {
      if (attr.getName() === nameOrAlias || attr.getAliases().includes(nameOrAlias)) {
        return attr;
      }
    }

    return undefined;
  }
}
