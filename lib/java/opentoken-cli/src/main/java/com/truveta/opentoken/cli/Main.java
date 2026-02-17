/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli;

import com.truveta.opentoken.cli.commands.OpenTokenCommand;

/**
 * Entry point for the OpenToken command-line application.
 * <p>
 * Provides a modern subcommand-based interface for token operations:
 * <ul>
 *   <li><code>opentoken tokenize</code> - Hash-only token generation</li>
 *   <li><code>opentoken encrypt</code> - Encrypt hashed tokens</li>
 *   <li><code>opentoken decrypt</code> - Decrypt encrypted tokens</li>
 *   <li><code>opentoken package</code> - Tokenize + encrypt in one step</li>
 *   <li><code>opentoken help [command]</code> - Display help information</li>
 * </ul>
 */
public class Main {

    /**
     * Application entry point. Routes to the subcommand-based interface.
     *
     * @param args command-line arguments
     */
    public static void main(String[] args) {
        OpenTokenCommand.main(args);
    }
}
