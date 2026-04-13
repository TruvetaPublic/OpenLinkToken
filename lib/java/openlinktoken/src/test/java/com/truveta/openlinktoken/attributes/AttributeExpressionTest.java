/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.attributes;

import java.util.UUID;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import com.truveta.openlinktoken.attributes.general.RecordIdAttribute;
import com.truveta.openlinktoken.attributes.person.SocialSecurityNumberAttribute;

class AttributeExpressionTest {

    @Test
    void getEffectiveValue_With_Empty_Expression_Works() {
        var attribute = new AttributeExpression(RecordIdAttribute.class, null);
        var value = UUID.randomUUID().toString();
        var result = attribute.getEffectiveValue(value);

        Assertions.assertEquals(value, result);
    }

    @Test
    void getEffectiveValue_With_Uppercase_Expression_Works() {
        var attribute = new AttributeExpression(RecordIdAttribute.class, "U");
        var value = "abcd";
        var result = attribute.getEffectiveValue(value);

        Assertions.assertEquals("ABCD", result);
    }

    @Test
    void getEffectiveValue_With_Trim_Expression_Works() {
        var attribute = new AttributeExpression(RecordIdAttribute.class, "T");
        var value = " abcd ";
        var result = attribute.getEffectiveValue(value);

        Assertions.assertEquals("abcd", result);
    }

    @Test
    void getEffectiveValue_With_Substring_Expression_Works() {
        var attribute1 = new AttributeExpression(RecordIdAttribute.class, "s(0,1)");
        var attribute2 = new AttributeExpression(RecordIdAttribute.class, "S(3,4)");
        var value = "abcd";
        var result1 = attribute1.getEffectiveValue(value);
        var result2 = attribute2.getEffectiveValue(value);

        Assertions.assertEquals("a", result1);
        Assertions.assertEquals("d", result2);
    }

    @Test
    void getEffectiveValue_With_Substring_OutOfBounds_Works() {
        var attribute1 = new AttributeExpression(RecordIdAttribute.class, "s(0,1)");
        var attribute2 = new AttributeExpression(RecordIdAttribute.class, "S(3,16)");
        var value = "abcd";
        var result1 = attribute1.getEffectiveValue(value);
        var result2 = attribute2.getEffectiveValue(value);

        Assertions.assertEquals("a", result1);
        Assertions.assertEquals("d", result2);
    }

    @Test
    void getEffectiveValue_With_Replace_Expression_Works() {
        var attribute1 = new AttributeExpression(RecordIdAttribute.class, "R('/','-')");
        var attribute2 = new AttributeExpression(RecordIdAttribute.class, "r('9999','')");
        var value = "99/99/9999";
        var result1 = attribute1.getEffectiveValue(value);
        var result2 = attribute2.getEffectiveValue(value);

        Assertions.assertEquals("99-99-9999", result1);
        Assertions.assertEquals("99/99/", result2);
    }

    @Test
    void getEffectiveValue_With_Match_Expression_Works() {
        var attribute1 = new AttributeExpression(SocialSecurityNumberAttribute.class, "M(\\d+)");
        var value1 = "123-45-6789";
        var result1 = attribute1.getEffectiveValue(value1);

        Assertions.assertEquals("123456789", result1);
    }

    @Test
    void getEffectiveValue_With_Multiple_Expressions_Works() {
        var attribute1 = new AttributeExpression(RecordIdAttribute.class, "U|T|R('.','')|S(5,7)");

        var value = "1234 56th Ave.";
        var result1 = attribute1.getEffectiveValue(value);

        Assertions.assertEquals("56", result1);
    }

    @Test
    void invalid_Expression_Throws() {
        var value = "whatever";

        var attribute = new AttributeExpression(RecordIdAttribute.class, "R(5,9)");
        try {
            attribute.getEffectiveValue(value);
        } catch (Exception ex) {
            Assertions.assertTrue(ex instanceof IllegalArgumentException);
        }

        attribute = new AttributeExpression(RecordIdAttribute.class, "S('d',9)");
        try {
            attribute.getEffectiveValue(value);
        } catch (Exception ex) {
            Assertions.assertTrue(ex instanceof IllegalArgumentException);
        }
    }
}
