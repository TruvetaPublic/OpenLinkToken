/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermission;
import java.util.EnumSet;
import java.util.Optional;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import picocli.CommandLine;

/**
 * Unit tests for {@link UpdateCommand}.
 */
class UpdateCommandTest {

    @TempDir
    Path tempDir;

    private PrintStream originalOut;
    private PrintStream originalErr;
    private ByteArrayOutputStream outBuffer;
    private ByteArrayOutputStream errBuffer;

    @BeforeEach
    void setUp() {
        originalOut = System.out;
        originalErr = System.err;
        outBuffer = new ByteArrayOutputStream();
        errBuffer = new ByteArrayOutputStream();
        System.setOut(new PrintStream(outBuffer));
        System.setErr(new PrintStream(errBuffer));
    }

    @AfterEach
    void tearDown() {
        System.setOut(originalOut);
        System.setErr(originalErr);
    }

    @Test
    void testCallDryRunReturnsSuccessWithoutDownloadOrReplace() {
        TestableUpdateCommand command = new TestableUpdateCommand();
        command.releaseInfo = release("v99.0.0", "https://example.com/release");
        command.asset = asset("opentoken-linux-x86_64", "https://example.com/opentoken-linux-x86_64");

        int exitCode = new CommandLine(command).execute("--dry-run");

        assertEquals(0, exitCode);
        assertFalse(command.downloadCalled);
        assertFalse(command.replaceCalled);
        assertTrue(outBuffer.toString().contains("Would update OpenToken"));
    }

    @Test
    void testCallAssetMissingReturnsError() {
        TestableUpdateCommand command = new TestableUpdateCommand();
        command.releaseInfo = release("v99.0.0", "https://example.com/release");
        command.asset = null;

        int exitCode = new CommandLine(command).execute("-y");

        assertEquals(1, exitCode);
        assertFalse(command.downloadCalled);
        assertFalse(command.replaceCalled);
        assertTrue(errBuffer.toString().contains("No suitable release asset found"));
    }

    @Test
    void testCallChecksumMismatchReturnsErrorWithoutReplace() {
        TestableUpdateCommand command = new TestableUpdateCommand();
        command.releaseInfo = release("v99.0.0", "https://example.com/release");
        command.asset = asset("opentoken-linux-x86_64", "https://example.com/opentoken-linux-x86_64");
        command.checksumAsset = asset("opentoken-linux-x86_64.sha256", "https://example.com/opentoken-linux-x86_64.sha256");
        command.downloadResult = true;
        command.checksumResult = Optional.of("expected-hash");
        command.sha256Result = "actual-hash";

        int exitCode = new CommandLine(command).execute("-y");

        assertEquals(1, exitCode);
        assertTrue(command.downloadCalled);
        assertFalse(command.replaceCalled);
        assertTrue(errBuffer.toString().contains("Checksum verification failed"));
    }

    @Test
    void testReplaceBinaryNonWritableTargetReturnsError() throws IOException {
        assumeTrue(Files.getFileStore(tempDir).supportsFileAttributeView("posix"));

        Path source = tempDir.resolve("opentoken-download");
        Path target = tempDir.resolve("opentoken");
        Files.writeString(source, "binary");
        Files.writeString(target, "existing");
        Files.setPosixFilePermissions(target, EnumSet.of(PosixFilePermission.OWNER_READ));
        assumeTrue(!Files.isWritable(target));

        TestableUpdateCommand command = new TestableUpdateCommand();
        command.targetBinary = target;

        int exitCode = command.replaceBinary(source, "opentoken-linux-x86_64");

        assertEquals(1, exitCode);
        assertTrue(errBuffer.toString().contains("Insufficient permissions"));
    }

    private static ObjectNode release(String tag, String htmlUrl, ObjectNode... assets) {
        ObjectMapper mapper = new ObjectMapper();
        ObjectNode release = mapper.createObjectNode();
        release.put("tag_name", tag);
        release.put("html_url", htmlUrl);
        ArrayNode assetArray = release.putArray("assets");
        for (ObjectNode asset : assets) {
            assetArray.add(asset);
        }
        return release;
    }

    private static ObjectNode asset(String name, String url) {
        ObjectMapper mapper = new ObjectMapper();
        ObjectNode asset = mapper.createObjectNode();
        asset.put("name", name);
        asset.put("browser_download_url", url);
        return asset;
    }

    private static class TestableUpdateCommand extends UpdateCommand {
        JsonNode releaseInfo;
        JsonNode asset;
        JsonNode checksumAsset;
        boolean downloadResult;
        boolean downloadCalled;
        boolean replaceCalled;
        Optional<String> checksumResult = Optional.empty();
        String sha256Result = "";
        Path targetBinary;

        @Override
        JsonNode fetchLatestRelease() {
            return releaseInfo;
        }

        @Override
        JsonNode fetchReleaseByTag(String tag) {
            return releaseInfo;
        }

        @Override
        JsonNode findAsset(JsonNode releaseInfo) {
            return asset;
        }

        @Override
        JsonNode findChecksumAsset(JsonNode releaseInfo, String assetName) {
            return checksumAsset;
        }

        @Override
        boolean downloadFile(String url, Path dest) {
            downloadCalled = true;
            return downloadResult;
        }

        @Override
        Optional<String> fetchChecksum(String url, String assetName) {
            return checksumResult;
        }

        @Override
        String sha256File(Path path) {
            return sha256Result;
        }

        @Override
        int replaceBinary(Path src, String assetName) throws IOException {
            replaceCalled = true;
            return super.replaceBinary(src, assetName);
        }

        @Override
        Path findTargetBinary() {
            return targetBinary;
        }
    }
}
