/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokens;

/**
 * Exception thrown when token generation fails.
 * <p>
 * This exception is thrown when there are errors during the token generation
 * process, such as invalid input data, validation failures, or processing errors.
 * </p>
 */
public class TokenGenerationException extends Exception {

    /**
     * Constructs a new TokenGenerationException with the specified detail message.
     *
     * @param message the detail message explaining the reason for the exception
     */
    public TokenGenerationException(String message) {
        super(message);
    }

    /**
     * Constructs a new TokenGenerationException with the specified detail message and cause.
     *
     * @param message the detail message explaining the reason for the exception
     * @param cause the underlying cause of this exception
     */
    public TokenGenerationException(String message, Throwable cause) {
        super(message, cause);
    }
}
