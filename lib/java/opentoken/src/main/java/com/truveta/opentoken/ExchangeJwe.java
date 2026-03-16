/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken;

/**
 * Placeholder for Python-side JWE envelope helpers used by the OpenToken CLI exchange workflow.
 *
 * <p>The full implementation lives in the Python package under
 * {@code opentoken.exchange_jwe} and handles building and decrypting multi-recipient
 * JWE envelopes for the {@code opentoken initiate-exchange} command. A Java equivalent
 * has not yet been implemented because the exchange-config workflow is currently
 * Python-CLI only.
 *
 * @see <a href="../../../../python/opentoken/exchange_jwe.py">exchange_jwe.py</a>
 */
public final class ExchangeJwe {

    private ExchangeJwe() {
    }
}
