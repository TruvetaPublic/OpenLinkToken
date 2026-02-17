/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.util.concurrent.Callable;

import org.jline.terminal.Terminal;
import org.jline.terminal.TerminalBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.HelpCommand;

/**
 * Main entry point command for OpenToken CLI with subcommands.
 * Provides modern, subcommand-based interface for token operations.
 */
@Command(
    name = "opentoken",
    description = "Privacy-preserving person matching via cryptographic tokens",
    mixinStandardHelpOptions = true,
    version = "OpenToken 1.12.5",
    subcommands = {
        HelpCommand.class,
        TokenizeCommand.class,
        EncryptCommand.class,
        DecryptCommand.class,
        PackageCommand.class
    }
)
public class OpenTokenCommand implements Callable<Integer> {
    
    private static final Logger logger = LoggerFactory.getLogger(OpenTokenCommand.class);
    
    /**
     * Display the OpenToken banner for interactive sessions.
     */
    public static void showBanner() {
        // Check if we're in an interactive terminal and NO_COLOR is not set
        if (!isInteractive() || System.getenv("NO_COLOR") != null) {
            return;
        }
        
        try {
            Terminal terminal = TerminalBuilder.builder()
                .system(true)
                .build();
            
            String banner = getColorizedBanner();
            terminal.writer().println(banner);
            terminal.writer().flush();
        } catch (Exception e) {
            // Silently fail banner display - it's not critical
            logger.debug("Could not display banner", e);
        }
    }
    
    /**
     * Check if stdout is connected to an interactive terminal.
     */
    private static boolean isInteractive() {
        try {
            Terminal terminal = TerminalBuilder.builder()
                .system(true)
                .dumb(true)
                .build();
            return terminal.getType() != Terminal.TYPE_DUMB;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Get the colorized OpenToken banner.
     */
    private static String getColorizedBanner() {
        String cyan = "\u001B[36m";
        String blue = "\u001B[34m";
        String reset = "\u001B[0m";
        
        return cyan + "  ___                 _____     _              " + reset + "\n" +
               cyan + " / _ \\ _ __   ___ _ _|_   _|__ | | _____ _ __  " + reset + "\n" +
               cyan + "| | | | '_ \\ / _ \\ '_ \\| |/ _ \\| |/ / _ \\ '_ \\ " + reset + "\n" +
               cyan + "| |_| | |_) |  __/ | | | | (_) |   <  __/ | | |" + reset + "\n" +
               cyan + " \\___/| .__/ \\___|_| |_|_|\\___/|_|\\_\\___|_| |_|" + reset + "\n" +
               cyan + "      |_|                                       " + reset + "\n" +
               blue + "Privacy-Preserving Person Matching v1.12.5" + reset + "\n";
    }
    
    @Override
    public Integer call() {
        // If no subcommand is specified, show help
        CommandLine.usage(this, System.out);
        return 0;
    }
    
    /**
     * Main entry point for the command-line application.
     */
    public static void main(String[] args) {
        int exitCode = execute(args);
        System.exit(exitCode);
    }
    
    /**
     * Execute the CLI without calling System.exit().
     * Useful for testing or when embedding the CLI in another application.
     * 
     * @param args command-line arguments
     * @return exit code (0 for success, non-zero for errors)
     */
    public static int execute(String[] args) {
        // Show banner for interactive runs (not for --help or piped output)
        if (args.length == 0 || !isHelpRequest(args)) {
            showBanner();
        }
        
        CommandLine commandLine = new CommandLine(new OpenTokenCommand());
        commandLine.setExecutionStrategy(new CommandLine.RunLast());
        
        return commandLine.execute(args);
    }
    
    /**
     * Check if the command is a help request.
     */
    private static boolean isHelpRequest(String[] args) {
        for (String arg : args) {
            if (arg.equals("--help") || arg.equals("help")) {
                return true;
            }
        }
        return false;
    }
}
