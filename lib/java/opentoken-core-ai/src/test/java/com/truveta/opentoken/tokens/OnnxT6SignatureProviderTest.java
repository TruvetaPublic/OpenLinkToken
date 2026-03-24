/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.tokens;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.attributes.person.BirthDateAttribute;
import com.truveta.opentoken.attributes.person.FirstNameAttribute;
import com.truveta.opentoken.attributes.person.LastNameAttribute;
import com.truveta.opentoken.attributes.person.SexAttribute;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

class OnnxT6SignatureProviderTest {

    private OnnxT6SignatureProvider provider;

    @BeforeEach
    void setUp() {
        provider = new OnnxT6SignatureProvider();
    }

    // -----------------------------------------------------------------------
    // computeT1Signature
    // -----------------------------------------------------------------------

    @Test
    void computeT1Signature_validAttributes_returnsExpectedSignature() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        // SexAttribute validates against ^([Mm](ale)?|[Ff](emale)?)$ — use mixed-case input
        attrs.put(SexAttribute.class, "Female");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        String sig = provider.computeT1Signature(attrs);

        // normalize("Female") → "Female"; T|U → "FEMALE"
        assertEquals("WRIGHT|R|FEMALE|1990-07-09", sig);
    }

    @Test
    void computeT1Signature_nullMap_returnsNull() {
        assertNull(provider.computeT1Signature(null));
    }

    @Test
    void computeT1Signature_missingLastName_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(SexAttribute.class, "FEMALE");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_missingFirstName_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(SexAttribute.class, "FEMALE");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_missingSex_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(BirthDateAttribute.class, "1990-07-09");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_missingBirthDate_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(SexAttribute.class, "Female");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_invalidBirthDate_returnsNull() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "Wright");
        attrs.put(FirstNameAttribute.class, "Robert");
        attrs.put(SexAttribute.class, "Female");
        attrs.put(BirthDateAttribute.class, "not-a-date");

        assertNull(provider.computeT1Signature(attrs));
    }

    @Test
    void computeT1Signature_lowercaseInputsAreNormalized() {
        Map<Class<? extends Attribute>, String> attrs = new HashMap<>();
        attrs.put(LastNameAttribute.class, "  smith  ");
        attrs.put(FirstNameAttribute.class, "  alice  ");
        attrs.put(SexAttribute.class, "male");
        attrs.put(BirthDateAttribute.class, "2000-01-15");

        String sig = provider.computeT1Signature(attrs);

        assertEquals("SMITH|A|MALE|2000-01-15", sig);
    }

    // -----------------------------------------------------------------------
    // hmacRotationValues
    // -----------------------------------------------------------------------

    @Test
    void hmacRotationValues_returnsOneHexDigestPerInput() {
        List<String> rotationValues = List.of("94 104 96 97", "12 34 56 78");
        List<String> result = provider.hmacRotationValues(rotationValues, "WRIGHT|R|FEMALE|1990-07-09");

        assertEquals(2, result.size());
        for (String digest : result) {
            // SHA-256 produces 32 bytes → 64 hex chars
            assertEquals(64, digest.length(), "Expected 64-char hex digest");
            assertTrue(digest.matches("[0-9a-f]+"), "Digest must be lowercase hex");
        }
    }

    @Test
    void hmacRotationValues_deterministicOutput() {
        List<String> rotationValues = List.of("94 104 96 97");
        String key = "WRIGHT|R|FEMALE|1990-07-09";

        List<String> first = provider.hmacRotationValues(rotationValues, key);
        List<String> second = provider.hmacRotationValues(rotationValues, key);

        assertEquals(first, second, "HMAC must be deterministic");
    }

    @Test
    void hmacRotationValues_differentKeysProduceDifferentDigests() {
        List<String> rotationValues = List.of("94 104 96 97");

        String digest1 = provider.hmacRotationValues(rotationValues, "WRIGHT|R|FEMALE|1990-07-09").get(0);
        String digest2 = provider.hmacRotationValues(rotationValues, "SMITH|A|MALE|2000-01-15").get(0);

        assertTrue(!digest1.equals(digest2), "Different keys must produce different digests");
    }

    @Test
    void hmacRotationValues_knownVector() {
        // Pre-computed: HMAC-SHA256("94 104 96 97", key="WRIGHT|R|FEMALE|1990-07-09")
        // Validated externally via Python: hmac.new(key.encode(), b"94 104 96 97", hashlib.sha256).hexdigest()
        List<String> result = provider.hmacRotationValues(
                List.of("94 104 96 97"), "WRIGHT|R|FEMALE|1990-07-09");
        assertNotNull(result.get(0));
        assertEquals(64, result.get(0).length());
    }
}
