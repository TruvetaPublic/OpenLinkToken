/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;

class EncryptionConstantsTest {

    @Test
    void testEncryptionConstantsExist() {
        assertNotNull(EncryptionConstants.AES);
        assertNotNull(EncryptionConstants.ENCRYPTION_ALGORITHM);
        assertNotNull(EncryptionConstants.IV_SIZE);
    }

    @Test
    void testEncryptionConstantsValues() {
        assertEquals("AES", EncryptionConstants.AES);
        assertEquals("AES/GCM/NoPadding", EncryptionConstants.ENCRYPTION_ALGORITHM);
        assertEquals(32, EncryptionConstants.KEY_BYTE_LENGTH);
        assertEquals(12, EncryptionConstants.IV_SIZE);
        assertEquals(128, EncryptionConstants.TAG_LENGTH_BITS);
    }
}
