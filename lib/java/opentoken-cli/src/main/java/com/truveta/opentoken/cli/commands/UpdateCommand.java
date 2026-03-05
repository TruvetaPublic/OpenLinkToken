/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.attribute.PosixFilePermission;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.EnumSet;
import java.util.Optional;
import java.util.Scanner;
import java.util.Set;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.truveta.opentoken.Metadata;
import com.truveta.opentoken.cli.util.VersionChecker;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Update command – self-update the OpenToken CLI to the latest release.
 *
 * <p>Downloads, verifies (SHA-256 checksum when available), and replaces the
 * running binary with the specified or latest release from GitHub.
 */
@Command(name = "update", description = "Update OpenToken CLI to the latest release")
public class UpdateCommand implements Callable<Integer> {

    private static final Logger logger = LoggerFactory.getLogger(UpdateCommand.class);

    private static final String GITHUB_API_BASE =
            "https://api.github.com/repos/TruvetaPublic/OpenToken";
    private static final int REQUEST_TIMEOUT_SECONDS = 30;

    @Option(names = { "--version" }, description = "Install a specific release version tag (default: latest)")
    private String targetVersion;

    @Option(names = { "--dry-run" }, description = "Show what would be updated without applying changes")
    private boolean dryRun;

    @Option(names = { "-y", "--yes" }, description = "Skip confirmation prompt")
    private boolean yes;

    @Option(names = { "--help" }, usageHelp = true, description = "Show this help message and exit")
    private boolean helpRequested;

    @Override
    public Integer call() {
        String currentVersion = Metadata.DEFAULT_VERSION;

        // Resolve which release to install
        JsonNode releaseInfo;
        try {
            if (targetVersion != null && !targetVersion.isBlank()) {
                String tag = targetVersion.startsWith("v") ? targetVersion : "v" + targetVersion;
                releaseInfo = fetchReleaseByTag(tag);
            } else {
                releaseInfo = fetchLatestRelease();
            }
        } catch (Exception e) {
            logger.error("Could not fetch release information from GitHub", e);
            System.err.println(
                    "Error: Could not fetch release information from GitHub. "
                    + "Please check your network connection.");
            return 1;
        }

        if (releaseInfo == null) {
            System.err.println(
                    "Error: Could not fetch release information from GitHub. "
                    + "Please check your network connection.");
            return 1;
        }

        String tag = releaseInfo.path("tag_name").asText("");
        String latestVersion = tag.startsWith("v") ? tag.substring(1) : tag;

        // Already up to date?
        if (targetVersion == null && !VersionChecker.isNewer(latestVersion, currentVersion)) {
            System.out.println("OpenToken is already up to date (" + tag + ").");
            return 0;
        }

        // Find the correct asset for this platform
        JsonNode asset = findAsset(releaseInfo);
        if (asset == null) {
            String system = System.getProperty("os.name", "").toLowerCase();
            String arch = System.getProperty("os.arch", "").toLowerCase();
            System.err.println("Error: No suitable release asset found for platform " + system + "/" + arch + ".\n"
                    + "Please download manually from: " + releaseInfo.path("html_url").asText(""));
            return 1;
        }

        String assetName = asset.path("name").asText();
        String assetUrl = asset.path("browser_download_url").asText();
        JsonNode checksumAsset = findChecksumAsset(releaseInfo, assetName);

        if (dryRun) {
            System.out.println("Would update OpenToken from v" + currentVersion + " to " + tag + ".");
            System.out.println("  Asset : " + assetName);
            System.out.println("  URL   : " + assetUrl);
            if (checksumAsset != null) {
                System.out.println("  Checksum: " + checksumAsset.path("name").asText());
            }
            return 0;
        }

        // Confirmation prompt
        if (!yes && System.console() != null) {
            System.out.print("Update OpenToken from v" + currentVersion + " to " + tag + "? [y/N] ");
            System.out.flush();
            try (Scanner scanner = new Scanner(System.in)) {
                String answer = scanner.hasNextLine() ? scanner.nextLine().trim().toLowerCase() : "";
                if (!answer.equals("y") && !answer.equals("yes")) {
                    System.out.println("Update cancelled.");
                    return 0;
                }
            }
        }

        // Download to a temp file
        System.out.println("Downloading " + assetName + "...");
        Path tmpFile;
        try {
            tmpFile = Files.createTempFile("opentoken-update-", getSuffix(assetName));
        } catch (IOException e) {
            logger.error("Could not create temp file", e);
            System.err.println("Error: Could not create temp file: " + e.getMessage());
            return 1;
        }

        try {
            if (!downloadFile(assetUrl, tmpFile)) {
                return 1;
            }

            // Verify checksum if available
            if (checksumAsset != null) {
                System.out.println("Verifying checksum...");
                Optional<String> expected = fetchChecksum(
                        checksumAsset.path("browser_download_url").asText(), assetName);
                if (expected.isPresent()) {
                    String actual = sha256File(tmpFile);
                    if (!actual.equalsIgnoreCase(expected.get())) {
                        System.err.println("Error: Checksum verification failed.\n"
                                + "  Expected: " + expected.get() + "\n"
                                + "  Actual  : " + actual);
                        Files.deleteIfExists(tmpFile);
                        return 1;
                    }
                }
            }

            int replaceResult = replaceBinary(tmpFile, assetName);
            if (replaceResult != 0) {
                return replaceResult;
            }

        } catch (Exception e) {
            logger.error("Update failed", e);
            System.err.println("Error: Update failed: " + e.getMessage());
            return 1;
        } finally {
            try {
                Files.deleteIfExists(tmpFile);
            } catch (IOException e) {
                logger.debug("Could not delete temp file", e);
            }
        }

        System.out.println("OpenToken successfully updated to " + tag + ".");
        return 0;
    }

