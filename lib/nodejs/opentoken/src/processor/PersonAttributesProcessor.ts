/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { PersonAttributesReader } from '../io/PersonAttributesReader';
import { PersonAttributesWriter } from '../io/PersonAttributesWriter';
import { TokenTransformer } from '../tokentransformer/TokenTransformer';
import { AttributeLoader } from '../attributes/AttributeLoader';
import { Metadata } from '../Metadata';
import { TokenGenerator } from '../tokens/TokenGenerator';
import { TokenDefinition } from '../tokens/TokenDefinition';
import { Attribute } from '../attributes/Attribute';

/**
 * Process all person attributes.
 *
 * This class is used to read person attributes from input source,
 * generate tokens for each person record and write the tokens back
 * to the output data source.
 */
export class PersonAttributesProcessor {
  /**
   * Reads person attributes from the input data source, generates tokens,
   * and writes the result back to the output data source.
   */
  static async process(
    reader: PersonAttributesReader,
    writer: PersonAttributesWriter,
    transformers: TokenTransformer[],
    metadata: Metadata
  ): Promise<void> {
    const attributes = AttributeLoader.load();
    const tokenDefinition = new TokenDefinition();
    const tokenGenerator = new TokenGenerator(tokenDefinition, transformers);
    let rowCounter = 0;

    // Track invalid attributes and blank tokens
    const invalidAttributeCount = new Map<string, number>();
    const blankTokensByRuleCount = new Map<string, number>();

    while (await reader.hasNext()) {
      const row = await reader.next();
      rowCounter++;

      // Convert row data to person attributes map
      const personAttributes = new Map<new () => Attribute, string>();
      
      for (const attr of attributes) {
        const attrName = attr.getName();
        let value = row.get(attrName);

        // Also try aliases ONLY when value is truly absent (undefined/null), not when empty string
        if (value === undefined || value === null) {
          for (const alias of attr.getAliases()) {
            const aliasValue = row.get(alias);
            if (aliasValue !== undefined && aliasValue !== null) {
              value = aliasValue;
              break;
            }
          }
        }

        // Store even empty string values so that validators can properly flag them as invalid
        if (value !== undefined && value !== null) {
          personAttributes.set(attr.constructor as new () => Attribute, value);
        }
      }

      // Generate all tokens for this row
      const result = await tokenGenerator.getAllTokens(personAttributes);

      // Track invalid attributes
      if (result.getInvalidAttributes().size > 0) {
        for (const attrName of result.getInvalidAttributes()) {
          invalidAttributeCount.set(
            attrName,
            (invalidAttributeCount.get(attrName) || 0) + 1
          );
        }
      }

      // Track blank tokens
      if (result.getBlankTokensByRule().size > 0) {
        for (const ruleId of result.getBlankTokensByRule()) {
          blankTokensByRuleCount.set(
            ruleId,
            (blankTokensByRuleCount.get(ruleId) || 0) + 1
          );
        }
      }

      // Write tokens
      const recordId = row.get('RecordId') || row.get('record-id') || `row-${rowCounter}`;
      for (const [ruleId, token] of result.getTokens().entries()) {
        const outputRecord = new Map<string, string>();
        outputRecord.set('RecordId', recordId);
        outputRecord.set('RuleId', ruleId);
        outputRecord.set('Token', token);
        await writer.writeAttributes(outputRecord);
      }

      if (rowCounter % 1000 === 0) {
        console.log(`Processed ${rowCounter} records`);
      }
    }

    // Log invalid attribute statistics
    if (invalidAttributeCount.size > 0) {
      for (const [attrName, count] of invalidAttributeCount.entries()) {
        console.log(
          `Total invalid Attribute count for [${attrName}]: ${count.toLocaleString()}`
        );
      }
      const totalInvalid = Array.from(invalidAttributeCount.values()).reduce(
        (sum, count) => sum + count,
        0
      );
      console.log(
        `Total number of records with invalid attributes: ${totalInvalid.toLocaleString()}`
      );
    }

    // Log blank token statistics
    if (blankTokensByRuleCount.size > 0) {
      for (const [ruleId, count] of blankTokensByRuleCount.entries()) {
        console.log(
          `Total blank tokens for rule [${ruleId}]: ${count.toLocaleString()}`
        );
      }
      const totalBlankTokens = Array.from(
        blankTokensByRuleCount.values()
      ).reduce((sum, count) => sum + count, 0);
      console.log(
        `Total blank tokens generated: ${totalBlankTokens.toLocaleString()}`
      );
    }

    metadata.totalRows = rowCounter;
    console.log(`Processed a total of ${rowCounter} records`);
  }
}
