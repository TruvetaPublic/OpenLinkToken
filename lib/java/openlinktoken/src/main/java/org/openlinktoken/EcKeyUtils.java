/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.ECFieldFp;
import java.security.spec.ECParameterSpec;
import java.security.spec.ECPoint;
import java.security.spec.ECPublicKeySpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import org.bouncycastle.jce.ECNamedCurveTable;
import org.bouncycastle.jce.spec.ECNamedCurveParameterSpec;

/**
 * In-memory EC key utilities used by exchange key bundles.
 *
 * <p>This class deliberately does not perform filesystem or environment operations. It
 * supports the named curves and key encodings required by the exchange bundle format.
 */
public final class EcKeyUtils implements Serializable {
    private static final long serialVersionUID = 1L;

    /** Curves supported by the exchange format. */
    public static final List<String> SUPPORTED_CURVES = List.of("P-256", "P-384", "P-521");

    private static final Map<String, String> JCA_CURVE_NAMES = Map.of(
            "P-256", "secp256r1",
            "P-384", "secp384r1",
            "P-521", "secp521r1");

    private EcKeyUtils() {
    }

    /**
     * Returns the JCA parameter specification for an Open Link Token curve name.
     *
     * @param curve the Open Link Token curve name
     * @return the named-curve specification
     */
    public static ECGenParameterSpec getCurveSpec(String curve) {
        String jcaName = JCA_CURVE_NAMES.get(curve);
        if (jcaName == null) {
            throw new IllegalArgumentException(
                    "Unsupported curve '" + curve + "'. Valid options are: " + String.join(", ", SUPPORTED_CURVES));
        }
        return new ECGenParameterSpec(jcaName);
    }

