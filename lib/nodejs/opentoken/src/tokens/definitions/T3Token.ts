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
 * Represents the token definition for token T3.
 *
 * It is a collection of attribute expressions that are concatenated together
 * to get the token signature. The token signature is as follows:
 * U(last-name)|U(first-name)|U(gender)|birth-date
 */
export class T3Token implements Token {
  private static readonly ID = 'T3';
  private definition: AttributeExpression[];

  constructor() {
    this.definition = [
      new AttributeExpression(LastNameAttribute as any, 'T|U'),
      new AttributeExpression(FirstNameAttribute as any, 'T|U'),
      new AttributeExpression(SexAttribute as any, 'T|U'),
      new AttributeExpression(BirthDateAttribute as any, 'T|D'),
    ];
  }

  getIdentifier(): string {
    return T3Token.ID;
  }

  getDefinition(): AttributeExpression[] {
    return this.definition;
  }
}
