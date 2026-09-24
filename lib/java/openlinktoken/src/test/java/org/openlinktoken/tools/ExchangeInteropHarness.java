/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tools;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.openlinktoken.EcKeyUtils;
import org.openlinktoken.ExchangeConfig;
import org.openlinktoken.ExchangeJwe;
import org.openlinktoken.ExchangeKem;
import org.openlinktoken.ExchangeKeyBundle;
import org.openlinktoken.crypto.CryptoSuite;

/**
 * Test-only harness for exchanging JSON envelopes with the Python interoperability checks.
 */
public final class ExchangeInteropHarness {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final TypeReference<Map<String, Object>> OBJECT_TYPE = new TypeReference<>() {
    };
    private static final byte[] HASHING_SECRET = "0123456789abcdef0123456789abcdef".getBytes(StandardCharsets.UTF_8);
    private static final byte[] ROTATION_IV = "interop-rotation-iv".getBytes(StandardCharsets.UTF_8);
    private static final String CREATED_AT = "2026-03-12T00:00:00Z";

    /**
     * Prevents instantiation of this command-line harness.
     */
    private ExchangeInteropHarness() {
    }

    /**
     * Builds or decrypts an exchange envelope.
     *
     * @param args {@code build <suite-id> <output-dir>} or
     *        {@code decrypt <suite-id> <envelope.json> <private-key> <result.json>}
     * @throws Exception if an envelope or key cannot be read, written, built, or decrypted
     */
    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected 'build' or 'decrypt' command.");
        }
        switch (args[0]) {
            case "build" -> build(args);
            case "decrypt" -> decrypt(args);
            default -> throw new IllegalArgumentException("Unsupported command: " + args[0]);
        }
    }

    /**
     * Generates a suite-specific envelope and sender private key for Python to decrypt.
     *
     * @param args command-line arguments
     * @throws Exception if an artifact cannot be written
     */
    private static void build(String[] args) throws Exception {
        if (args.length != 3) {
            throw new IllegalArgumentException("Expected: build <suite-id> <output-dir>");
        }

        CryptoSuite suite = CryptoSuite.fromId(args[1]);
        Path outputDirectory = Path.of(args[2]);
        Files.createDirectories(outputDirectory);

        if (suite.getExchangeConfigVersion() == 1) {
            buildLegacyEnvelope(suite, outputDirectory);
        } else {
            buildVersionTwoEnvelope(suite, outputDirectory);
        }
    }

    /**
     * Generates a legacy ECDH envelope using the public v1 exchange API.
     *
     * @param suite the legacy suite
     * @param outputDirectory destination directory
     * @throws Exception if key generation or serialization fails
     */
    private static void buildLegacyEnvelope(CryptoSuite suite, Path outputDirectory) throws Exception {
        var sender = EcKeyUtils.generateKeyPair("P-256");
        var recipient = EcKeyUtils.generateKeyPair("P-256");
        var envelope = ExchangeJwe.buildExchangeEnvelope(
                exchangeName(suite),
                HASHING_SECRET,
                EcKeyUtils.publicKeyToPem(sender.getPublic()),
                EcKeyUtils.publicKeyToPem(recipient.getPublic()),
                "P-256",
                CREATED_AT,
                exchangeId(suite),
                ROTATION_IV,
                3,
                0.05,
                List.of(0.1, -0.2),
                suite);

        writeJson(outputDirectory.resolve("exchange.json"), envelope);
        Files.write(outputDirectory.resolve("sender.private.pem"), EcKeyUtils.privateKeyToPem(sender.getPrivate()));
    }

    /**
     * Generates a pure or hybrid ML-KEM envelope using the public v2 exchange API.
     *
     * @param suite the version-two suite
     * @param outputDirectory destination directory
     * @throws Exception if key generation or serialization fails
     */
    private static void buildVersionTwoEnvelope(CryptoSuite suite, Path outputDirectory) throws Exception {
        var sender = ExchangeKeyBundle.generate(suite);
        var recipient = ExchangeKeyBundle.generate(suite);
        var envelope = ExchangeKem.buildExchangeEnvelopeV2(
                exchangeName(suite),
                HASHING_SECRET,
                sender,
                recipient,
                CREATED_AT,
                exchangeId(suite),
                ROTATION_IV,
                3,
                0.05,
                List.of(0.1, -0.2));

        writeJson(outputDirectory.resolve("exchange.json"), envelope);
        Files.write(outputDirectory.resolve("sender.private.bundle.json"), sender.toJson(true));
    }

    /**
     * Decrypts an envelope and writes only deterministic plaintext and key material.
     * Returns no value; the result is written to the requested output path.
     *
     * @param args command-line arguments
     * @throws Exception if an artifact cannot be read, decrypted, or written
     */
    private static void decrypt(String[] args) throws Exception {
        if (args.length != 5) {
            throw new IllegalArgumentException(
                    "Expected: decrypt <suite-id> <envelope.json> <private-key> <result.json>");
        }

        CryptoSuite suite = CryptoSuite.fromId(args[1]);
        byte[] envelope = Files.readAllBytes(Path.of(args[2]));
        byte[] privateKey = Files.readAllBytes(Path.of(args[3]));
        byte[] plaintext;
        byte[] transportKey = null;
        ExchangeConfig.ResolvedExchangeConfig resolved;

        if (suite.getExchangeConfigVersion() == 1) {
            plaintext = ExchangeJwe.decryptExchangeEnvelope(envelope, privateKey);
            resolved = ExchangeConfig.resolveExchangeConfig(envelope, privateKey);
            transportKey = resolved.transportEncryptionKey();
        } else {
            ExchangeKeyBundle privateBundle = ExchangeKeyBundle.fromJson(privateKey, true);
            ExchangeKem.DecryptionResult result = ExchangeKem.decryptExchangeEnvelopeV2(envelope, privateBundle);
            resolved = ExchangeConfig.resolveExchangeConfig(envelope, privateBundle);
            plaintext = result.getPlaintext();
            transportKey = resolved.transportEncryptionKey();
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("version", suite.getExchangeConfigVersion());
        result.put("cryptoSuite", resolved.cryptoSuite().getSuiteId());
        result.put("payload", JSON.readValue(plaintext, OBJECT_TYPE));
        result.put(
                "transportKey",
                transportKey == null
                        ? null
                        : Base64.getUrlEncoder().withoutPadding().encodeToString(transportKey));
        writeJson(Path.of(args[4]), result);
    }

    /**
     * Writes a JSON-compatible value using UTF-8.
     *
     * @param path destination path
     * @param value value to serialize
     * @throws Exception if serialization or writing fails
     */
    private static void writeJson(Path path, Object value) throws Exception {
        if (path.getParent() != null) {
            Files.createDirectories(path.getParent());
        }
        Files.write(path, JSON.writeValueAsBytes(value));
    }

    /**
     * Returns the stable exchange name shared with the Python fixture.
     *
     * @param suite the crypto suite
     * @return exchange name
     */
    private static String exchangeName(CryptoSuite suite) {
        return "interop-exchange-" + suite.getSuiteId();
    }

    /**
     * Returns the stable exchange identifier shared with the Python fixture.
     *
     * @param suite the crypto suite
     * @return exchange identifier
     */
    private static String exchangeId(CryptoSuite suite) {
        return "interop-" + suite.getSuiteId();
    }
}
