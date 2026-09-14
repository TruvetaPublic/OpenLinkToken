/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

/**
 * Placeholder for Python-side JWE envelope helpers used by the Open Link Token CLI exchange workflow.
 *
 * <p>The full implementation lives in the Python package under
 * {@code openlinktoken.exchange_jwe} and handles building and decrypting multi-recipient
 * JWE envelopes for the {@code olt initiate-exchange} command. A Java equivalent
 * has not yet been implemented because the exchange-config workflow is currently
 * Python-CLI only. This marker is intentionally kept in the corresponding Java
 * package so cross-language tooling can identify the boundary explicitly.
 *
 * @see <a href="../../../../python/openlinktoken/exchange_jwe.py">exchange_jwe.py</a>
 */
public final class ExchangeJwe {

    private ExchangeJwe() {
    }
}
