/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.util;

import java.io.IOException;
import java.io.PrintStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * Asynchronous version checker that compares the running version against the
 * latest GitHub release.
 *
 * <p>The check runs in the background via a {@link CompletableFuture} so it
 * never blocks or delays normal command execution. The notice is surfaced to
 * stderr only after the primary command has completed.
 *
 * <p>Results are cached for 24 hours in an OpenToken-specific user directory
 * to avoid hitting the GitHub API on every invocation.
 */
public final class VersionChecker {

    private static final Logger logger = LoggerFactory.getLogger(VersionChecker.class);

    private static final String GITHUB_API_URL =
            "https://api.github.com/repos/TruvetaPublic/OpenToken/releases/latest";
    private static final long CACHE_TTL_SECONDS = 24L * 60 * 60;
    private static final int REQUEST_TIMEOUT_SECONDS = 2;
    private static final String ENV_DISABLE = "OPENTOKEN_DISABLE_UPDATE_CHECK";
    private static final String CACHE_FILENAME = "update-check.json";
    private static final String CACHE_DIR_NAME = ".opentoken";

    private final String currentVersion;
    private final boolean noUpdateCheck;
    private final Path cachePathOverride;

    private CompletableFuture<Optional<String>> future;

    /**
     * Creates a new VersionChecker.
     *
     * @param currentVersion the running version string (e.g. {@code "2.0.0-alpha"})
     * @param noUpdateCheck  when {@code true} the checker is disabled entirely
     */
    public VersionChecker(String currentVersion, boolean noUpdateCheck) {
        this(currentVersion, noUpdateCheck, null);
    }

    /**
     * Package-private constructor that allows injecting a custom cache path for testing.
     *
     * @param currentVersion    the running version string
     * @param noUpdateCheck     when {@code true} the checker is disabled entirely
     * @param cachePathOverride when non-null, used instead of the default OS config path
     */
    VersionChecker(String currentVersion, boolean noUpdateCheck, Path cachePathOverride) {
        this.currentVersion = currentVersion;
        this.noUpdateCheck = noUpdateCheck;
        this.cachePathOverride = cachePathOverride;
    }

    /**
     * Launch the background version check.
     *
     * <p>Does nothing when update checks are disabled via {@code --no-update-check}
     * or the {@code OPENTOKEN_DISABLE_UPDATE_CHECK} environment variable.
     */
    public void start() {
        if (isDisabled()) {
            return;
        }

        future = CompletableFuture.supplyAsync(this::run);
    }

