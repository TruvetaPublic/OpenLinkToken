/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { Attribute } from '../attributes/Attribute';
import { AttributeLoader } from '../attributes/AttributeLoader';
import { BaseTokenDefinition } from './BaseTokenDefinition';
import { Token } from './Token';
import { TokenGenerationException } from './TokenGenerationException';
import { TokenGeneratorResult } from './TokenGeneratorResult';
import { SHA256Tokenizer } from './tokenizer/SHA256Tokenizer';
import { TokenTransformer } from '../tokentransformer/TokenTransformer';

/**
 * Generates both the token signature and the token itself.
 */
export class TokenGenerator {
  private tokenizer: SHA256Tokenizer;
  private tokenTransformerList: TokenTransformer[];
  private tokenDefinition: BaseTokenDefinition;
  private attributeInstanceMap: Map<new () => Attribute, Attribute>;

  /**
   * Initializes the token generator.
   *
   * @param tokenDefinition - The token definition.
   * @param tokenTransformerList - A list of token transformers.
   */
  constructor(tokenDefinition: BaseTokenDefinition, tokenTransformerList: TokenTransformer[]) {
    this.tokenDefinition = tokenDefinition;
    this.tokenTransformerList = tokenTransformerList;
    this.attributeInstanceMap = new Map();
    
    AttributeLoader.load().forEach((attribute) => {
      this.attributeInstanceMap.set(attribute.constructor as new () => Attribute, attribute);
    });
    
    try {
      this.tokenizer = new SHA256Tokenizer(tokenTransformerList);
    } catch (e) {
      console.error('Error initializing tokenizer with hashing secret', e);
      throw e;
    }
  }

  /**
   * Get the token signature for a given token identifier. Populates the
   * invalidAttributes list in the result object with the attributes that are
   * invalid.
   *
   * @param tokenId - The token identifier.
   * @param personAttributes - The person attributes. It is a map of the person attributes.
   * @param result - The token generator result.
   * @returns the token signature using the token definition for the given token identifier.
   */
  protected getTokenSignature(
    tokenId: string,
    personAttributes: Map<new () => Attribute, string>,
    result: TokenGeneratorResult
  ): string | null {
    const definition = this.tokenDefinition.getTokenDefinition(tokenId);
    if (!personAttributes) {
      throw new Error('Person attributes cannot be null.');
    }

    const values: string[] = [];

    for (const attributeExpression of definition) {
      if (!personAttributes.has(attributeExpression.getAttributeClass())) {
        return null;
      }

      const attribute = this.attributeInstanceMap.get(attributeExpression.getAttributeClass());
      if (!attribute) {
        return null;
      }

      let attributeValue = personAttributes.get(attributeExpression.getAttributeClass());
      if (!attributeValue || !attribute.validate(attributeValue)) {
        result.getInvalidAttributes().add(attribute.getName());
        return null;
      }

      attributeValue = attribute.normalize(attributeValue);

      try {
        const effectiveValue = attributeExpression.getEffectiveValue(attributeValue);
        if (effectiveValue) {
          values.push(effectiveValue);
        }
      } catch (e) {
        console.error((e as Error).message);
        return null;
      }
    }

    return values.filter((s) => s != null && s.trim() !== '').join('|');
  }

  /**
   * Get the token signatures for all token/rule identifiers. This is mostly a
   * debug/logging/test method.
   *
   * @param personAttributes - The person attributes map.
   * @returns A map of token/rule identifier to the token signature.
   */
  getAllTokenSignatures(personAttributes: Map<new () => Attribute, string>): Map<string, string> {
    const signatures = new Map<string, string>();
    for (const tokenId of this.tokenDefinition.getTokenIdentifiers()) {
      try {
        const signature = this.getTokenSignature(tokenId, personAttributes, new TokenGeneratorResult());
        if (signature != null) {
          signatures.set(tokenId, signature);
        }
      } catch (e) {
        console.error(`Error generating token signature for token id: ${tokenId}`, e);
      }
    }
    return signatures;
  }

  /**
   * Get token for a given token identifier.
   *
   * @param tokenId - The token identifier.
   * @param personAttributes - The person attributes map.
   * @param result - The token generator result.
   * @returns the token using the token definition for the given token identifier.
   * @throws TokenGenerationException in case of failure to generate the token.
   */
  protected async getToken(
    tokenId: string,
    personAttributes: Map<new () => Attribute, string>,
    result: TokenGeneratorResult
  ): Promise<string | null> {
    const signature = this.getTokenSignature(tokenId, personAttributes, result);
    console.debug(`Token signature for token id ${tokenId}: ${signature}`);
    
    try {
      const token = await this.tokenizer.tokenize(signature);
      // Track blank tokens by rule
      if (token === Token.BLANK) {
        result.getBlankTokensByRule().add(tokenId);
      }
      return token;
    } catch (e) {
      console.error(`Error generating token for token id: ${tokenId}`, e);
      throw new TokenGenerationException('Error generating token', e as Error);
    }
  }

  /**
   * Get the tokens for all token/rule identifiers.
   *
   * @param personAttributes - The person attributes map.
   * @returns A {@link TokenGeneratorResult} object containing the tokens and invalid attributes.
   */
  async getAllTokens(personAttributes: Map<new () => Attribute, string>): Promise<TokenGeneratorResult> {
    const result = new TokenGeneratorResult();

    for (const tokenId of this.tokenDefinition.getTokenIdentifiers()) {
      try {
        const token = await this.getToken(tokenId, personAttributes, result);
        if (token != null) {
          result.getTokens().set(tokenId, token);
        }
      } catch (e) {
        console.error(`Error generating token for token id: ${tokenId}`, e);
      }
    }

    return result;
  }

  /**
   * Get invalid person attribute names.
   *
   * @param personAttributes - The person attributes map.
   * @returns A set of invalid person attribute names.
   */
  getInvalidPersonAttributes(personAttributes: Map<new () => Attribute, string>): Set<string> {
    const response = new Set<string>();

    for (const [attributeClass, value] of personAttributes.entries()) {
      const attribute = this.attributeInstanceMap.get(attributeClass);
      if (attribute && !attribute.validate(value)) {
        response.add(attribute.getName());
      }
    }

    return response;
  }

  getTokenizer(): SHA256Tokenizer {
    return this.tokenizer;
  }

  setTokenizer(tokenizer: SHA256Tokenizer): void {
    this.tokenizer = tokenizer;
  }

  getTokenTransformerList(): TokenTransformer[] {
    return this.tokenTransformerList;
  }

  setTokenTransformerList(tokenTransformerList: TokenTransformer[]): void {
    this.tokenTransformerList = tokenTransformerList;
  }

  getTokenDefinition(): BaseTokenDefinition {
    return this.tokenDefinition;
  }

  setTokenDefinition(tokenDefinition: BaseTokenDefinition): void {
    this.tokenDefinition = tokenDefinition;
  }

  getAttributeInstanceMap(): Map<new () => Attribute, Attribute> {
    return this.attributeInstanceMap;
  }

  setAttributeInstanceMap(attributeInstanceMap: Map<new () => Attribute, Attribute>): void {
    this.attributeInstanceMap = attributeInstanceMap;
  }
}
