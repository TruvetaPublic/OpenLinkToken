/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokentransformer;

import com.nimbusds.jose.EncryptionMethod;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWEAlgorithm;
import com.nimbusds.jose.JWEHeader;
import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.JWEObject;
import com.nimbusds.jose.Payload;
import com.nimbusds.jose.crypto.DirectEncrypter;
import com.nimbusds.jose.jwk.OctetSequenceKey;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Formats tokens in the JWE-based match token format (ot.V1.&lt;JWE&gt;).
 * <p>
 * This transformer wraps the privacy-protected identifier (PPID) in a 
 * self-contained JWE structure with all necessary metadata for versioning
 * and cryptographic agility.
 * 
 * @see <a href="https://datatracker.ietf.org/doc/html/rfc7516">RFC 7516 - JSON Web Encryption (JWE)</a>
 */
public class JweMatchTokenFormatter implements TokenTransformer {
    private static final long serialVersionUID = 1L;
    private static final Logger logger = LoggerFactory.getLogger(JweMatchTokenFormatter.class);

    private final String ringId;
    private final String ruleId;
    private final String issuer;
    private final String encryptionKey;
    private transient DirectEncrypter encrypter;

    /**
     * Initializes the JWE match token formatter.
     * 
     * @param encryptionKey the encryption key (must be 32 bytes for AES-256)
     * @param ringId the ring identifier for key management
     * @param ruleId the token rule identifier (e.g., "T1", "T2", etc.)
     * @param issuer the issuer identifier (optional, defaults to "truveta.opentoken")
     * @throws JOSEException if the encrypter cannot be initialized
     */
    public JweMatchTokenFormatter(String encryptionKey, String ringId, String ruleId, String issuer)
            throws JOSEException {
        if (encryptionKey == null || encryptionKey.length() != 32) {
            throw new IllegalArgumentException("Encryption key must be exactly 32 characters (256 bits)");
        }
        if (ringId == null || ringId.isEmpty()) {
            throw new IllegalArgumentException("Ring ID must not be null or empty");
        }
        if (ruleId == null || ruleId.isEmpty()) {
            throw new IllegalArgumentException("Rule ID must not be null or empty");
        }

        this.ringId = ringId;
        this.ruleId = ruleId;
        this.issuer = (issuer != null && !issuer.isEmpty()) ? issuer : "truveta.opentoken";
        this.encryptionKey = encryptionKey;

        // Create a 256-bit key from the encryption key
        byte[] keyBytes = encryptionKey.getBytes(StandardCharsets.UTF_8);
        OctetSequenceKey jwk = new OctetSequenceKey.Builder(keyBytes).build();

        // Initialize direct encrypter for AES-256-GCM
        this.encrypter = new DirectEncrypter(jwk);
    }

    private void writeObject(ObjectOutputStream oos) throws IOException {
        oos.defaultWriteObject();
    }

    private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
        ois.defaultReadObject();
        try {
            byte[] keyBytes = encryptionKey.getBytes(StandardCharsets.UTF_8);
            OctetSequenceKey jwk = new OctetSequenceKey.Builder(keyBytes).build();
            this.encrypter = new DirectEncrypter(jwk);
        } catch (JOSEException e) {
            throw new IOException("Failed to reconstruct JWE encrypter", e);
        }
    }

    /**
     * Transforms a token (PPID) into the JWE match token format.
     * <p>
     * The input token should be the base64-encoded HMAC output from previous transformers.
     * This method wraps it in a JWE structure with metadata and prepends the "ot.V1." prefix.
     * 
     * @param token the privacy-protected identifier (PPID) to wrap in JWE format
     * @return the formatted match token: ot.V1.&lt;JWE compact serialization&gt;
     * @throws Exception if JWE encryption or serialization fails
     */
    @Override
    public String transform(String token) throws Exception {
        if (token == null || token.isBlank()) {
            logger.warn("Received null or empty token for rule {}", ruleId);
            return token; // Return as-is for blank tokens
        }

        try {
            // Build the JWE payload with metadata using a Map
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put(MatchTokenConstants.PAYLOAD_KEY_RULE_ID, ruleId);
            payload.put(MatchTokenConstants.PAYLOAD_KEY_HASH_ALGORITHM, "SHA-256");
            payload.put(MatchTokenConstants.PAYLOAD_KEY_MAC_ALGORITHM, "HS256");
            payload.put(MatchTokenConstants.PAYLOAD_KEY_PPID, Collections.singletonList(token));
            payload.put(MatchTokenConstants.PAYLOAD_KEY_RING_ID, ringId);
            payload.put(MatchTokenConstants.PAYLOAD_KEY_ISSUER, issuer);
            payload.put(MatchTokenConstants.PAYLOAD_KEY_ISSUED_AT, Instant.now().getEpochSecond());

            // Create JWE header with algorithm and encryption method
            JWEHeader header = new JWEHeader.Builder(JWEAlgorithm.DIR, EncryptionMethod.A256GCM)
                    .type(new JOSEObjectType(MatchTokenConstants.TOKEN_TYPE))
                    .keyID(ringId)
                    .build();

            // Create JWE object with the payload (Payload accepts Map and converts to JSON)
            JWEObject jweObject = new JWEObject(header, new Payload(payload));

            // Encrypt the JWE object
            jweObject.encrypt(encrypter);

            // Serialize to compact form and prepend the ot.V1. prefix
            String jweCompact = jweObject.serialize();
            return MatchTokenConstants.V1_TOKEN_PREFIX + jweCompact;

        } catch (JOSEException e) {
            logger.error("Failed to create JWE token for rule {}: {}", ruleId, e.getMessage());
            throw new Exception("JWE token generation failed", e);
        }
    }
}
