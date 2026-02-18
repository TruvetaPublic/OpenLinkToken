/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.processor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.truveta.opentoken.cli.io.TokenReader;
import com.truveta.opentoken.cli.io.TokenWriter;
import com.truveta.opentoken.tokens.Token;
import com.truveta.opentoken.tokentransformer.DecryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.JweMatchTokenFormatter;

/**
 * Unit tests for {@link TokenDecryptionProcessor}.
 */
class TokenDecryptionProcessorTest {

    private static final String ENCRYPTION_KEY = "12345678901234567890123456789012";
    private static final String RING_ID = "ring-1";

    private TokenReader mockReader;
    private TokenWriter mockWriter;
    private DecryptTokenTransformer mockDecryptor;

    @BeforeEach
    void setUp() {
        mockReader = mock(TokenReader.class);
        mockWriter = mock(TokenWriter.class);
        mockDecryptor = mock(DecryptTokenTransformer.class);
    }

    @Test
    void testProcessDecryptsTokens() throws Exception {
        // Setup test data
        Map<String, String> row1 = new HashMap<>();
        row1.put(TokenConstants.RECORD_ID, "record-1");
        row1.put(TokenConstants.RULE_ID, "T1");
        row1.put(TokenConstants.TOKEN, "encryptedToken1");

        Map<String, String> row2 = new HashMap<>();
        row2.put(TokenConstants.RECORD_ID, "record-2");
        row2.put(TokenConstants.RULE_ID, "T2");
        row2.put(TokenConstants.TOKEN, "encryptedToken2");

        when(mockReader.hasNext()).thenReturn(true, true, false);
        when(mockReader.next()).thenReturn(row1, row2);
        when(mockDecryptor.transform("encryptedToken1")).thenReturn("decryptedToken1");
        when(mockDecryptor.transform("encryptedToken2")).thenReturn("decryptedToken2");

        // Execute
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify
        ArgumentCaptor<Map<String, String>> captor = ArgumentCaptor.forClass(Map.class);
        verify(mockWriter, times(2)).writeToken(captor.capture());

        assertEquals("decryptedToken1", captor.getAllValues().get(0).get(TokenConstants.TOKEN));
        assertEquals("decryptedToken2", captor.getAllValues().get(1).get(TokenConstants.TOKEN));
    }

    @Test
    void testProcessSkipsBlankTokens() throws Exception {
        // Setup test data with blank token
        Map<String, String> row = new HashMap<>();
        row.put(TokenConstants.RECORD_ID, "record-1");
        row.put(TokenConstants.RULE_ID, "T1");
        row.put(TokenConstants.TOKEN, Token.BLANK);

        when(mockReader.hasNext()).thenReturn(true, false);
        when(mockReader.next()).thenReturn(row);

        // Execute
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify decryptor was not called for blank token
        verify(mockDecryptor, times(0)).transform(Token.BLANK);

        // Verify token was still written
        verify(mockWriter, times(1)).writeToken(row);
    }

    @Test
    void testProcessSkipsEmptyTokens() throws Exception {
        // Setup test data with empty token
        Map<String, String> row = new HashMap<>();
        row.put(TokenConstants.RECORD_ID, "record-1");
        row.put(TokenConstants.RULE_ID, "T1");
        row.put(TokenConstants.TOKEN, "");

        when(mockReader.hasNext()).thenReturn(true, false);
        when(mockReader.next()).thenReturn(row);

        // Execute
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify decryptor was not called for empty token
        verify(mockDecryptor, times(0)).transform("");

        // Verify token was still written
        verify(mockWriter, times(1)).writeToken(row);
    }

    @Test
    void testProcessSkipsNullTokens() throws Exception {
        // Setup test data with null token
        Map<String, String> row = new HashMap<>();
        row.put(TokenConstants.RECORD_ID, "record-1");
        row.put(TokenConstants.RULE_ID, "T1");
        row.put(TokenConstants.TOKEN, null);

        when(mockReader.hasNext()).thenReturn(true, false);
        when(mockReader.next()).thenReturn(row);

        // Execute
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify token was still written with null
        verify(mockWriter, times(1)).writeToken(row);
    }

