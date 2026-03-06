/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.util;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit tests for {@link VersionChecker}.
 */
class VersionCheckerTest {

    @TempDir
    Path tempDir;

    private PrintStream originalErr;

    @BeforeEach
    void setUp() {
        originalErr = System.err;
    }

    @AfterEach
    void tearDown() {
        System.setErr(originalErr);
    }

    // ------------------------------------------------------------------
    // isNewer – semantic version comparison
    // ------------------------------------------------------------------

    @Test
    void testIsNewer_patchVersion() {
        assertTrue(VersionChecker.isNewer("2.0.1", "2.0.0"));
    }

    @Test
    void testIsNewer_minorVersion() {
        assertTrue(VersionChecker.isNewer("2.1.0", "2.0.0"));
    }

    @Test
    void testIsNewer_majorVersion() {
        assertTrue(VersionChecker.isNewer("3.0.0", "2.0.0"));
    }

    @Test
    void testIsNewer_sameVersion() {
        assertFalse(VersionChecker.isNewer("2.0.0", "2.0.0"));
    }

    @Test
    void testIsNewer_olderVersion() {
        assertFalse(VersionChecker.isNewer("1.9.0", "2.0.0"));
    }

    @Test
    void testIsNewer_releaseIsNewerThanAlpha() {
        assertTrue(VersionChecker.isNewer("2.0.0", "2.0.0-alpha"));
    }

    @Test
    void testIsNewer_alphaIsNotNewerThanSameAlpha() {
        assertFalse(VersionChecker.isNewer("2.0.0-alpha", "2.0.0-alpha"));
    }

    @Test
    void testIsNewer_nullCandidate() {
        assertFalse(VersionChecker.isNewer(null, "2.0.0"));
    }

    @Test
    void testIsNewer_nullCurrent() {
        assertFalse(VersionChecker.isNewer("2.0.0", null));
    }

    // ------------------------------------------------------------------
    // Disable logic
    // ------------------------------------------------------------------

    @Test
    void testStart_doesNothingWhenFlagSet() {
        VersionChecker checker = new VersionChecker("2.0.0", true);
        checker.start();
        // future should be null – no thread spawned; waitAndNotify must not throw
        checker.waitAndNotify();
    }

    // ------------------------------------------------------------------
    // Cache read / write (using injectable cache path via package-private constructor)
    // ------------------------------------------------------------------

    @Test
    void testReadCache_missingFile() {
        Path cacheFile = tempDir.resolve("non-existent.json");
        VersionChecker checker = new VersionChecker("2.0.0", false, cacheFile);
        Optional<String> result = checker.readCache();
        assertTrue(result.isEmpty());
    }

    @Test
    void testWriteAndReadCache_roundTrip() throws IOException {
        Path cacheFile = tempDir.resolve("update-check.json");
        VersionChecker checker = new VersionChecker("2.0.0", false, cacheFile);

        checker.writeCache("2.1.0");
        Optional<String> result = checker.readCache();

        assertTrue(result.isPresent());
        assertEquals("2.1.0", result.get());
    }

    @Test
    void testReadCache_expiredEntry() throws IOException {
        Path cacheFile = tempDir.resolve("update-check.json");

        // Write a cache entry that is 25 hours old
        Instant old = Instant.now().minus(25, ChronoUnit.HOURS);
        String json = "{\"last_checked\":\"" + old.toString() + "\","
                + "\"latest_version\":\"2.1.0\","
                + "\"current_version\":\"2.0.0\"}";
        Files.writeString(cacheFile, json);

        VersionChecker checker = new VersionChecker("2.0.0", false, cacheFile);
        Optional<String> result = checker.readCache();
        assertTrue(result.isEmpty());
    }

    @Test
    void testReadCache_corruptFile() throws IOException {
        Path cacheFile = tempDir.resolve("update-check.json");
        Files.writeString(cacheFile, "not-valid-json{{{");

        VersionChecker checker = new VersionChecker("2.0.0", false, cacheFile);
        Optional<String> result = checker.readCache();
        assertTrue(result.isEmpty());
    }

    @Test
    void testWriteCache_createsParentDirectories() throws IOException {
        Path cacheFile = tempDir.resolve("nested").resolve("dir").resolve("update-check.json");
        VersionChecker checker = new VersionChecker("2.0.0", false, cacheFile);
        checker.writeCache("2.1.0");
        assertTrue(Files.exists(cacheFile));
    }

    // ------------------------------------------------------------------
    // getCachePath
    // ------------------------------------------------------------------

    @Test
    void testGetCachePath_returnsPath() {
        Path path = VersionChecker.getCachePath();
        assertNotNull(path);
        assertEquals("update-check.json", path.getFileName().toString());
    }

    // ------------------------------------------------------------------
    // waitAndNotify – no thread set
    // ------------------------------------------------------------------

    @Test
    void testWaitAndNotify_noThread() {
        VersionChecker checker = new VersionChecker("2.0.0", false);
        // Should not throw even though start() was never called
        checker.waitAndNotify();
    }
}
