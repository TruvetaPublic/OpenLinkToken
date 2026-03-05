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
    // Cache read / write
    // ------------------------------------------------------------------

    @Test
    void testReadCache_missingFile() {
        VersionChecker checker = new VersionChecker("2.0.0", false);
        // The default cache path won't exist in CI
        Optional<String> result = readCacheFromDir(checker, tempDir.resolve("non-existent.json"));
        assertTrue(result.isEmpty());
    }

    @Test
    void testWriteAndReadCache_roundTrip() throws IOException {
        Path cacheFile = tempDir.resolve("update-check.json");
        VersionChecker checker = new VersionChecker("2.0.0", false);

        writeCacheToPath(checker, "2.1.0", cacheFile);
        Optional<String> result = readCacheFromDir(checker, cacheFile);

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

        VersionChecker checker = new VersionChecker("2.0.0", false);
        Optional<String> result = readCacheFromDir(checker, cacheFile);
        assertTrue(result.isEmpty());
    }

    @Test
    void testReadCache_corruptFile() throws IOException {
        Path cacheFile = tempDir.resolve("update-check.json");
        Files.writeString(cacheFile, "not-valid-json{{{");

        VersionChecker checker = new VersionChecker("2.0.0", false);
        Optional<String> result = readCacheFromDir(checker, cacheFile);
        assertTrue(result.isEmpty());
    }

    @Test
    void testWriteCache_createsParentDirectories() throws IOException {
        Path cacheFile = tempDir.resolve("nested").resolve("dir").resolve("update-check.json");
        VersionChecker checker = new VersionChecker("2.0.0", false);
        writeCacheToPath(checker, "2.1.0", cacheFile);
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

    // ------------------------------------------------------------------
    // Helpers to work around package-private cache methods via reflection
    // ------------------------------------------------------------------

    /**
     * Call {@code readCache()} after temporarily redirecting its path by replacing the
     * cache file contents at the expected location.  Since getCachePath() is package-private
     * static, we use the overriding approach: write to the expected location then read.
     *
     * <p>For unit-test isolation we use a simpler approach: we call the method directly
     * because the test is in the same package.
     */
    private Optional<String> readCacheFromDir(VersionChecker checker, Path customPath) {
        // Save and restore the real cache file so tests are independent
        Path realPath = VersionChecker.getCachePath();
        boolean usedReal = customPath.equals(realPath);

        if (!usedReal && !Files.exists(customPath)) {
            return Optional.empty();
        }

        // The test is in the same package so we can call the package-private method
        // by copying the file to the real location for the duration of the call.
        if (!usedReal) {
            try {
                // Temporarily swap
                boolean parentExists = Files.exists(realPath.getParent());
                Path backup = null;
                if (Files.exists(realPath)) {
                    backup = tempDir.resolve("cache-backup.json");
                    Files.copy(realPath, backup);
                }
                Files.createDirectories(realPath.getParent());
                Files.copy(customPath, realPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                Optional<String> result = checker.readCache();
                // Restore
                if (backup != null) {
                    Files.copy(backup, realPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                } else {
                    Files.deleteIfExists(realPath);
                }
                return result;
            } catch (IOException e) {
                return Optional.empty();
            }
        }
        return checker.readCache();
    }

    private void writeCacheToPath(VersionChecker checker, String latestVersion, Path targetPath) throws IOException {
        Path realPath = VersionChecker.getCachePath();
        boolean usedReal = targetPath.equals(realPath);

        if (!usedReal) {
            // Override the real path temporarily: write cache to a temp location then
            // copy to targetPath. Since writeCache() uses getCachePath() we work around
            // by calling writeCache and then moving the result.
            Path backup = null;
            try {
                if (Files.exists(realPath)) {
                    backup = tempDir.resolve("cache-backup-w.json");
                    Files.copy(realPath, backup);
                }
                checker.writeCache(latestVersion);
                if (Files.exists(realPath)) {
                    Files.createDirectories(targetPath.getParent());
                    Files.copy(realPath, targetPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                }
                // Restore
                if (backup != null) {
                    Files.copy(backup, realPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                } else {
                    Files.deleteIfExists(realPath);
                }
            } catch (IOException e) {
                throw new IOException("Could not write cache to custom path", e);
            }
        } else {
            checker.writeCache(latestVersion);
        }
    }
}
