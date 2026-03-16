/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken;

/**
 * Placeholder for Python-side EC key utilities used by the OpenToken CLI exchange workflow.
 *
 * <p>The full implementation lives in the Python package under
 * {@code opentoken.ec_key_utils} and handles key-pair generation, PEM serialization,
 * public-key fingerprinting, and secure key file I/O. A Java equivalent has not yet
 * been implemented because the exchange-config workflow is currently Python-CLI only.
 *
 * @see <a href="../../../../python/opentoken/ec_key_utils.py">ec_key_utils.py</a>
 */
public final class EcKeyUtils {

    private EcKeyUtils() {
    }
}