    // ------------------------------------------------------------------
    // GitHub API helpers
    // ------------------------------------------------------------------

    private JsonNode fetchLatestRelease() throws IOException, InterruptedException {
        return getJson(GITHUB_API_BASE + "/releases/latest");
    }

    private JsonNode fetchReleaseByTag(String tag) throws IOException, InterruptedException {
        return getJson(GITHUB_API_BASE + "/releases/tags/" + tag);
    }

    private JsonNode getJson(String url) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                .build();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("User-Agent", "opentoken-cli")
                .timeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                .GET()
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 200) {
            return null;
        }
        return new ObjectMapper().readTree(response.body());
    }

    // ------------------------------------------------------------------
    // Asset selection
    // ------------------------------------------------------------------

    private JsonNode findAsset(JsonNode releaseInfo) {
        JsonNode assets = releaseInfo.path("assets");
        String system = System.getProperty("os.name", "").toLowerCase();
        String arch = System.getProperty("os.arch", "").toLowerCase();

        // Normalise OS name tokens
        String osToken = system.contains("win") ? "windows"
                : system.contains("mac") ? "macos"
                : "linux";

        // Normalise arch tokens
        String archToken = (arch.equals("amd64") || arch.equals("x86_64")) ? "x86_64"
                : (arch.equals("aarch64") || arch.equals("arm64")) ? "aarch64"
                : arch;

        for (JsonNode asset : assets) {
            String name = asset.path("name").asText("").toLowerCase();
            if (name.endsWith(".sha256") || name.endsWith(".sha256sum")) {
                continue;
            }
            if (name.contains(osToken) && name.contains(archToken)) {
                return asset;
            }
        }

        // Fallback: system-only match
        for (JsonNode asset : assets) {
            String name = asset.path("name").asText("").toLowerCase();
            if (name.endsWith(".sha256") || name.endsWith(".sha256sum")) {
                continue;
            }
            if (name.contains(osToken)) {
                return asset;
            }
        }

        return null;
    }

    private JsonNode findChecksumAsset(JsonNode releaseInfo, String assetName) {
        for (JsonNode asset : releaseInfo.path("assets")) {
            String name = asset.path("name").asText();
            if (name.equals(assetName + ".sha256") || name.equals(assetName + ".sha256sum")) {
                return asset;
            }
        }
        return null;
    }

    // ------------------------------------------------------------------
    // Download and verification
    // ------------------------------------------------------------------

    private boolean downloadFile(String url, Path dest) {
        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                    .build();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("User-Agent", "opentoken-cli")
                    .timeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                    .GET()
                    .build();
            HttpResponse<InputStream> response =
                    client.send(request, HttpResponse.BodyHandlers.ofInputStream());
            if (response.statusCode() != 200) {
                System.err.println("Error: Download failed with HTTP " + response.statusCode());
                return false;
            }
            try (InputStream body = response.body()) {
                Files.copy(body, dest, StandardCopyOption.REPLACE_EXISTING);
            }
            return true;
        } catch (Exception e) {
            System.err.println("Error: Download failed: " + e.getMessage());
            return false;
        }
    }

    private Optional<String> fetchChecksum(String url, String assetName) {
        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                    .build();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("User-Agent", "opentoken-cli")
                    .timeout(Duration.ofSeconds(REQUEST_TIMEOUT_SECONDS))
                    .GET()
                    .build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            for (String line : response.body().split("\n")) {
                String[] parts = line.trim().split("\\s+", 2);
                if (parts.length >= 2 && parts[1].replaceFirst("^\\*", "").equals(assetName)) {
                    return Optional.of(parts[0].toLowerCase());
                }
            }
            return Optional.empty();
        } catch (Exception e) {
            logger.debug("Could not fetch checksum", e);
            return Optional.empty();
        }
    }

    private String sha256File(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[65536];
        try (InputStream in = Files.newInputStream(path)) {
            int read;
            while ((read = in.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
            }
        }
        byte[] hash = digest.digest();
        StringBuilder sb = new StringBuilder(hash.length * 2);
        for (byte b : hash) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    // ------------------------------------------------------------------
    // Binary replacement
    // ------------------------------------------------------------------

    private int replaceBinary(Path src, String assetName) throws IOException {
        // Try to find the 'opentoken' binary on PATH
        Path target = findTargetBinary();

        if (target == null) {
            System.err.println(
                    "Error: Could not locate the opentoken binary to replace.\n"
                    + "Please replace it manually.");
            return 1;
        }

        if (!Files.isWritable(target)) {
            System.err.println(
                    "Error: Insufficient permissions to write to " + target + ".\n"
                    + "Try running with elevated privileges (e.g. sudo) or download manually from:\n"
                    + "  https://github.com/TruvetaPublic/OpenToken/releases");
            return 1;
        }

        Files.copy(src, target, StandardCopyOption.REPLACE_EXISTING);

        // Ensure executable bit (POSIX only; ignored silently on Windows)
        try {
            Set<PosixFilePermission> perms = Files.getPosixFilePermissions(target);
            perms.addAll(EnumSet.of(
                    PosixFilePermission.OWNER_EXECUTE,
                    PosixFilePermission.GROUP_EXECUTE,
                    PosixFilePermission.OTHERS_EXECUTE));
            Files.setPosixFilePermissions(target, perms);
        } catch (UnsupportedOperationException e) {
            // Windows – ignore
        }
        return 0;
    }

    private Path findTargetBinary() {
        String pathEnv = System.getenv("PATH");
        if (pathEnv == null) {
            return null;
        }
        for (String dir : pathEnv.split(System.getProperty("path.separator", ":"))) {
            Path candidate = Path.of(dir, "opentoken");
            if (Files.isRegularFile(candidate)) {
                return candidate;
            }
            Path candidateExe = Path.of(dir, "opentoken.exe");
            if (Files.isRegularFile(candidateExe)) {
                return candidateExe;
            }
        }
        return null;
    }

    private String getSuffix(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot) : "";
    }
}
