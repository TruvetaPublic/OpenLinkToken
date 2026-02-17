/**
 * Copyright (c) Truveta. All rights reserved.
 */

/**
 * Exception thrown when token generation fails.
 *
 * This exception is thrown when there are errors during the token generation
 * process, such as invalid input data, validation failures, or processing errors.
 */
export class TokenGenerationException extends Error {
  cause?: Error;

  /**
   * Constructs a new TokenGenerationException with the specified detail message.
   *
   * @param message - The detail message explaining the reason for the exception.
   * @param cause - The underlying cause of this exception (optional).
   */
  constructor(message: string, cause?: Error) {
    super(message);
    this.name = 'TokenGenerationException';
    
    // Maintain proper stack trace for where our error was thrown (only available on V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, TokenGenerationException);
    }

    // Store the cause if provided
    if (cause) {
      this.cause = cause;
    }
  }
}
