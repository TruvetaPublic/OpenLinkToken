/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;

/**
 * Package-private encoding primitives shared by the exchange key components.
 */
final class CryptoEncoding implements Serializable {
    private static final long serialVersionUID = 1L;

    private CryptoEncoding() {
    }

    static String encodeBase64Url(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    static byte[] decodeBase64Url(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldName + " must be a non-empty base64url string.");
        }
        try {
            byte[] decoded = Base64.getUrlDecoder().decode(value);
            if (!value.equals(encodeBase64Url(decoded))) {
                throw new IllegalArgumentException("non-canonical base64url encoding");
            }
            return decoded;
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(fieldName + " is not valid base64url data.", exception);
        }
    }

    static byte[] sha256(byte[] value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available.", exception);
        }
    }

    static String fingerprint(byte[] value) {
        byte[] digest = sha256(value);
        StringBuilder result = new StringBuilder(digest.length * 3 - 1);
        for (int index = 0; index < digest.length; index++) {
            if (index > 0) {
                result.append(':');
            }
            result.append(String.format("%02X", digest[index] & 0xFF));
        }
        return result.toString();
    }

    static byte[] encodePem(byte[] value, String type) {
        String encoded = Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.US_ASCII)).encodeToString(value);
        String pem = "-----BEGIN " + type + "-----\n"
                + encoded
                + "\n-----END " + type + "-----\n";
        return pem.getBytes(StandardCharsets.US_ASCII);
    }

    static byte[] decodePem(byte[] pem, String type) {
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
}
