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
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");

        assertEquals(CryptoSuite.SUITE_PQ_V1, bundle.getSuite());
        assertEquals(1184, bundle.getMlkemPublicKey().length);
        assertEquals(64, bundle.getMlkemPrivateSeed().length);
        assertFalse(bundle.hasEcKey());
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
     * Verifies hybrid bundles include P-256 material alongside ML-KEM keys.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void generatesHybridBundleWithP256Material() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-hybrid-v1");

        assertEquals(CryptoSuite.SUITE_PQ_HYBRID_V1, bundle.getSuite());
        assertTrue(bundle.hasEcKey());
        assertTrue(bundle.hasPrivateMaterial());
        assertEquals(1184, bundle.getMlkemPublicKey().length);
        assertEquals(64, bundle.getMlkemPrivateSeed().length);
        assertTrue(new String(bundle.getEcPublicPem()).contains("BEGIN PUBLIC KEY"));
        assertTrue(new String(bundle.getEcPrivatePem()).contains("BEGIN PRIVATE KEY"));
    }

    /**
     * Verifies public-only bundles are rejected when private material is required.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsPublicOnlyBundleWhenPrivateMaterialIsRequired() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");

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
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");
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
     * Verifies version-one suites and malformed envelopes are rejected.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void rejectsVersionOneSuiteAndMalformedEnvelope() {
        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.generate("suite-sha256-v1"));
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
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");
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
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> mapping = bundle.toMapping();
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        keys.put("ec", Map.of("algorithm", ExchangeKeyBundle.EC_ALGORITHM));

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
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");
        Map<String, Object> mapping = bundle.toMapping();
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        Map<String, Object> mlkem = (Map<String, Object>) keys.get("mlkem");
        mlkem.put("privateKeyEncoding", "base64url");

        assertThrows(
                ExchangeKeyBundle.KeyBundleException.class,
                () -> ExchangeKeyBundle.fromMapping(mapping));
    }

    /**
     * Verifies equivalent EC PEM line endings preserve the key identifier.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void acceptsEquivalentEcPemFormatting() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-hybrid-v1");
        Map<String, Object> mapping = bundle.toMapping(true);
        Map<String, Object> keys = (Map<String, Object>) mapping.get("keys");
        Map<String, Object> ec = (Map<String, Object>) keys.get("ec");
        String publicPem = (String) ec.get("publicKey");
        ec.put("publicKey", publicPem.replace("\n", "\r\n"));

        ExchangeKeyBundle restored = ExchangeKeyBundle.fromMapping(mapping, true);

        assertEquals(bundle.getKid(), restored.getKid());
    }

    /**
     * Verifies key-material getters return defensive copies.
     *
     * <p>This test method accepts no arguments and returns no value.</p>
     */
    @Test
    void returnsDefensiveCopiesOfKeyMaterial() {
        ExchangeKeyBundle bundle = ExchangeKeyBundle.generate("suite-pq-v1");
        byte[] publicKey = bundle.getMlkemPublicKey();
        byte[] original = publicKey.clone();

        publicKey[0] ^= 0x01;

        assertArrayEquals(original, bundle.getMlkemPublicKey());
        assertNotEquals(publicKey[0], bundle.getMlkemPublicKey()[0]);
    }
}
