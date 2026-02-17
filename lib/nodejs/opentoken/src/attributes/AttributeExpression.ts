/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * An attribute expression determines how the value of an attribute is normalized for consumption.
 *
 * Components used to compose the attribute expression:
 * - T - trim
 * - U - convert to upper case
 * - S(start_index, end_index) - substring of value
 * - D - treat as date
 * - M(regex) - match the regular expression
 * - | - expression separator
 *
 * Examples:
 * - T|S(0,3)|U - trim the value, then take first 3 characters, and then convert to upper case
 * - T|D - trim the value, treat the value as a date in the yyyy-MM-dd format
 * - T|M("\\d+") - trim the value, then make sure that the value matches the regular expression
 */
export class AttributeExpression {
  private static readonly EXPRESSION_PATTERN = /\s*(?<expr>[^ (]+)(?:\((?<args>[^)]+)\))?/;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private attributeClass: any;
  private expressions: string;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(attributeClass: any, expressions: string) {
    this.attributeClass = attributeClass;
    this.expressions = expressions;
  }

  /**
   * Get the effective value for an attribute after application of the attribute expression.
   *
   * @param value - The attribute value
   * @returns The effective value after applying the attribute expression
   */
  getEffectiveValue(value: string): string {
    if (!value || value.trim().length === 0) {
      return '';
    }

    if (!this.expressions || this.expressions.trim().length === 0) {
      return value;
    }

    let result = value;
    const expressionParts = this.expressions.split('|');
    for (const expression of expressionParts) {
      result = this.eval(result, expression);
    }
    return result;
  }

  private eval(value: string, expression: string): string {
    if (!value || !expression) {
      throw new Error(`Unable to evaluate expression [${expression}] over value [${value}]`);
    }

    const match = expression.match(AttributeExpression.EXPRESSION_PATTERN);
    if (!match || !match.groups) {
      throw new Error(`Unable to evaluate expression [${expression}] over value [${value}]`);
    }

    const expr = match.groups['expr'];
    const argsString = match.groups['args'];
    const args = argsString ? argsString.trim().split(',') : null;

    const exprChar = expr.charAt(0).toUpperCase();

    switch (exprChar) {
      case 'U':
        return value.toUpperCase();
      case 'T':
        return value.trim();
      case 'S':
        if (!args) {
          throw new Error(`Expression S requires arguments: ${expression}`);
        }
        return this.substringExpression(value, expression, args);
      case 'R':
        if (!args) {
          throw new Error(`Expression R requires arguments: ${expression}`);
        }
        return this.replaceExpression(value, expression, args);
      case 'M':
        if (!args) {
          throw new Error(`Expression M requires arguments: ${expression}`);
        }
        return this.matchExpression(value, expression, args);
      case 'D':
        return this.dateExpression(value, expression);
      default:
        throw new Error(`Unknown expression: ${expression}`);
    }
  }

  /**
   * Substring expression S(start,end)
   */
  private substringExpression(value: string, expression: string, args: string[]): string {
    if (args.length !== 2) {
      throw new Error(`Expression S requires exactly 2 arguments: ${expression}`);
    }

    try {
      const start = Math.max(0, parseInt(args[0]));
      const end = Math.min(value.length, parseInt(args[1]));
      return value.substring(start, end);
    } catch (ex) {
      throw new Error(`Unable to evaluate expression [${expression}] over value [${value}]`);
    }
  }

  /**
   * Replace expression R(oldString,newString)
   */
  private replaceExpression(value: string, expression: string, args: string[]): string {
    if (args.length !== 2) {
      throw new Error(`Expression R requires exactly 2 arguments: ${expression}`);
    }

    try {
      const oldVal = args[0].substring(1, args[0].length - 1);
      const newVal = args[1].substring(1, args[1].length - 1);
      return value.replace(new RegExp(oldVal, 'g'), newVal);
    } catch (ex) {
      throw new Error(`Unable to evaluate expression [${expression}] over value [${value}]`);
    }
  }

  /**
   * RegEx match M(regex)
   */
  private matchExpression(value: string, expression: string, args: string[]): string {
    if (args.length !== 1) {
      throw new Error(`Expression M requires exactly 1 argument: ${expression}`);
    }

    try {
      const pattern = new RegExp(args[0], 'g');
      const matches = value.match(pattern);
      return matches ? matches.join('') : '';
    } catch (ex) {
      throw new Error(`Unable to evaluate expression [${expression}] over value [${value}]`);
    }
  }

  /**
   * Date expression - returns date in yyyy-MM-dd format
   */
  private dateExpression(value: string, _expression: string): string {
    // For dates, we expect them to already be normalized
    // This is a placeholder - full implementation would parse various date formats
    return value.trim();
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getAttributeClass(): any {
    return this.attributeClass;
  }

  getExpressions(): string {
    return this.expressions;
  }
}
