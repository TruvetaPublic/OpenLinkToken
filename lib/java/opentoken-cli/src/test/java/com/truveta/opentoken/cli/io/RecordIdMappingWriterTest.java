/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.io;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit tests for {@link RecordIdMappingWriter}.
 */
class RecordIdMappingWriterTest {

    @TempDir
    Path tempDir;

    @Test
    void testWriteMapping_createsFileWithHeader() throws Exception {
        Path mappingFile = tempDir.resolve("output.record-id-mapping.csv");

        try (RecordIdMappingWriter writer = new RecordIdMappingWriter(mappingFile.toString())) {
            writer.writeMapping("original-001", "hashed-001");
        }

        assertTrue(Files.exists(mappingFile), "Mapping file should be created");
        List<String> lines = Files.readAllLines(mappingFile);
        assertEquals("original_record_id,hashed_record_id", lines.get(0), "First line must be the CSV header");
    }

    @Test
    void testWriteMapping_containsMappingRows() throws Exception {
        Path mappingFile = tempDir.resolve("output.record-id-mapping.csv");

        try (RecordIdMappingWriter writer = new RecordIdMappingWriter(mappingFile.toString())) {
            writer.writeMapping("record-001", "abc123");
            writer.writeMapping("record-002", "def456");
        }

        List<String> lines = Files.readAllLines(mappingFile);
        assertEquals(3, lines.size(), "File should contain header + 2 data rows");
        assertEquals("record-001,abc123", lines.get(1));
        assertEquals("record-002,def456", lines.get(2));
    }

    @Test
    void testBuildMappingFilePath_stripsExtensionAndAppendsSuffix() {
        assertEquals("path/to/output.record-id-mapping.csv",
                RecordIdMappingWriter.buildMappingFilePath("path/to/output.csv"));
        assertEquals("output.record-id-mapping.csv",
                RecordIdMappingWriter.buildMappingFilePath("output.parquet"));
        assertEquals("noextension.record-id-mapping.csv",
                RecordIdMappingWriter.buildMappingFilePath("noextension"));
    }

    @Test
    void testGetFilePath_returnsConstructorPath() throws Exception {
        Path mappingFile = tempDir.resolve("test.record-id-mapping.csv");
        try (RecordIdMappingWriter writer = new RecordIdMappingWriter(mappingFile.toString())) {
            assertEquals(mappingFile.toString(), writer.getFilePath());
        }
    }

    @Test
    void testWriteMapping_multipleRows() throws Exception {
        Path mappingFile = tempDir.resolve("multi.record-id-mapping.csv");
        int numRows = 50;

        try (RecordIdMappingWriter writer = new RecordIdMappingWriter(mappingFile.toString())) {
            for (int i = 0; i < numRows; i++) {
                writer.writeMapping("original-" + i, "hashed-" + i);
            }
        }

        List<String> lines = Files.readAllLines(mappingFile);
        assertEquals(numRows + 1, lines.size(), "File should contain header + " + numRows + " data rows");
    }
}
