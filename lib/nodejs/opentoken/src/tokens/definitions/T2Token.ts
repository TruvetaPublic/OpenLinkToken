/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../../attributes/AttributeExpression';
import { BirthDateAttribute } from '../../attributes/person/BirthDateAttribute';
import { FirstNameAttribute } from '../../attributes/person/FirstNameAttribute';
import { LastNameAttribute } from '../../attributes/person/LastNameAttribute';
import { PostalCodeAttribute } from '../../attributes/person/PostalCodeAttribute';
import { Token } from '../Token';

/**
 * Represents the token definition for token T2.
 *
 * It is a collection of attribute expressions that are concatenated together
 * to get the token signature. The token signature is as follows:
 * U(last-name)|U(first-name)|birth-date|postal-code-3
 */
export class T2Token implements Token {
  private static readonly ID = 'T2';
  private definition: AttributeExpression[];

  constructor() {
    this.definition = [
      new AttributeExpression(LastNameAttribute as any, 'T|U'),
      new AttributeExpression(FirstNameAttribute as any, 'T|U'),
      new AttributeExpression(BirthDateAttribute as any, 'T|D'),
      new AttributeExpression(PostalCodeAttribute as any, 'T|S(0,3)|U'),
    ];
  }

  getIdentifier(): string {
    return T2Token.ID;
  }

  getDefinition(): AttributeExpression[] {
    return this.definition;
  }
}
