/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.openlinktoken;

/**
 * Placeholder for Python-side JWE envelope helpers used by the OpenLinkToken CLI exchange workflow.
 *
 * <p>The full implementation lives in the Python package under
 * {@code openlinktoken.exchange_jwe} and handles building and decrypting multi-recipient
 * JWE envelopes for the {@code openlinktoken initiate-exchange} command. A Java equivalent
 * has not yet been implemented because the exchange-config workflow is currently
 * Python-CLI only.
 *
 * @see <a href="../../../../python/openlinktoken/exchange_jwe.py">exchange_jwe.py</a>
 */
public final class ExchangeJwe {

    private ExchangeJwe() {
    }
}
