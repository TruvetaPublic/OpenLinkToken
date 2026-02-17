/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.processor;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.text.ParseException;
import java.util.List;
import java.util.Map;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWEObject;
import com.nimbusds.jose.crypto.DirectDecrypter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.truveta.opentoken.cli.io.TokenReader;
import com.truveta.opentoken.cli.io.TokenWriter;
import com.truveta.opentoken.tokens.Token;
import com.truveta.opentoken.tokentransformer.DecryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.MatchTokenConstants;

/**
 * Process encrypted tokens for decryption.
 * <p>
 * This class is used to read encrypted tokens from input source,
 * decrypt them, and write the decrypted tokens to the output data source.
 */
public final class TokenDecryptionProcessor {

    private static final Logger logger = LoggerFactory.getLogger(TokenDecryptionProcessor.class);

    private TokenDecryptionProcessor() {
    }

    /**
     * Reads encrypted tokens from the input data source, decrypts them, and
     * writes the result back to the output data source.
     * 
    * @param reader        TokenReader providing encrypted token rows
    * @param writer        TokenWriter for output
    * @param decryptor     The decryption transformer
    * @param encryptionKey Encryption key used for JWE token decryption
     * @throws IOException if an I/O error occurs
     */
    public static void process(TokenReader reader,
            TokenWriter writer,
            DecryptTokenTransformer decryptor,
            String encryptionKey) throws IOException {
        long rowCounter = 0;
        long decryptedCounter = 0;
        long errorCounter = 0;

        while (reader.hasNext()) {
            Map<String, String> row = reader.next();
            rowCounter++;

            String token = row.get(TokenConstants.TOKEN);

            // Decrypt the token if it's not blank
            if (token != null && !token.isEmpty() && !Token.BLANK.equals(token)) {
                try {
                    String decryptedToken = decryptToken(token, decryptor, encryptionKey);
                    row.put(TokenConstants.TOKEN, decryptedToken);
                    decryptedCounter++;
                } catch (Exception e) {
                    logger.error("Failed to decrypt token for RecordId {}, RuleId {}: {}",
                            row.get(TokenConstants.RECORD_ID), row.get(TokenConstants.RULE_ID), e.getMessage());
                    errorCounter++;
                    // Keep the encrypted token in case of error
                }
            }

            // Write token
            writer.writeToken(row);

            if (rowCounter % 10000 == 0) {
                logger.info(String.format("Processed \"%,d\" tokens", rowCounter));
            }
        }

        logger.info(String.format("Processed a total of %,d tokens", rowCounter));
        logger.info(String.format("Successfully decrypted %,d tokens", decryptedCounter));
        if (errorCounter > 0) {
            logger.warn(String.format("Failed to decrypt %,d tokens", errorCounter));
        }
    }

    private static String decryptToken(String token,
            DecryptTokenTransformer decryptor,
            String encryptionKey) throws Exception {
        if (token.startsWith(MatchTokenConstants.V1_TOKEN_PREFIX)) {
            return decryptV1Token(token, decryptor, encryptionKey);
        }
        return decryptor.transform(token);
    }

    private static String decryptV1Token(String token,
            DecryptTokenTransformer decryptor,
            String encryptionKey) throws ParseException, JOSEException {
        if (encryptionKey == null || encryptionKey.isBlank()) {
            throw new IllegalArgumentException("Encryption key is required for JWE token decryption");
        }

        String jweCompact = token.substring(MatchTokenConstants.V1_TOKEN_PREFIX.length());
        JWEObject jweObject = JWEObject.parse(jweCompact);
        DirectDecrypter decrypter = new DirectDecrypter(encryptionKey.getBytes(StandardCharsets.UTF_8));
        jweObject.decrypt(decrypter);

        Map<String, Object> payload = jweObject.getPayload().toJSONObject();
        Object ppidValue = null;
        if (payload != null) {
            Object ppid = payload.get(MatchTokenConstants.PAYLOAD_KEY_PPID);
            if (ppid instanceof List<?> list && !list.isEmpty()) {
                ppidValue = list.get(0);
            } else {
                ppidValue = ppid;
            }
        }

        if (ppidValue == null) {
            return null;
        }

        String ppidToken = ppidValue.toString();
        if (ppidToken.isBlank() || Token.BLANK.equals(ppidToken)) {
            return ppidToken;
        }

        try {
            return decryptor.transform(ppidToken);
        } catch (Exception e) {
            logger.debug("Failed to decrypt legacy token inside JWE payload", e);
            return ppidToken;
        }
    }
}
