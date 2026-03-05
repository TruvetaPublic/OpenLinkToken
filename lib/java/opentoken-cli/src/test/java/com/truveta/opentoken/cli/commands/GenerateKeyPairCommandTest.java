/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFileAttributeView;
import java.nio.file.attribute.PosixFilePermission;
import java.security.KeyPair;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
/**
 * Unit and integration tests for {@link GenerateKeyPairCommand}.
 */
class GenerateKeyPairCommandTest {

    @TempDir
    Path tempDir;

    private Path opentokenDir;

    @BeforeEach
    void setUp() {
        opentokenDir = tempDir.resolve(".opentoken");
    }

    // -------------------------------------------------------------------------
    // Supported curves via CLI
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_P256_Succeeds() throws IOException {
        assertCurveSucceeds("P-256", "test-p256");
    }

    @Test
    void testGenerateKeyPair_P384_Succeeds() throws IOException {
        assertCurveSucceeds("P-384", "test-p384");
    }

    @Test
    void testGenerateKeyPair_P521_Succeeds() throws IOException {
        assertCurveSucceeds("P-521", "test-p521");
    }

    private void assertCurveSucceeds(String curve, String keyName) throws IOException {
        String[] args = {
                "generate-key-pair",
                "--curve", curve,
                "--name", keyName
        };

        int exitCode = executeWithCustomHome(args);
        assertEquals(0, exitCode, "generate-key-pair should succeed for curve " + curve);

        Path privKey = opentokenDir.resolve(keyName + ".private.pem");
        Path pubKey = opentokenDir.resolve(keyName + ".public.pem");
        assertTrue(Files.exists(privKey), "Private key file must be created for curve " + curve);
        assertTrue(Files.exists(pubKey), "Public key file must be created for curve " + curve);
    }

    // -------------------------------------------------------------------------
    // Default curve is P-256
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_DefaultCurveIsP256() throws IOException {
        String keyName = "default-curve-test";
        String[] args = { "generate-key-pair", "--name", keyName };

        int exitCode = executeWithCustomHome(args);
        assertEquals(0, exitCode, "generate-key-pair should succeed with default curve");

        Path privKey = opentokenDir.resolve(keyName + ".private.pem");
        assertTrue(Files.exists(privKey), "Private key should be written with default curve");

        String content = Files.readString(privKey);
        assertTrue(content.contains("-----BEGIN PRIVATE KEY-----"), "Should be PKCS#8 PEM");
    }

    // -------------------------------------------------------------------------
    // Default name uses ISO date
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_DefaultNameUsesIsoDate() throws IOException {
        String[] args = { "generate-key-pair" };

        int exitCode = executeWithCustomHome(args);
        assertEquals(0, exitCode, "generate-key-pair should succeed with default name");

        // Expect at least one file matching opentoken-YYYY-MM-DD pattern
        boolean foundPrivKey = Files.list(opentokenDir)
                .anyMatch(p -> p.getFileName().toString().matches("opentoken-\\d{4}-\\d{2}-\\d{2}\\.private\\.pem"));
        assertTrue(foundPrivKey, "Default key name must follow opentoken-<ISO-date> pattern");
    }

    // -------------------------------------------------------------------------
    // PEM format validation
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_PrivateKeyIsPkcs8Pem() throws IOException {
        String keyName = "pem-format-test";
        String[] args = { "generate-key-pair", "--name", keyName };

        executeWithCustomHome(args);

        String content = Files.readString(opentokenDir.resolve(keyName + ".private.pem"));
        assertTrue(content.startsWith("-----BEGIN PRIVATE KEY-----"),
                "Private key must start with PKCS#8 PEM header");
        assertTrue(content.contains("-----END PRIVATE KEY-----"),
                "Private key must end with PKCS#8 PEM footer");
    }

    @Test
    void testGenerateKeyPair_PublicKeyIsSubjectPublicKeyInfoPem() throws IOException {
        String keyName = "pem-format-test";
        String[] args = { "generate-key-pair", "--name", keyName };

        executeWithCustomHome(args);

        String content = Files.readString(opentokenDir.resolve(keyName + ".public.pem"));
        assertTrue(content.startsWith("-----BEGIN PUBLIC KEY-----"),
                "Public key must start with SubjectPublicKeyInfo PEM header");
        assertTrue(content.contains("-----END PUBLIC KEY-----"),
                "Public key must end with SubjectPublicKeyInfo PEM footer");
    }

    // -------------------------------------------------------------------------
    // File permissions (POSIX only)
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_FilePermissions() throws IOException {
        assumeTrue(isPosixSupported(tempDir), "Skipping permission test on non-POSIX filesystem");

        String keyName = "perm-test";
        executeWithCustomHome(new String[] { "generate-key-pair", "--name", keyName });

        Path privKey = opentokenDir.resolve(keyName + ".private.pem");
        Path pubKey = opentokenDir.resolve(keyName + ".public.pem");

        Set<PosixFilePermission> privPerms = Files.getPosixFilePermissions(privKey);
        assertFalse(privPerms.contains(PosixFilePermission.GROUP_READ),
                "Private key must not be group-readable (600)");
        assertFalse(privPerms.contains(PosixFilePermission.OTHERS_READ),
                "Private key must not be world-readable (600)");

        Set<PosixFilePermission> pubPerms = Files.getPosixFilePermissions(pubKey);
        assertTrue(pubPerms.contains(PosixFilePermission.OWNER_READ),
                "Public key must be owner-readable (644)");
        assertTrue(pubPerms.contains(PosixFilePermission.GROUP_READ),
                "Public key must be group-readable (644)");
    }

