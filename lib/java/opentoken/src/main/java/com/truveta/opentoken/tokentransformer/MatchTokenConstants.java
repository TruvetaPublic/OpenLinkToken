/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokentransformer;

/**
 * Shared constants for match token formatting and parsing.
 */
public final class MatchTokenConstants {

    private MatchTokenConstants() {
        // Utility class, prevent instantiation
    }

    /** Prefix for version 1 match tokens. */
    public static final String V1_TOKEN_PREFIX = "ot.V1.";

    /** Token type value for JWE header. */
    public static final String TOKEN_TYPE = "match-token";

    /** Payload key for rule identifier. */
    public static final String PAYLOAD_KEY_RULE_ID = "rlid";

    /** Payload key for hash algorithm. */
    public static final String PAYLOAD_KEY_HASH_ALGORITHM = "hash_alg";

    /** Payload key for MAC algorithm. */
    public static final String PAYLOAD_KEY_MAC_ALGORITHM = "mac_alg";

    /** Payload key for privacy-preserved identifier list. */
    public static final String PAYLOAD_KEY_PPID = "ppid";

    /** Payload key for key ring identifier. */
    public static final String PAYLOAD_KEY_RING_ID = "rid";

    /** Payload key for issuer. */
    public static final String PAYLOAD_KEY_ISSUER = "iss";

    /** Payload key for issued-at timestamp. */
    public static final String PAYLOAD_KEY_ISSUED_AT = "iat";

    /** Header key for key identifier. */
    public static final String HEADER_KEY_KEY_ID = "kid";
}
