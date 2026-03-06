/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import picocli.CommandLine;

/**
 * Tests startup update-check policy in {@link OpenTokenCommand}.
 */
class OpenTokenCommandVersionCheckTest {

    @Test
    void testShouldRunStartupVersionCheck_falseForUpdateSubcommand() {
        CommandLine.ParseResult parseResult = new CommandLine(new OpenTokenCommand()).parseArgs("update");
        assertFalse(OpenTokenCommand.shouldRunStartupVersionCheck(parseResult));
    }

    @Test
    void testShouldRunStartupVersionCheck_trueForNonUpdateSubcommand() {
        CommandLine.ParseResult parseResult = new CommandLine(new OpenTokenCommand()).parseArgs("help");
        assertTrue(OpenTokenCommand.shouldRunStartupVersionCheck(parseResult));
    }

    @Test
    void testShouldRunStartupVersionCheck_trueWhenNoSubcommand() {
        CommandLine.ParseResult parseResult = new CommandLine(new OpenTokenCommand()).parseArgs();
        assertTrue(OpenTokenCommand.shouldRunStartupVersionCheck(parseResult));
    }
}