    @Test
    void testProcessHandlesDecryptionError() throws Exception {
        // Setup test data - use fresh map since the processor modifies it in place
        Map<String, String> row = new HashMap<>();
        row.put(TokenConstants.RECORD_ID, "record-1");
        row.put(TokenConstants.RULE_ID, "T1");
        row.put(TokenConstants.TOKEN, "invalidEncryptedToken");

        when(mockReader.hasNext()).thenReturn(true, false);
        when(mockReader.next()).thenReturn(row);
        when(mockDecryptor.transform("invalidEncryptedToken"))
                .thenThrow(new RuntimeException("Decryption failed"));

        // Execute - should not throw, should log error
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify token was still written (with original encrypted value since decryption failed)
        verify(mockWriter, times(1)).writeToken(row);
        // The row should still have the original encrypted token since decryption failed
        assertEquals("invalidEncryptedToken", row.get(TokenConstants.TOKEN));
    }

    @Test
    void testProcessMultipleTokensWithMixedContent() throws Exception {
        // Setup test data with mixed content
        Map<String, String> row1 = new HashMap<>();
        row1.put(TokenConstants.RECORD_ID, "record-1");
        row1.put(TokenConstants.RULE_ID, "T1");
        row1.put(TokenConstants.TOKEN, "encryptedToken1");

        Map<String, String> row2 = new HashMap<>();
        row2.put(TokenConstants.RECORD_ID, "record-1");
        row2.put(TokenConstants.RULE_ID, "T2");
        row2.put(TokenConstants.TOKEN, Token.BLANK);

        Map<String, String> row3 = new HashMap<>();
        row3.put(TokenConstants.RECORD_ID, "record-2");
        row3.put(TokenConstants.RULE_ID, "T1");
        row3.put(TokenConstants.TOKEN, "encryptedToken3");

        when(mockReader.hasNext()).thenReturn(true, true, true, false);
        when(mockReader.next()).thenReturn(row1, row2, row3);
        when(mockDecryptor.transform("encryptedToken1")).thenReturn("decryptedToken1");
        when(mockDecryptor.transform("encryptedToken3")).thenReturn("decryptedToken3");

        // Execute
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify all tokens were written
        verify(mockWriter, times(3)).writeToken(org.mockito.ArgumentMatchers.any());

        // Verify decryptor was only called for non-blank tokens
        verify(mockDecryptor, times(1)).transform("encryptedToken1");
        verify(mockDecryptor, times(1)).transform("encryptedToken3");
    }

    @Test
    void testProcessEmptyInput() throws Exception {
        when(mockReader.hasNext()).thenReturn(false);

        // Execute
        TokenDecryptionProcessor.process(mockReader, mockWriter, mockDecryptor, ENCRYPTION_KEY);

        // Verify no tokens were written
        verify(mockWriter, times(0)).writeToken(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void testProcessDecryptsJweTokens() throws Exception {
        String plainToken = "plain-token";
        EncryptTokenTransformer encryptor = new EncryptTokenTransformer(ENCRYPTION_KEY);
        DecryptTokenTransformer decryptor = new DecryptTokenTransformer(ENCRYPTION_KEY);
        JweMatchTokenFormatter formatter = new JweMatchTokenFormatter(ENCRYPTION_KEY, RING_ID, "T1", null);

        String encryptedToken = encryptor.transform(plainToken);
        String jweToken = formatter.transform(encryptedToken);

        Map<String, String> row = new HashMap<>();
        row.put(TokenConstants.RECORD_ID, "record-1");
        row.put(TokenConstants.RULE_ID, "T1");
        row.put(TokenConstants.TOKEN, jweToken);

        when(mockReader.hasNext()).thenReturn(true, false);
        when(mockReader.next()).thenReturn(row);

        TokenDecryptionProcessor.process(mockReader, mockWriter, decryptor, ENCRYPTION_KEY);

        ArgumentCaptor<Map<String, String>> captor = ArgumentCaptor.forClass(Map.class);
        verify(mockWriter, times(1)).writeToken(captor.capture());
        assertEquals(plainToken, captor.getValue().get(TokenConstants.TOKEN));
    }
}