    /**
     * Wait for the background check to finish and, if a newer version is available
     * and stderr is an interactive TTY, print an update notice to stderr.
     *
     * <p>This method should be called <em>after</em> the primary command has
     * completed so it never adds latency to the critical path.
     */
    public void waitAndNotify() {
        if (future == null) {
            return;
        }

        Optional<String> result;
        try {
            result = future.get(REQUEST_TIMEOUT_SECONDS + 1L, TimeUnit.SECONDS);
        } catch (Exception e) {
            logger.debug("Version check did not complete in time", e);
            return;
        }

        result.ifPresent(latest -> {
            if (isNewer(latest, currentVersion) && isStderrInteractive()) {
                printNotice(latest);
            }
        });
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    private boolean isDisabled() {
        if (noUpdateCheck) {
            return true;
        }
        String env = System.getenv(ENV_DISABLE);
        return "1".equals(env != null ? env.trim() : "");
    }

    private Optional<String> run() {
        try {
            Optional<String> cached = readCache();
            if (cached.isPresent()) {
                return cached;
            }

            Optional<String> fetched = fetchLatestVersion();
            fetched.ifPresent(v -> writeCache(v));
            return fetched;
        } catch (Exception e) {
            logger.debug("Version check failed", e);
            return Optional.empty();
        }
    }

    // ------------------------------------------------------------------
    // GitHub API fetch
    // ------------------------------------------------------------------

    /**
     * Query the GitHub Releases API and return the latest version tag (without leading "v").
     *
     * @return the version string, or empty if the request failed
     */
    Optional<String> fetchLatestVersion() {
        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(GITHUB_API_URL))
                    .header("User-Agent", "opentoken-cli")
                    .timeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                return Optional.empty();
            }

            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(response.body());
            String tag = root.path("tag_name").asText("");
            if (tag.isBlank()) {
                return Optional.empty();
            }
            return Optional.of(tag.startsWith("v") ? tag.substring(1) : tag);
        } catch (Exception e) {
            logger.debug("Failed to fetch latest version from GitHub", e);
            return Optional.empty();
        }
    }

    // ------------------------------------------------------------------
    // Cache helpers
    // ------------------------------------------------------------------

    /**
     * Return the platform-appropriate path for the cache file.
     *
     * @return the cache file path
     */
    static Path getCachePath() {
        String appData = System.getenv("APPDATA");
        if (appData != null && !appData.isBlank()) {
            return Paths.get(appData, CACHE_DIR_NAME, CACHE_FILENAME);
        }
        String home = System.getProperty("user.home", "");
        return Paths.get(home, CACHE_DIR_NAME, CACHE_FILENAME);
    }

    /**
     * Read the cached version result if it exists and is within the TTL.
     *
     * @return the cached latest version, or empty if missing/expired
     */
    Optional<String> readCache() {
        try {
            Path cachePath = cachePathOverride != null ? cachePathOverride : getCachePath();
            if (!Files.exists(cachePath)) {
                return Optional.empty();
            }

            String content = Files.readString(cachePath);
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(content);

            String lastCheckedStr = root.path("last_checked").asText("");
            if (lastCheckedStr.isBlank()) {
                return Optional.empty();
            }

            Instant lastChecked = Instant.parse(lastCheckedStr);
            long ageSeconds = Instant.now().getEpochSecond() - lastChecked.getEpochSecond();
            if (ageSeconds > CACHE_TTL_SECONDS) {
                return Optional.empty();
            }

            String latest = root.path("latest_version").asText("");
            return latest.isBlank() ? Optional.empty() : Optional.of(latest);
        } catch (IOException | DateTimeParseException e) {
            logger.debug("Could not read version cache", e);
            return Optional.empty();
        }
    }

    /**
     * Write the fetched version to the cache file, silently ignoring errors.
     *
     * @param latestVersion the version string to cache
     */
    void writeCache(String latestVersion) {
        try {
            Path cachePath = cachePathOverride != null ? cachePathOverride : getCachePath();
            Files.createDirectories(cachePath.getParent());

            ObjectMapper mapper = new ObjectMapper();
            ObjectNode payload = mapper.createObjectNode();
            payload.put("last_checked", Instant.now().toString());
            payload.put("latest_version", latestVersion);
            payload.put("current_version", currentVersion);

            Files.writeString(cachePath, mapper.writeValueAsString(payload));
        } catch (IOException e) {
            logger.debug("Could not write version cache", e);
        }
    }

    // ------------------------------------------------------------------
    // Version comparison
    // ------------------------------------------------------------------

    /**
     * Return {@code true} when {@code candidate} is strictly greater than
     * {@code current} using semantic-version rules.
     *
     * <p>Version strings are split on {@code .} and compared numerically where
     * possible, falling back to lexicographic comparison for pre-release suffixes.
     *
     * @param candidate the version to test
     * @param current   the baseline version
     * @return whether {@code candidate} is newer
     */
    public static boolean isNewer(String candidate, String current) {
        if (candidate == null || current == null) {
            return false;
        }
        try {
            int[] cand = parseSemver(candidate);
            int[] curr = parseSemver(current);
            int len = Math.max(cand.length, curr.length);
            for (int i = 0; i < len; i++) {
                int c = i < cand.length ? cand[i] : 0;
                int r = i < curr.length ? curr[i] : 0;
                if (c != r) {
                    return c > r;
                }
            }
            // Numeric parts equal: check pre-release.
            // A release without a pre-release label is newer than one with one.
            boolean candHasPre = candidate.contains("-");
            boolean currHasPre = current.contains("-");
            if (currHasPre && !candHasPre) {
                return true;  // e.g. 2.0.0 > 2.0.0-alpha
            }
            if (!currHasPre && candHasPre) {
                return false; // e.g. 2.0.0-alpha < 2.0.0
            }
            // Both have (or lack) pre-release; compare lexicographically
            return candidate.compareTo(current) > 0;
        } catch (NumberFormatException e) {
            return candidate.compareTo(current) > 0;
        }
    }

    private static int[] parseSemver(String version) {
        // Strip pre-release part for numeric comparison
        String numeric = version.contains("-") ? version.substring(0, version.indexOf('-')) : version;
        String[] parts = numeric.split("\\.", -1);
        int[] result = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {
            result[i] = Integer.parseInt(parts[i].trim());
        }
        return result;
    }

    // ------------------------------------------------------------------
    // Update notice
    // ------------------------------------------------------------------

    private static boolean isStderrInteractive() {
        return System.console() != null;
    }

    /**
     * Write the update notice to stderr.
     * Respects the {@code NO_COLOR} environment variable.
     *
     * @param latestVersion the latest available version
     */
    private void printNotice(String latestVersion) {
        boolean useColor = System.getenv("NO_COLOR") == null;
        String yellow = useColor ? "\u001B[33m" : "";
        String reset = useColor ? "\u001B[0m" : "";

        String tag = "v" + latestVersion;
        String currentTag = "v" + currentVersion;

        PrintStream err = System.err;
        err.println(yellow + "⚠ A new version of OpenToken is available: " + tag
                + " (you have " + currentTag + ")" + reset);
        err.println("   Release notes: https://github.com/TruvetaPublic/OpenToken/releases/tag/" + tag);
        err.println("   Run 'opentoken update' to upgrade, or set " + ENV_DISABLE
                + "=1 to silence this message.");
    }
}