    /**
     * Generates an EC key pair for a supported named curve.
     *
     * @param curve the Open Link Token curve name
     * @return the generated key pair
     */
    public static KeyPair generateKeyPair(String curve) {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("EC");
            generator.initialize(getCurveSpec(curve));
            return generator.generateKeyPair();
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("Unable to generate an EC key pair for curve '" + curve + "'.", exception);
        }
    }

    /**
     * Encodes an EC private key as unencrypted PKCS#8 PEM.
     *
     * @param privateKey the EC private key
     * @return a defensive PEM byte array
     */
    public static byte[] privateKeyToPem(PrivateKey privateKey) {
        return encodePem(privateKeyToDer(privateKey), "PRIVATE KEY");
    }

    /**
     * Encodes an EC public key as SubjectPublicKeyInfo PEM.
     *
     * @param publicKey the EC public key
     * @return a defensive PEM byte array
     */
    public static byte[] publicKeyToPem(PublicKey publicKey) {
        return encodePem(publicKeyToDer(publicKey), "PUBLIC KEY");
    }

    /**
     * Returns a defensive copy of an EC private key's PKCS#8 DER encoding.
     *
     * @param privateKey the EC private key
     * @return PKCS#8 DER bytes
     */
    public static byte[] privateKeyToDer(PrivateKey privateKey) {
        if (!(privateKey instanceof ECPrivateKey)) {
            throw new IllegalArgumentException("Key must be an EC private key.");
        }
        byte[] encoded = privateKey.getEncoded();
        return Arrays.copyOf(encoded, encoded.length);
    }

    /**
     * Returns a defensive copy of an EC public key's SubjectPublicKeyInfo DER encoding.
     *
     * @param publicKey the EC public key
     * @return SubjectPublicKeyInfo DER bytes
     */
    public static byte[] publicKeyToDer(PublicKey publicKey) {
        if (!(publicKey instanceof ECPublicKey)) {
            throw new IllegalArgumentException("Key must be an EC public key.");
        }
        byte[] encoded = publicKey.getEncoded();
        return Arrays.copyOf(encoded, encoded.length);
    }

    /**
     * Parses an unencrypted PKCS#8 EC private key PEM.
     *
     * @param privatePem the PEM bytes
     * @return the parsed EC private key
     */
    public static ECPrivateKey privateKeyFromPem(byte[] privatePem) {
        return privateKeyFromDer(decodePem(privatePem, "PRIVATE KEY"));
    }

    /**
     * Parses an unencrypted PKCS#8 EC private key DER encoding.
     *
     * @param privateDer the DER bytes
     * @return the parsed EC private key
     */
    public static ECPrivateKey privateKeyFromDer(byte[] privateDer) {
        try {
            PrivateKey privateKey = KeyFactory.getInstance("EC")
                    .generatePrivate(new PKCS8EncodedKeySpec(copyDer(privateDer, "EC private key")));
            if (!(privateKey instanceof ECPrivateKey)) {
                throw new IllegalArgumentException("Key must be an EC private key.");
            }
            return (ECPrivateKey) privateKey;
        } catch (GeneralSecurityException | ClassCastException exception) {
            throw new IllegalArgumentException("Invalid EC private key PEM.", exception);
        }
    }

    /**
     * Parses an EC SubjectPublicKeyInfo PEM.
     *
     * @param publicPem the PEM bytes
     * @return the parsed EC public key
     */
    public static ECPublicKey publicKeyFromPem(byte[] publicPem) {
        return publicKeyFromDer(decodePem(publicPem, "PUBLIC KEY"));
    }

    /**
     * Parses an EC SubjectPublicKeyInfo DER encoding.
     *
     * @param publicDer the DER bytes
     * @return the parsed EC public key
     */
    public static ECPublicKey publicKeyFromDer(byte[] publicDer) {
        try {
            PublicKey publicKey = KeyFactory.getInstance("EC")
                    .generatePublic(new X509EncodedKeySpec(copyDer(publicDer, "EC public key")));
            if (!(publicKey instanceof ECPublicKey)) {
                throw new IllegalArgumentException("Key must be an EC public key.");
            }
            return (ECPublicKey) publicKey;
        } catch (GeneralSecurityException | ClassCastException exception) {
            throw new IllegalArgumentException("Invalid EC public key PEM.", exception);
        }
    }

    /**
     * Derives the public key corresponding to an EC private key PEM.
     *
     * @param privatePem the private key PEM bytes
     * @return the derived SubjectPublicKeyInfo public key PEM
     */
    public static byte[] derivePublicKeyFromPrivatePem(byte[] privatePem) {
        PrivateKey parsed = privateKeyFromPem(privatePem);
        if (!(parsed instanceof ECPrivateKey privateKey)) {
            throw new IllegalArgumentException("Key must be an EC private key.");
        }
        return publicKeyToPem(derivePublicKey(privateKey));
    }

    /**
     * Returns the Open Link Token curve name for an EC private key.
     *
     * @param privateKey the EC private key
     * @return the Open Link Token curve name
     */
    public static String curveName(PrivateKey privateKey) {
        if (!(privateKey instanceof ECPrivateKey ecPrivateKey)) {
            throw new IllegalArgumentException("Key must be an EC private key.");
        }
        return curveName(ecPrivateKey.getParams());
    }

    /**
     * Returns the Open Link Token curve name for an EC public key.
     *
     * @param publicKey the EC public key
     * @return the Open Link Token curve name
     */
    public static String curveName(PublicKey publicKey) {
        if (!(publicKey instanceof ECPublicKey ecPublicKey)) {
            throw new IllegalArgumentException("Key must be an EC public key.");
        }
        return curveName(ecPublicKey.getParams());
    }

    /**
     * Computes the SHA-256 fingerprint of an EC SubjectPublicKeyInfo PEM.
     *
     * @param publicPem the public key PEM bytes
     * @return an uppercase, colon-delimited fingerprint
     */
    public static String publicKeyFingerprint(byte[] publicPem) {
        return publicKeyFingerprint(publicKeyFromPem(publicPem));
    }

    /**
     * Computes the SHA-256 fingerprint of an EC public key.
     *
     * @param publicKey the public key
     * @return an uppercase, colon-delimited fingerprint
     */
    public static String publicKeyFingerprint(PublicKey publicKey) {
        if (!(publicKey instanceof ECPublicKey)) {
            throw new IllegalArgumentException("Key must be an EC public key.");
        }
        return fingerprint(publicKey.getEncoded());
    }

    /**
     * Converts a display fingerprint into the portable JWE key identifier.
     *
     * @param fingerprint the display fingerprint
     * @return the normalized key identifier
     */
    public static String fingerprintToKid(String fingerprint) {
        if (fingerprint == null || fingerprint.isBlank()) {
            throw new IllegalArgumentException("Fingerprint must not be empty.");
        }
        return "sha256:" + fingerprint.trim().toLowerCase(Locale.ROOT).replace(':', '-');
    }

    /**
     * Encodes DER key bytes in a PEM envelope.
     *
     * @param value DER-encoded key bytes
     * @param type PEM label to place in the envelope
     * @return ASCII-encoded PEM bytes
     */
    private static byte[] encodePem(byte[] value, String type) {
        String encoded = Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.US_ASCII)).encodeToString(value);
        String pem = "-----BEGIN " + type + "-----\n"
                + encoded
                + "\n-----END " + type + "-----\n";
        return pem.getBytes(StandardCharsets.US_ASCII);
    }

    /**
     * Decodes PEM bytes with the expected key type label.
     *
     * @param pem ASCII-encoded PEM bytes
     * @param type expected PEM label
     * @return decoded DER key bytes
     * @throws IllegalArgumentException if the PEM is empty, malformed, or contains invalid base64
     */
    private static byte[] decodePem(byte[] pem, String type) {
        if (pem == null || pem.length == 0) {
            throw new IllegalArgumentException(type + " PEM must not be empty.");
        }
        String value = new String(pem, StandardCharsets.US_ASCII).trim();
        String header = "-----BEGIN " + type + "-----";
        String footer = "-----END " + type + "-----";
        if (!value.startsWith(header) || !value.endsWith(footer)) {
            throw new IllegalArgumentException("Invalid " + type + " PEM.");
        }
        String body = value.substring(header.length(), value.length() - footer.length()).replaceAll("\\s", "");
        if (body.isEmpty()) {
            throw new IllegalArgumentException("Invalid " + type + " PEM.");
        }
        try {
            return Base64.getDecoder().decode(body);
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException("Invalid " + type + " PEM.", exception);
        }
    }

    /**
     * Computes a SHA-256 fingerprint for encoded key material.
     *
     * @param value encoded key bytes
     * @return uppercase, colon-delimited SHA-256 fingerprint
     */
    private static String fingerprint(byte[] value) {
        byte[] digest;
        try {
            digest = MessageDigest.getInstance("SHA-256").digest(value);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available.", exception);
        }

        StringBuilder result = new StringBuilder(digest.length * 3 - 1);
        for (int index = 0; index < digest.length; index++) {
            if (index > 0) {
                result.append(':');
            }
            result.append(String.format("%02X", digest[index] & 0xFF));
        }
        return result.toString();
    }

    private static PublicKey derivePublicKey(ECPrivateKey privateKey) {
        String curve = curveName(privateKey);
        ECNamedCurveParameterSpec namedSpec = ECNamedCurveTable.getParameterSpec(JCA_CURVE_NAMES.get(curve));
        var point = namedSpec.getG().multiply(privateKey.getS()).normalize();
        ECPoint publicPoint = new ECPoint(
                point.getAffineXCoord().toBigInteger(),
                point.getAffineYCoord().toBigInteger());
        try {
            return KeyFactory.getInstance("EC")
                    .generatePublic(new ECPublicKeySpec(publicPoint, privateKey.getParams()));
        } catch (GeneralSecurityException exception) {
            throw new IllegalArgumentException("Unable to derive an EC public key.", exception);
        }
    }

    private static byte[] copyDer(byte[] value, String keyName) {
        if (value == null || value.length == 0) {
            throw new IllegalArgumentException(keyName + " DER must not be empty.");
        }
        return Arrays.copyOf(value, value.length);
    }

    private static String curveName(ECParameterSpec parameters) {
        for (String curve : SUPPORTED_CURVES) {
            ECNamedCurveParameterSpec namedSpec = ECNamedCurveTable.getParameterSpec(JCA_CURVE_NAMES.get(curve));
            if (matches(parameters, namedSpec)) {
                return curve;
            }
        }
        throw new IllegalArgumentException("Unsupported EC curve.");
    }

    private static boolean matches(ECParameterSpec javaSpec, ECNamedCurveParameterSpec bcSpec) {
        if (!(javaSpec.getCurve().getField() instanceof ECFieldFp javaField)) {
            return false;
        }
        return javaField.getP().equals(bcSpec.getCurve().getField().getCharacteristic())
                && javaSpec.getCurve().getA().equals(bcSpec.getCurve().getA().toBigInteger())
                && javaSpec.getCurve().getB().equals(bcSpec.getCurve().getB().toBigInteger())
                && javaSpec.getGenerator().getAffineX().equals(bcSpec.getG().normalize().getAffineXCoord().toBigInteger())
                && javaSpec.getGenerator().getAffineY().equals(bcSpec.getG().normalize().getAffineYCoord().toBigInteger())
                && javaSpec.getOrder().equals(bcSpec.getN())
                && javaSpec.getCofactor() == bcSpec.getH().intValue();
    }
}
