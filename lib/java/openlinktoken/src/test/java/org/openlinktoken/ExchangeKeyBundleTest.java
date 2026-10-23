/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Tests key-bundle generation, serialization, validation, and defensive copying.
 */
class ExchangeKeyBundleTest {

    /**
     * Verifies pure ML-KEM bundles generate and round-trip their public and private key material.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void generatesAndRoundTripsPureMlKemBundle() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");

        assertEquals(CryptoSuite.MLKEM768_SHA3_256, bundle.getSuite());
        assertEquals(1184, bundle.getMlkemPublicKey().length);
        assertEquals(64, bundle.getMlkemPrivateSeed().length);
        assertTrue(bundle.hasPrivateMaterial());

        Map<String, Object> publicMapping = bundle.toMapping();
        assertFalse(((Map<?, ?>) publicMapping.get("keys")).containsKey("ec"));
        assertFalse(((Map<?, ?>) ((Map<?, ?>) publicMapping.get("keys")).get("mlkem")).containsKey("privateKey"));

        ExchangeKeyBundle restored = ExchangeKeyBundle.fromJson(bundle.toJson(true), true);
        assertEquals(bundle.getKid(), restored.getKid());
        assertArrayEquals(bundle.getMlkemPublicKey(), restored.getMlkemPublicKey());
        assertArrayEquals(bundle.getMlkemPrivateSeed(), restored.getMlkemPrivateSeed());
    }

    /**
     * Verifies public-only bundles are rejected when private material is required.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsPublicOnlyBundleWhenPrivateMaterialIsRequired() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(bundle.toMapping(), true));
    }

    /**
     * Verifies tampered fingerprints and key identifiers are rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsTamperedPublicFingerprintAndKeyId() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        Map<String, Object> mapping = bundle.toMapping(true);
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        Map<String, Object> mlkem = (Map<String, Object>) keys.get("mlkem");

        mlkem.put("fingerprint", "00:".repeat(31) + "00");
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(mapping, true));

        Map<String, Object> validMapping = bundle.toMapping(true);
        validMapping.put("kid", "sha256:wrong");
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(validMapping, true));
    }

    /**
     * Verifies an ML-KEM private seed must derive the public key stored in its bundle.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsMismatchedMlKemPrivateSeed() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        ExchangeKeyBundle otherBundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        Map<String, Object> mapping = bundle.toMapping(true);
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        Map<String, Object> mlkem = (Map<String, Object>) keys.get("mlkem");
        Map<String, Object> otherKeys = (Map<String, Object>) otherBundle.toMapping(true).get("keys");
        Map<String, Object> otherMlkem = (Map<String, Object>) otherKeys.get("mlkem");
        mlkem.put("privateKey", otherMlkem.get("privateKey"));

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(mapping, true));
    }

    /**
     * Verifies version-one suites and malformed envelopes are rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsVersionOneSuiteAndMalformedEnvelope() {
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.generate("ecdh-sha256"));
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.generate("unknown-suite"));
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.generate((String) null));
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromJson("{\"version\":1}".getBytes(), false));
    }

    /**
     * Verifies trailing JSON tokens are rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsTrailingJsonTokens() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        byte[] serialized = bundle.toJson();
        byte[] withTrailingObject = new byte[serialized.length + 2];
        System.arraycopy(serialized, 0, withTrailingObject, 0, serialized.length);
        withTrailingObject[serialized.length] = '{';
        withTrailingObject[serialized.length + 1] = '}';

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromJson(withTrailingObject));
    }

    /**
     * Verifies invalid UTF-8 JSON bytes are rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsInvalidUtf8Json() {
        byte[] invalidUtf8 = new byte[] {
            '{', '"', 'x', '"', ':', '"', (byte) 0xC3, (byte) 0x28, '"', '}'
        };

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromJson(invalidUtf8));
    }

    /**
     * Verifies a pure ML-KEM bundle rejects an EC key section.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsEcSectionForPureMlKemBundle() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        Map<String, Object> mapping = bundle.toMapping();
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        keys.put("ec", Map.of("algorithm", "ECDH-P256"));

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(mapping));
    }

    /**
     * Verifies an orphan private-key encoding field is rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsOrphanPrivateEncodingField() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        Map<String, Object> mapping = bundle.toMapping();
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        Map<String, Object> mlkem = (Map<String, Object>) keys.get("mlkem");
        mlkem.put("privateKeyEncoding", "base64url");

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(mapping));
    }

    /**
     * Verifies key-material getters return defensive copies.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void returnsDefensiveCopiesOfKeyMaterial() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("mlkem768-sha3-256");
        byte[] publicKey = bundle.getMlkemPublicKey();
        byte[] original = publicKey.clone();

        publicKey[0] ^= 0x01;

        assertArrayEquals(original, bundle.getMlkemPublicKey());
        assertNotEquals(publicKey[0], bundle.getMlkemPublicKey()[0]);
    }
}
