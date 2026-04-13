/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken.tokens;

import java.io.Serializable;
import java.util.List;
import java.util.Set;

import com.truveta.openlinktoken.attributes.AttributeExpression;

/**
 * A generic interface for the token definition.
 */
public interface BaseTokenDefinition extends Serializable {

    /**
     * Get the version of the token definition.
     *
     * @return the token definition version.
     */
    String getVersion();

    /**
     * Get all token identifiers. For example, a set of
     * <code>{ T1, T2, T3, T4, T5 }</code>.
     * <p>
     * The token identifiers are also called rule identifiers because every token is
     * generated from rule definition.
     *
     * @return a set of token identifiers.
     */
    Set<String> getTokenIdentifiers();

    /**
     * Get the token definition for a given token identifier.
     *
     * @param tokenId the token/rule identifier.
     *
     * @return a list of token/rule definition.
     */
    List<AttributeExpression> getTokenDefinition(String tokenId);
}
