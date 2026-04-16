/* SPDX-License-Identifier: MIT */
package org.openlinktoken;

/**
 * Placeholder for Python-side exchange-config loading and resolution used by the Open Link Token CLI.
 *
 * <p>The full implementation lives in the Python package under
 * {@code openlinktoken.exchange_config} and handles loading, validating, and decrypting
 * initiate-exchange config files produced by {@code openlinktoken initiate-exchange}.
 * A Java equivalent has not yet been implemented because the exchange-config consumer
 * workflow is currently Python-CLI only.
 *
 * @see <a href="../../../../python/openlinktoken/exchange_config.py">exchange_config.py</a>
 */
public final class ExchangeConfig {

    private ExchangeConfig() {
    }
}
