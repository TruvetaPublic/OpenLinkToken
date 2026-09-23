/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

/**
 * Package-private deterministic JSON support for exchange key bundles.
 */
final class JsonSupport {

    private static final TypeReference<Map<String, Object>> OBJECT_TYPE = new TypeReference<>() {
    };

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_TRAILING_TOKENS, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private JsonSupport() {
    }

    static Map<String, Object> readObject(byte[] json) {
        if (json == null || json.length == 0) {
            throw new IllegalArgumentException("JSON value must not be empty.");
        }
        try {
            return MAPPER.readValue(decodeUtf8(json), OBJECT_TYPE);
        } catch (IOException exception) {
            throw new IllegalArgumentException("JSON value must be an object.", exception);
        }
    }

    static byte[] writeObject(Map<String, Object> value) {
        try {
            return MAPPER.writeValueAsBytes(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Unable to serialize JSON object.", exception);
        }
    }

    private static String decodeUtf8(byte[] json) {
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(json))
                    .toString();
        } catch (CharacterCodingException exception) {
            throw new IllegalArgumentException("JSON value must be valid UTF-8.", exception);
        }
    }
}
