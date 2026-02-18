/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import com.beust.jcommander.JCommander;
import com.beust.jcommander.ParameterException;

/**
 * Unit tests for {@link CommandLineArguments}.
 */
class CommandLineArgumentsTest {

    @Test
    void testRequiredParameters() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander.newBuilder()
                .addObject(args)
                .build()
                .parse("-i", "input.csv", "-t", "csv", "-o", "output.csv");

        assertEquals("input.csv", args.getInputPath());
        assertEquals("csv", args.getInputType());
        assertEquals("output.csv", args.getOutputPath());
    }

    @Test
    void testAllParameters() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander.newBuilder()
                .addObject(args)
                .build()
                .parse(
                        "-i", "input.csv",
                        "-t", "csv",
                        "-o", "output.csv",
                        "-ot", "parquet",
                        "-h", "hashSecret",
                        "-e", "encryptKey",
                        "-d",
                        "--hash-only");

        assertEquals("input.csv", args.getInputPath());
        assertEquals("csv", args.getInputType());
        assertEquals("output.csv", args.getOutputPath());
        assertEquals("parquet", args.getOutputType());
        assertEquals("hashSecret", args.getHashingSecret());
        assertEquals("encryptKey", args.getEncryptionKey());
        assertTrue(args.isDecrypt());
        assertTrue(args.isHashOnly());
    }

    @Test
    void testLongParameterNames() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander.newBuilder()
                .addObject(args)
                .build()
                .parse(
                        "--input", "input.parquet",
                        "--type", "parquet",
                        "--output", "output.parquet",
                        "--output-type", "csv",
                        "--hashingsecret", "myHashSecret",
                        "--encryptionkey", "myEncryptionKey",
                        "--decrypt");

        assertEquals("input.parquet", args.getInputPath());
        assertEquals("parquet", args.getInputType());
        assertEquals("output.parquet", args.getOutputPath());
        assertEquals("csv", args.getOutputType());
        assertEquals("myHashSecret", args.getHashingSecret());
        assertEquals("myEncryptionKey", args.getEncryptionKey());
        assertTrue(args.isDecrypt());
    }

    @Test
    void testDefaultValues() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander.newBuilder()
                .addObject(args)
                .build()
                .parse("-i", "input.csv", "-t", "csv", "-o", "output.csv");

        assertNull(args.getHashingSecret());
        assertNull(args.getEncryptionKey());
        assertEquals("", args.getOutputType());
        assertFalse(args.isDecrypt());
        assertFalse(args.isHashOnly());
        // ringId should have a default random UUID value
        assertTrue(args.getRingId() != null && !args.getRingId().isEmpty());
    }

    @Test
    void testRingIdParameter() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander.newBuilder()
                .addObject(args)
                .build()
                .parse(
                        "-i", "input.csv",
                        "-t", "csv",
                        "-o", "output.csv",
                        "--ring-id", "test-ring-2026-q1");

        assertEquals("test-ring-2026-q1", args.getRingId());
    }

    @Test
    void testMissingRequiredInput() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander jc = JCommander.newBuilder()
                .addObject(args)
                .build();

        assertThrows(ParameterException.class, () -> jc.parse("-t", "csv", "-o", "output.csv"));
    }

    @Test
    void testMissingRequiredType() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander jc = JCommander.newBuilder()
                .addObject(args)
                .build();

        assertThrows(ParameterException.class, () -> jc.parse("-i", "input.csv", "-o", "output.csv"));
    }

    @Test
    void testMissingRequiredOutput() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander jc = JCommander.newBuilder()
                .addObject(args)
                .build();

        assertThrows(ParameterException.class, () -> jc.parse("-i", "input.csv", "-t", "csv"));
    }

    @Test
    void testTypeConstants() {
        assertEquals("csv", CommandLineArguments.TYPE_CSV);
        assertEquals("parquet", CommandLineArguments.TYPE_PARQUET);
    }

    @Test
    void testHashOnlyWithoutDecrypt() {
        CommandLineArguments args = new CommandLineArguments();
        JCommander.newBuilder()
                .addObject(args)
                .build()
                .parse(
                        "-i", "input.csv",
                        "-t", "csv",
                        "-o", "output.csv",
                        "-h", "hashSecret",
                        "--hash-only");

        assertTrue(args.isHashOnly());
        assertFalse(args.isDecrypt());
        assertEquals("hashSecret", args.getHashingSecret());
        assertNull(args.getEncryptionKey());
    }
}
