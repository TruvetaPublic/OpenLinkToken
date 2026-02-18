/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.processor;

import java.io.IOException;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.cli.io.TokenReader;
import com.truveta.opentoken.cli.io.TokenWriter;
import com.truveta.opentoken.tokens.Token;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

/**
 * Unified processor for token transformations (encryption/decryption).
 * <p>
 * This class provides a generic token transformation pipeline that can handle
 * both encryption and decryption operations using the provided TokenTransformer.
 */
public final class TokenTransformationProcessor {

    private static final Logger logger = LoggerFactory.getLogger(TokenTransformationProcessor.class);

    private TokenTransformationProcessor() {
    }

    /**
     * Reads tokens from the input data source, transforms them using the provided
     * transformer, and writes the result to the output data source.
     * 
     * @param reader      TokenReader providing input token rows
     * @param writer      TokenWriter for output
     * @param transformer The token transformer (encryption or decryption)
     * @param operation   The operation name for logging (e.g., "encrypted", "decrypted")
     * @throws IOException if an I/O error occurs
     */
    public static void process(TokenReader reader,
                                TokenWriter writer,
                                TokenTransformer transformer,
                                String operation) throws IOException {
        long rowCounter = 0;
        long transformedCounter = 0;
        long errorCounter = 0;

        while (reader.hasNext()) {
            Map<String, String> row = reader.next();
            rowCounter++;
            
            String token = row.get(TokenConstants.TOKEN);
            
            // Transform the token if it's not blank
            if (token != null && !token.isEmpty() && !Token.BLANK.equals(token)) {
                try {
                    String transformedToken = transformer.transform(token);
                    row.put(TokenConstants.TOKEN, transformedToken);
                    transformedCounter++;
                } catch (Exception e) {
                    logger.error("Failed to {} token for RecordId {}, RuleId {}: {}", 
                               operation, row.get(TokenConstants.RECORD_ID), 
                               row.get(TokenConstants.RULE_ID), e.getMessage());
                    errorCounter++;
                    // Keep the original token in case of error
                }
            }
            
            // Write token
            writer.writeToken(row);

            if (rowCounter % 10000 == 0) {
                logger.info(String.format("Processed \"%,d\" tokens", rowCounter));
            }
        }

        logger.info(String.format("Processed a total of %,d tokens", rowCounter));
        logger.info(String.format("Successfully %s %,d tokens", operation, transformedCounter));
        if (errorCounter > 0) {
            logger.warn(String.format("Failed to %s %,d tokens", operation, errorCounter));
        }
    }
}
