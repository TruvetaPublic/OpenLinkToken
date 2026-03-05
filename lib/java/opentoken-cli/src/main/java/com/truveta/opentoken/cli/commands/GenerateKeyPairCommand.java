/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.commands;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.InvalidParameterSpecException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

/**
 * Generate an ECDH key pair and write the keys to {@code ~/.opentoken/}.
 *
 * <p>The private key is written in PEM PKCS#8 format ({@code .private.pem})
 * with {@code 600} permissions. The public key is written in PEM
 * SubjectPublicKeyInfo format ({@code .public.pem}) with {@code 644}
 * permissions. The {@code ~/.opentoken/} directory is created with {@code 700}
 * permissions if it does not already exist.
 */
@Command(
        name = "generate-key-pair",
        description = {
                "Generate an ECDH public/private key pair and write the keys to ~/.opentoken/.",
                "",
                "Private key:  ~/.opentoken/<name>.private.pem  (PEM PKCS#8, permissions 600)",
                "Public key:   ~/.opentoken/<name>.public.pem   (PEM SubjectPublicKeyInfo, permissions 644)",
                "Directory:    ~/.opentoken/                     (created with permissions 700 if absent)"
        }
)
public class GenerateKeyPairCommand implements Callable<Integer> {

    /** Supported ECDH curves mapped to their JCA standard names. */
    private static final List<String> SUPPORTED_CURVES = List.of("P-256", "P-384", "P-521");

    private static final String CURVE_P256_JCA = "secp256r1";
    private static final String CURVE_P384_JCA = "secp384r1";
    private static final String CURVE_P521_JCA = "secp521r1";

    private static final Logger logger = LoggerFactory.getLogger(GenerateKeyPairCommand.class);

    @Option(
            names = { "-c", "--curve" },
            description = "Elliptic curve for key generation. Supported: P-256, P-384, P-521 (default: P-256)",
            defaultValue = "P-256"
    )
    private String curve;

    @Option(
            names = { "-n", "--name" },
            description = "Base name for the key files (default: opentoken-<ISO8601-date>)"
    )
    private String name;

    @Option(
            names = { "--force" },
            description = "Overwrite existing key files if they already exist"
    )
    private boolean force;

    @Option(names = { "--help" }, usageHelp = true, description = "Show this help message and exit")
    private boolean helpRequested;

    @Option(names = { "-V", "--version" }, versionHelp = true, description = "Print version information and exit")
    private boolean versionRequested;

    @Override
    public Integer call() {
        // Resolve default name from current date
        if (name == null || name.isBlank()) {
            name = "opentoken-" + LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE);
        }

        // Validate curve
        if (!SUPPORTED_CURVES.contains(curve)) {
            logger.error("Unsupported curve '{}'. Valid options are: {}", curve, String.join(", ", SUPPORTED_CURVES));
            return 1;
        }

        Path opentokenDir = Paths.get(System.getProperty("user.home"), ".opentoken");
        Path privateKeyPath = opentokenDir.resolve(name + ".private.pem");
        Path publicKeyPath = opentokenDir.resolve(name + ".public.pem");

        // Guard against silent overwrite
        if (!force) {
            if (Files.exists(privateKeyPath) || Files.exists(publicKeyPath)) {
                logger.error(
                        "Key files for '{}' already exist in {}. Use --force to overwrite.",
                        name, opentokenDir);
                return 1;
            }
        }

        try {
            ensureDirectory(opentokenDir);
            KeyPair keyPair = generateKeyPair(curve);
            writePrivateKey(keyPair, privateKeyPath);
            writePublicKey(keyPair, publicKeyPath);
        } catch (Exception e) {
            logger.error("Failed to generate key pair: {}", e.getMessage(), e);
            return 1;
        }

