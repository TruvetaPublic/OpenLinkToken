/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeExpression } from '../../attributes/AttributeExpression';
import { BirthDateAttribute } from '../../attributes/person/BirthDateAttribute';
import { SexAttribute } from '../../attributes/person/SexAttribute';
import { SocialSecurityNumberAttribute } from '../../attributes/person/SocialSecurityNumberAttribute';
import { Token } from '../Token';

/**
 * Represents the token definition for token T4.
 *
 * It is a collection of attribute expressions that are concatenated together
 * to get the token signature. The token signature is as follows:
 * social-security-number|U(gender)|birth-date
 */
export class T4Token implements Token {
  private static readonly ID = 'T4';
  private definition: AttributeExpression[];

  constructor() {
    this.definition = [
      new AttributeExpression(SocialSecurityNumberAttribute as any, 'T|M(\\d+)'),
      new AttributeExpression(SexAttribute as any, 'T|U'),
      new AttributeExpression(BirthDateAttribute as any, 'T|D'),
    ];
  }

  getIdentifier(): string {
    return T4Token.ID;
  }

  getDefinition(): AttributeExpression[] {
    return this.definition;
  }
}