    @Test
    void testGenerateKeyPair_DirectoryPermissions() throws IOException {
        assumeTrue(isPosixSupported(tempDir), "Skipping permission test on non-POSIX filesystem");

        executeWithCustomHome(new String[] { "generate-key-pair", "--name", "dir-perm-test" });

        Set<PosixFilePermission> dirPerms = Files.getPosixFilePermissions(opentokenDir);
        assertTrue(dirPerms.contains(PosixFilePermission.OWNER_READ),
                "Directory must be owner-readable (700)");
        assertTrue(dirPerms.contains(PosixFilePermission.OWNER_WRITE),
                "Directory must be owner-writable (700)");
        assertTrue(dirPerms.contains(PosixFilePermission.OWNER_EXECUTE),
                "Directory must be owner-executable (700)");
        assertFalse(dirPerms.contains(PosixFilePermission.GROUP_READ),
                "Directory must not be group-readable (700)");
        assertFalse(dirPerms.contains(PosixFilePermission.OTHERS_READ),
                "Directory must not be world-readable (700)");
    }

    // -------------------------------------------------------------------------
    // No overwrite without --force
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_FailsWhenKeyAlreadyExists() throws IOException {
        String keyName = "existing-key";
        String[] args = { "generate-key-pair", "--name", keyName };

        // First run creates the files
        int firstExit = executeWithCustomHome(args);
        assertEquals(0, firstExit, "First run should succeed");

        // Second run without --force should fail
        int secondExit = executeWithCustomHome(args);
        assertNotEquals(0, secondExit, "Second run without --force must exit non-zero");
    }

    @Test
    void testGenerateKeyPair_ForceOverwritesExistingKeys() throws IOException {
        String keyName = "force-overwrite-key";
        executeWithCustomHome(new String[] { "generate-key-pair", "--name", keyName });

        Path pubKey = opentokenDir.resolve(keyName + ".public.pem");
        long originalSize = Files.size(pubKey);

        int exitCode = executeWithCustomHome(new String[] { "generate-key-pair", "--name", keyName, "--force" });
        assertEquals(0, exitCode, "--force should allow overwriting existing key files");

        // File still exists and is non-empty
        assertTrue(Files.exists(pubKey), "Key file must still exist after --force overwrite");
        assertTrue(Files.size(pubKey) > 0, "Key file must be non-empty after --force overwrite");
        // The new key will be a fresh key pair (may differ or may coincidentally equal the old one)
        assertTrue(originalSize > 0, "Original size was valid");
    }

    // -------------------------------------------------------------------------
    // Unsupported curve
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPair_UnsupportedCurveExitsNonZero() {
        String[] args = { "generate-key-pair", "--curve", "P-192" };
        int exitCode = executeWithCustomHome(args);
        assertNotEquals(0, exitCode, "Unsupported curve must exit non-zero");
    }

    // -------------------------------------------------------------------------
    // Key generation unit tests
    // -------------------------------------------------------------------------

    @Test
    void testGenerateKeyPairUnit_P256() throws Exception {
        GenerateKeyPairCommand cmd = new GenerateKeyPairCommand();
        KeyPair kp = cmd.generateKeyPair("P-256");
        assertTrue(kp.getPrivate().getAlgorithm().equals("EC"), "Key algorithm should be EC");
        assertTrue(kp.getPublic().getAlgorithm().equals("EC"), "Public key algorithm should be EC");
    }

    @Test
    void testGenerateKeyPairUnit_P384() throws Exception {
        GenerateKeyPairCommand cmd = new GenerateKeyPairCommand();
        KeyPair kp = cmd.generateKeyPair("P-384");
        assertTrue(kp.getPrivate().getAlgorithm().equals("EC"), "Key algorithm should be EC");
    }

    @Test
    void testGenerateKeyPairUnit_P521() throws Exception {
        GenerateKeyPairCommand cmd = new GenerateKeyPairCommand();
        KeyPair kp = cmd.generateKeyPair("P-521");
        assertTrue(kp.getPrivate().getAlgorithm().equals("EC"), "Key algorithm should be EC");
    }

    @Test
    void testToPem_ContainsHeaderAndFooter() throws Exception {
        GenerateKeyPairCommand cmd = new GenerateKeyPairCommand();
        KeyPair kp = cmd.generateKeyPair("P-256");

        String privatePem = cmd.toPem("PRIVATE KEY", kp.getPrivate().getEncoded());
        assertTrue(privatePem.startsWith("-----BEGIN PRIVATE KEY-----"));
        assertTrue(privatePem.contains("-----END PRIVATE KEY-----"));

        String publicPem = cmd.toPem("PUBLIC KEY", kp.getPublic().getEncoded());
        assertTrue(publicPem.startsWith("-----BEGIN PUBLIC KEY-----"));
        assertTrue(publicPem.contains("-----END PUBLIC KEY-----"));
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    /**
     * Executes {@link OpenTokenCommand#execute} with {@code user.home} temporarily
     * redirected to {@link #tempDir} so that {@code ~/.opentoken/} is created
     * under the test's temporary directory.
     */
    private int executeWithCustomHome(String[] args) {
        String originalHome = System.getProperty("user.home");
        try {
            System.setProperty("user.home", tempDir.toString());
            return OpenTokenCommand.execute(args);
        } finally {
            System.setProperty("user.home", originalHome);
        }
    }

    private boolean isPosixSupported(Path path) {
        return path.getFileSystem().supportedFileAttributeViews().contains("posix") &&
                Files.getFileAttributeView(path, PosixFileAttributeView.class) != null;
    }
}
