/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../../attributes/AttributeExpression';
import { BirthDateAttribute } from '../../attributes/person/BirthDateAttribute';
import { FirstNameAttribute } from '../../attributes/person/FirstNameAttribute';
import { LastNameAttribute } from '../../attributes/person/LastNameAttribute';
import { SexAttribute } from '../../attributes/person/SexAttribute';
import { Token } from '../Token';

/**
 * Represents the token definition for token T1.
 *
 * It is a collection of attribute expressions that are concatenated together
 * to get the token signature. The token signature is as follows:
 * U(last-name)|U(first-name-1)|U(gender)|birth-date
 */
export class T1Token implements Token {
  private static readonly ID = 'T1';
  private definition: AttributeExpression[];

  constructor() {
    this.definition = [
      new AttributeExpression(LastNameAttribute as any, 'T|U'),
      new AttributeExpression(FirstNameAttribute as any, 'T|S(0,1)|U'),
      new AttributeExpression(SexAttribute as any, 'T|U'),
      new AttributeExpression(BirthDateAttribute as any, 'T|D'),
    ];
  }

  getIdentifier(): string {
    return T1Token.ID;
  }

  getDefinition(): AttributeExpression[] {
    return this.definition;
  }
}
