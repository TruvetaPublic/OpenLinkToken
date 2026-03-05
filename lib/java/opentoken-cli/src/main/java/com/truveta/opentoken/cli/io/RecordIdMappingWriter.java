/**
 * Copyright (c) Truveta. All rights reserved.
 */
package com.truveta.opentoken.cli.io;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Writes a record-ID mapping CSV file containing two columns:
 * {@code original_record_id} and {@code hashed_record_id}.
 *
 * <p>The file is used when {@code --hash-record-ids} is specified on the
 * {@code tokenize} or {@code package} subcommands, so that callers can
 * reconcile hashed output back to their source records.
 */
public class RecordIdMappingWriter implements AutoCloseable {

    public static final String ORIGINAL_RECORD_ID = "original_record_id";
    public static final String HASHED_RECORD_ID = "hashed_record_id";
    public static final String MAPPING_FILE_SUFFIX = ".record-id-mapping.csv";

    private static final Logger logger = LoggerFactory.getLogger(RecordIdMappingWriter.class);

    private final BufferedWriter fileWriter;
    private final CSVPrinter csvPrinter;
    private final String filePath;

    /**
     * Constructs a RecordIdMappingWriter for the given file path.
     *
     * @param filePath path of the mapping CSV file to create
     * @throws IOException if the file cannot be opened for writing
     */
    public RecordIdMappingWriter(String filePath) throws IOException {
        this.filePath = filePath;
        fileWriter = new BufferedWriter(new FileWriter(filePath));
        CSVFormat format = CSVFormat.Builder.create(CSVFormat.DEFAULT)
                .setRecordSeparator('\n')
                .setHeader(ORIGINAL_RECORD_ID, HASHED_RECORD_ID)
                .get();
        csvPrinter = new CSVPrinter(fileWriter, format);
    }

    /**
     * Writes a mapping row to the CSV file.
     *
     * @param originalRecordId the original record ID
     * @param hashedRecordId   the SHA-256 hash of the record ID
     * @throws IOException if an I/O error occurs
     */
    public void writeMapping(String originalRecordId, String hashedRecordId) throws IOException {
        csvPrinter.printRecord(originalRecordId, hashedRecordId);
    }

    /**
     * Returns the absolute path of the mapping file.
     *
     * @return file path
     */
    public String getFilePath() {
        return filePath;
    }

    /**
     * Builds the mapping file path from an output file path by stripping the
     * file extension and appending {@value #MAPPING_FILE_SUFFIX}.
     *
     * @param outputFilePath the token output file path
     * @return the corresponding mapping file path
     */
    public static String buildMappingFilePath(String outputFilePath) {
        int lastDotIndex = outputFilePath.lastIndexOf('.');
        String basePath = lastDotIndex > 0 ? outputFilePath.substring(0, lastDotIndex) : outputFilePath;
        return basePath + MAPPING_FILE_SUFFIX;
    }

    @Override
    public void close() throws IOException {
        try {
            csvPrinter.close();
        } catch (IOException e) {
            logger.warn("Error closing CSV printer for mapping file", e);
        }
        fileWriter.close();
    }
}
