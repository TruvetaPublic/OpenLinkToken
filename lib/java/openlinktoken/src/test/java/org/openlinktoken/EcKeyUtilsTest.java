/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;

import org.junit.jupiter.api.Test;

class EcKeyUtilsTest {

    @Test
    void generatesAndSerializesSupportedCurves() {
        for (String[] curve : new String[][] {{"P-256", "256"}, {"P-384", "384"}, {"P-521", "521"}}) {
            KeyPair keyPair = EcKeyUtils.generateKeyPair(curve[0]);

            assertEquals("EC", keyPair.getPrivate().getAlgorithm());
            assertEquals("EC", keyPair.getPublic().getAlgorithm());
            assertEquals(
                    Integer.parseInt(curve[1]),
                    ((ECPrivateKey) keyPair.getPrivate()).getParams().getCurve().getField().getFieldSize());
            assertEquals(
                    Integer.parseInt(curve[1]),
                    ((ECPublicKey) keyPair.getPublic()).getParams().getCurve().getField().getFieldSize());

            byte[] privatePem = EcKeyUtils.privateKeyToPem(keyPair.getPrivate());
            byte[] publicPem = EcKeyUtils.publicKeyToPem(keyPair.getPublic());

            assertEquals("EC", EcKeyUtils.privateKeyFromPem(privatePem).getAlgorithm());
            assertEquals("EC", EcKeyUtils.publicKeyFromPem(publicPem).getAlgorithm());
        }
    }

    @Test
    void derivesPublicKeyAndStablePortableKidFromPrivatePem() {
        KeyPair keyPair = EcKeyUtils.generateKeyPair("P-256");
        byte[] publicPem = EcKeyUtils.publicKeyToPem(keyPair.getPublic());
        byte[] derivedPublicPem = EcKeyUtils.derivePublicKeyFromPrivatePem(
                EcKeyUtils.privateKeyToPem(keyPair.getPrivate()));

        assertArrayEquals(publicPem, derivedPublicPem);

        String fingerprint = EcKeyUtils.publicKeyFingerprint(publicPem);
        assertEquals(95, fingerprint.length());
        assertEquals(31, fingerprint.chars().filter(character -> character == ':').count());
        assertEquals("sha256:" + fingerprint.toLowerCase().replace(':', '-'), EcKeyUtils.fingerprintToKid(fingerprint));
    }

    @Test
    void roundTripsPrivateAndPublicKeysThroughDer() {
        KeyPair keyPair = EcKeyUtils.generateKeyPair("P-384");

        assertEquals(
                EcKeyUtils.privateKeyFromDer(EcKeyUtils.privateKeyToDer(keyPair.getPrivate())),
                EcKeyUtils.privateKeyFromPem(EcKeyUtils.privateKeyToPem(keyPair.getPrivate())));
        assertEquals(
                EcKeyUtils.publicKeyFromDer(EcKeyUtils.publicKeyToDer(keyPair.getPublic())),
                EcKeyUtils.publicKeyFromPem(EcKeyUtils.publicKeyToPem(keyPair.getPublic())));
    }

    @Test
    void rejectsUnsupportedCurvesAndMalformedPem() {
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.generateKeyPair("P-255"));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.privateKeyFromPem("not PEM".getBytes()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.fingerprintToKid(" "));
    }

    @Test
    void rejectsNonEcKeysAndMalformedDer() throws GeneralSecurityException {
        KeyPair rsa = KeyPairGenerator.getInstance("RSA").generateKeyPair();

        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.privateKeyToDer(rsa.getPrivate()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.publicKeyToDer(rsa.getPublic()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.curveName(rsa.getPrivate()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.curveName(rsa.getPublic()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.publicKeyFingerprint(rsa.getPublic()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.privateKeyFromDer(new byte[0]));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.publicKeyFromDer(new byte[0]));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.privateKeyFromDer(rsa.getPrivate().getEncoded()));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.publicKeyFromDer(rsa.getPublic().getEncoded()));
    }

    /**
     * Verifies null, empty, and malformed PEM inputs and null fingerprints are rejected.
     */
    @Test
    void rejectsMalformedPemAndNullFingerprint() {
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.privateKeyFromPem(null));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.publicKeyFromPem(new byte[0]));
        assertThrows(
                IllegalArgumentException.class,
                () -> EcKeyUtils.privateKeyFromPem(
                        "-----BEGIN PRIVATE KEY-----\n\n-----END PRIVATE KEY-----"
                                .getBytes(StandardCharsets.US_ASCII)));
        assertThrows(
                IllegalArgumentException.class,
                () -> EcKeyUtils.publicKeyFromPem(
                        "-----BEGIN PUBLIC KEY-----\n%%%\n-----END PUBLIC KEY-----"
                                .getBytes(StandardCharsets.US_ASCII)));
        assertThrows(IllegalArgumentException.class, () -> EcKeyUtils.fingerprintToKid(null));
    }

    /**
     * Verifies mutating private PEM input after derivation does not change the derived public PEM output.
     */
    @Test
    void doesNotExposeMutablePemInputThroughDerivedOutput() {
        KeyPair keyPair = EcKeyUtils.generateKeyPair("P-256");
        byte[] privatePem = EcKeyUtils.privateKeyToPem(keyPair.getPrivate());
        byte[] derivedPublicPem = EcKeyUtils.derivePublicKeyFromPrivatePem(privatePem);

        privatePem[0] = 'X';

        assertNotEquals('X', derivedPublicPem[0]);
    }
}
