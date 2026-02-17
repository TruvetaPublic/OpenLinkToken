/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../../attributes/AttributeExpression';
import { FirstNameAttribute } from '../../attributes/person/FirstNameAttribute';
import { LastNameAttribute } from '../../attributes/person/LastNameAttribute';
import { SexAttribute } from '../../attributes/person/SexAttribute';
import { Token } from '../Token';

/**
 * Represents the token definition for token T5.
 *
 * It is a collection of attribute expressions that are concatenated together
 * to get the token signature. The token signature is as follows:
 * U(last-name)|U(first-name-3)|U(gender)
 */
export class T5Token implements Token {
  private static readonly ID = 'T5';
  private definition: AttributeExpression[];

  constructor() {
    this.definition = [
      new AttributeExpression(LastNameAttribute as any, 'T|U'),
      new AttributeExpression(FirstNameAttribute as any, 'T|S(0,3)|U'),
      new AttributeExpression(SexAttribute as any, 'T|U'),
    ];
  }

  getIdentifier(): string {
    return T5Token.ID;
  }

  getDefinition(): AttributeExpression[] {
    return this.definition;
  }
}