        System.out.println("Private key: " + privateKeyPath.toAbsolutePath());
        System.out.println("Public key:  " + publicKeyPath.toAbsolutePath());
        return 0;
    }

    /**
     * Creates {@code ~/.opentoken/} with {@code 700} permissions if it does not exist.
     *
     * @param dir the directory path to ensure
     * @throws IOException if the directory cannot be created
     */
    private void ensureDirectory(Path dir) throws IOException {
        if (!Files.exists(dir)) {
            try {
                Set<PosixFilePermission> perms = PosixFilePermissions.fromString("rwx------");
                Files.createDirectories(dir);
                Files.setPosixFilePermissions(dir, perms);
            } catch (UnsupportedOperationException e) {
                // Non-POSIX filesystem (e.g., Windows): create directory without setting permissions
                logger.warn("POSIX permissions not supported on this filesystem; directory created without restricted permissions");
                Files.createDirectories(dir);
            }
        }
    }

    /**
     * Generates an EC key pair for the specified curve name.
     *
     * @param curveName one of {@code P-256}, {@code P-384}, or {@code P-521}
     * @return the generated {@link KeyPair}
     * @throws NoSuchAlgorithmException   if the EC algorithm is unavailable
     * @throws InvalidParameterSpecException if the curve spec is invalid
     */
    KeyPair generateKeyPair(String curveName)
            throws NoSuchAlgorithmException, InvalidParameterSpecException {
        String jcaCurve = toJcaCurveName(curveName);
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
        try {
            kpg.initialize(new ECGenParameterSpec(jcaCurve));
        } catch (java.security.InvalidAlgorithmParameterException e) {
            throw new InvalidParameterSpecException("Invalid curve parameter: " + jcaCurve);
        }
        return kpg.generateKeyPair();
    }

    /**
     * Maps an OpenToken curve name to its JCA standard curve name.
     *
     * @param curveName the OpenToken curve name (e.g., {@code P-256})
     * @return the JCA curve name (e.g., {@code secp256r1})
     */
    private String toJcaCurveName(String curveName) {
        return switch (curveName) {
            case "P-256" -> CURVE_P256_JCA;
            case "P-384" -> CURVE_P384_JCA;
            case "P-521" -> CURVE_P521_JCA;
            default -> throw new IllegalArgumentException("Unknown curve: " + curveName);
        };
    }

    /**
     * Writes the private key to the specified path in PEM PKCS#8 format with {@code 600} permissions.
     *
     * @param keyPair   the key pair containing the private key
     * @param path      the target file path
     * @throws IOException if the file cannot be written
     */
    private void writePrivateKey(KeyPair keyPair, Path path) throws IOException {
        byte[] encoded = keyPair.getPrivate().getEncoded();
        String pem = toPem("PRIVATE KEY", encoded);
        writeWithPermissions(path, pem, "rw-------");
    }

    /**
     * Writes the public key to the specified path in PEM SubjectPublicKeyInfo format with {@code 644} permissions.
     *
     * @param keyPair   the key pair containing the public key
     * @param path      the target file path
     * @throws IOException if the file cannot be written
     */
    private void writePublicKey(KeyPair keyPair, Path path) throws IOException {
        byte[] encoded = keyPair.getPublic().getEncoded();
        String pem = toPem("PUBLIC KEY", encoded);
        writeWithPermissions(path, pem, "rw-r--r--");
    }

    /**
     * Encodes DER bytes as a PEM block with the given label.
     *
     * @param label the PEM label (e.g., {@code PRIVATE KEY})
     * @param der   the DER-encoded key bytes
     * @return the PEM string
     */
    String toPem(String label, byte[] der) {
        String base64 = Base64.getMimeEncoder(64, new byte[] { '\n' }).encodeToString(der);
        return "-----BEGIN " + label + "-----\n"
                + base64
                + "\n-----END " + label + "-----\n";
    }

    /**
     * Writes {@code content} to {@code path} and sets POSIX permissions described by {@code permString}.
     *
     * @param path       the target file path
     * @param content    the file content
     * @param permString a POSIX permission string such as {@code "rw-------"}
     * @throws IOException if the file cannot be written or permissions cannot be set
     */
    private void writeWithPermissions(Path path, String content, String permString) throws IOException {
        Files.writeString(path, content, StandardCharsets.UTF_8);
        try {
            Set<PosixFilePermission> perms = PosixFilePermissions.fromString(permString);
            Files.setPosixFilePermissions(path, perms);
        } catch (UnsupportedOperationException e) {
            // Non-POSIX filesystem: write succeeds but permissions cannot be set
            logger.warn("POSIX permissions not supported on this filesystem; file written without restricted permissions");
        }
    }
}
