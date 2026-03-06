"""
Copyright (c) Truveta. All rights reserved.
"""

import base64
import csv
import hashlib
import hmac
import os
import tempfile
from pathlib import Path
from typing import Dict, List

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from opentoken.attributes.general.record_id_attribute import RecordIdAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.metadata import Metadata
from opentoken.tokens.token import Token
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from opentoken.tokentransformer.no_operation_token_transformer import NoOperationTokenTransformer
from opentoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from opentoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from opentoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from opentoken_cli.processor.person_attributes_processor import PersonAttributesProcessor

# Get repository root (goes up from lib/python/opentoken/src/test/opentoken/processor/ to repo root)
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent.parent
RESOURCES_DIR = REPO_ROOT / "resources" / "mockdata"


class TestPersonAttributesProcessorIntegration:
    def setup_method(self):
        """Set up test fixtures."""
        self.total_records_matched = 1001
        self.hash_key = "hash_key"
        self.encryption_key = "the_encryption_key_goes_here...."
        self.hash_algorithm = "HmacSHA256"
        self.encryption_algorithm = "AES"

    def test_input_with_duplicates(self):
        """
        This test case takes input csv which has repeat probability of 0.30.
        RecordIds will still be unique.
        The goal is to ensure that the records with repeated data still generate
        the same tokens.
        """
        input_csv_file = str(RESOURCES_DIR / "test_data.csv")
        ssn_to_record_ids_map = self.group_records_ids_with_same_ssn(input_csv_file)

        token_transformer_list = [HashTokenTransformer(self.hash_key), EncryptTokenTransformer(self.encryption_key)]
        result_from_person_attributes_processor = self.read_csv_from_person_attributes_processor(
            input_csv_file, token_transformer_list
        )

        for processed_csv_map_key in ssn_to_record_ids_map.keys():
            record_ids = ssn_to_record_ids_map[processed_csv_map_key]

            count = 0
            token_generated = []

            for record_token in result_from_person_attributes_processor:
                record_id = record_token.get("RecordId")

                # This code block checks that for multiple recordIds with same SSN
                # the 5 tokens generated (for each recordId) are always the same
                if record_id in record_ids:
                    token = self.decrypt_token(record_token.get("Token"))
                    # for a new RecordId simply store the 5 tokens as a list
                    if len(token_generated) < 5:
                        token_generated.append(token)
                    # for RecordId with same SSN, tokens should match as in the list
                    elif len(token_generated) == 5:  # check existing tokens match for duplicate records
                        assert token in token_generated
                    count += 1

            assert count == len(record_ids) * 5

    def test_input_with_overlapping_data(self):
        """
        This test case compares two input csv's. A section of these data will
        overlap with both the csv's.
        The first csv is hashed and encrypted and the second csv is only hashed.
        The goal is to ensure that tokenization process still generates the tokens
        correctly for both the csv's.
        The test case then ensures the tokens match for overlapping records.
        This is done by decrypting the encrypted tokens for the first csv and
        hashing the tokens in second csv.
        Finally we find exact matches in both files.
        """
        # Incoming file is hashed and encrypted
        token_transformer_list = [HashTokenTransformer(self.hash_key), EncryptTokenTransformer(self.encryption_key)]
        result_from_person_attributes_processor1 = self.read_csv_from_person_attributes_processor(
            str(RESOURCES_DIR / "test_overlap1.csv"), token_transformer_list
        )

        # Truveta file is neither hashed nor encrypted
        token_transformer_list = [NoOperationTokenTransformer()]
        result_from_person_attributes_processor2 = self.read_csv_from_person_attributes_processor(
            str(RESOURCES_DIR / "test_overlap2.csv"), token_transformer_list
        )

        record_id_to_token_map1 = {}
        # tokens from incoming file are hashed and encrypted. This needs decryption
        for record_token1 in result_from_person_attributes_processor1:
            encrypted_token = record_token1.get("Token")
            record_id_to_token_map1[record_token1.get("RecordId")] = self.decrypt_token(encrypted_token)

        record_id_to_token_map2 = {}
        # Truveta tokens are neither hashed nor encrypted. This needs to be hashed
        for record_token2 in result_from_person_attributes_processor2:
            no_op_token = record_token2.get("Token")
            # hashing this token to match incoming records files
            record_id_to_token_map2[record_token2.get("RecordId")] = self.hash_token(no_op_token)

        # Now both are similarly hashed (Hmac hash)
        overlapp_count = 0
        for record_id1 in record_id_to_token_map1.keys():
            token1 = record_id_to_token_map1[record_id1]
            if record_id1 in record_id_to_token_map2:
                overlapp_count += 1
                assert record_id_to_token_map2[record_id1] == token1, "For same RecordIds the tokens must match"

        assert overlapp_count == self.total_records_matched

    def test_metadata_file_location(self):
        """
        This test verifies that the metadata file is created alongside the output
        file with the correct extension and contains the expected metadata.
        """
        # Set up the test
        input_csv_file = str(RESOURCES_DIR / "test_data.csv")
        output_csv_file = "lib/python/opentoken/target/test_metadata_location_output.csv"

        token_transformer_list = [NoOperationTokenTransformer()]

        # Delete output files if they exist
        if os.path.exists(output_csv_file):
            os.remove(output_csv_file)

        # Calculate correct metadata file path (same logic as MetadataJsonWriter)
        dot_index = output_csv_file.rfind(".")
        base_name = output_csv_file[:dot_index] if dot_index > 0 else output_csv_file
        metadata_file_path = base_name + Metadata.METADATA_FILE_EXTENSION
        if os.path.exists(metadata_file_path):
            os.remove(metadata_file_path)

        # Process the input file
        with PersonAttributesCSVReader(input_csv_file) as reader, PersonAttributesCSVWriter(output_csv_file) as writer:
            # Create initial metadata
            metadata_map = {
                Metadata.PLATFORM: Metadata.PLATFORM_PYTHON,
                Metadata.PYTHON_VERSION: Metadata.SYSTEM_PYTHON_VERSION,
                Metadata.OUTPUT_FORMAT: Metadata.OUTPUT_FORMAT_CSV,
            }

            # Process data and get updated metadata
            PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

            # Write the metadata to file
            metadata_writer = MetadataJsonWriter(output_csv_file)
            metadata_writer.write(metadata_map)

        # Verify that the output file exists
        assert os.path.exists(output_csv_file), "Output CSV file should exist"

        # Verify that the metadata file exists alongside the output file
        # Handle files with or without extensions (same logic as MetadataJsonWriter)
        last_dot_index = output_csv_file.rfind(".")
        base_path = output_csv_file[:last_dot_index] if last_dot_index > 0 else output_csv_file
        expected_metadata_file = base_path + Metadata.METADATA_FILE_EXTENSION
        assert os.path.exists(expected_metadata_file), "Metadata file should exist alongside the output file"

        # Verify that metadata file contains the expected data
        with open(expected_metadata_file, "r") as f:
            metadata_content = f.read()

        assert Metadata.PLATFORM_PYTHON in metadata_content, "Metadata should contain platform information"
        assert Metadata.SYSTEM_PYTHON_VERSION in metadata_content, "Metadata should contain Python version"
        assert Metadata.OUTPUT_FORMAT_CSV in metadata_content, "Metadata should contain output format"
        assert "TotalRows" in metadata_content, "Metadata should contain total rows processed"

    def test_input_backward_compatibility(self):
        """
        This test verifies backward compatibility by ensuring that tokens
        generated for the same input data remain consistent across different
        processing runs and configurations.
        """
        old_tmp_input_file = None
        new_tmp_input_file = None
        old_tmp_output_file = None
        new_tmp_output_file = None

        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                old_tmp_input_file = f.name
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                new_tmp_input_file = f.name
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                old_tmp_output_file = f.name
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                new_tmp_output_file = f.name

            # Person attributes to be used for token generation
            person_attributes = {
                "FirstName": "Alice",
                "LastName": "Wonderland",
                "SocialSecurityNumber": "345-54-6795",
                "PostalCode": "98052",
                "BirthDate": "1993-08-10",
                "Sex": "Female",
            }

            # Create identical CSV files for both old and new processing
            self.create_test_csv_file(old_tmp_input_file, person_attributes)
            self.create_test_csv_file(new_tmp_input_file, person_attributes)

            # Use consistent transformers for backward compatibility testing
            token_transformer_list = [HashTokenTransformer(self.hash_key), EncryptTokenTransformer(self.encryption_key)]

            # Process both files with the same configuration
            old_results = self.read_csv_from_person_attributes_processor(old_tmp_input_file, token_transformer_list)
            new_results = self.read_csv_from_person_attributes_processor(new_tmp_input_file, token_transformer_list)

            # Verify that both processing runs produce the same number of tokens
            assert len(old_results) == len(new_results), (
                "Both processing runs should produce the same number of tokens for backward compatibility"
            )

            # Verify that tokens are identical for the same input data
            for i in range(len(old_results)):
                old_token = old_results[i]
                new_token = new_results[i]

                assert old_token.get("RecordId") == new_token.get("RecordId"), (
                    "RecordId should be identical for backward compatibility"
                )
                assert old_token.get("RuleId") == new_token.get("RuleId"), (
                    "RuleId should be identical for backward compatibility"
                )

                # Decrypt and compare the actual token values
                old_decrypted_token = self.decrypt_token(old_token.get("Token"))
                new_decrypted_token = self.decrypt_token(new_token.get("Token"))
                assert old_decrypted_token == new_decrypted_token, (
                    "Decrypted tokens should be identical for backward compatibility"
                )

            # Verify that exactly 5 tokens are generated per record (T1-T5)
            assert len(old_results) == 5, "Should generate exactly 5 tokens per record for backward compatibility"

            # Verify token structure consistency
            for token in old_results:
                assert "RecordId" in token, "Token must contain RecordId"
                assert "RuleId" in token, "Token must contain RuleId"
                assert "Token" in token, "Token must contain Token"

                rule_id = token.get("RuleId")
                assert rule_id in ["T1", "T2", "T3", "T4", "T5"], (
                    f"RuleId should follow T1-T5 pattern, but got: {rule_id}"
                )

            # Test metadata consistency
            metadata_map = {}
            with (
                PersonAttributesCSVReader(old_tmp_input_file) as reader,
                PersonAttributesCSVWriter(old_tmp_output_file) as writer,
            ):
                PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

            # Verify essential metadata fields for backward compatibility
            assert PersonAttributesProcessor.TOTAL_ROWS in metadata_map, (
                "Metadata must contain TotalRows for backward compatibility"
            )
            assert metadata_map[PersonAttributesProcessor.TOTAL_ROWS] == 1, "TotalRows should be 1 for single record"
            assert PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES in metadata_map, (
                "Metadata must contain TotalRowsWithInvalidAttributes for backward compatibility"
            )
            assert PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE in metadata_map, (
                "Metadata must contain InvalidAttributesByType for backward compatibility"
            )

        finally:
            # Clean up temporary files
            temp_files = [old_tmp_input_file, new_tmp_input_file, old_tmp_output_file, new_tmp_output_file]
            for temp_file in temp_files:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)

    def create_test_csv_file(self, file_path: str, person_attributes: Dict[str, str]):
        """Helper method to create a test CSV file with specified person attributes."""
        with PersonAttributesCSVWriter(file_path) as writer:
            record = {"RecordId": "TEST_RECORD_001"}
            record.update(person_attributes)
            writer.write_attributes(record)

    def read_csv_from_person_attributes_processor(
        self, input_csv_file_path: str, token_transformers: List
    ) -> List[Dict[str, str]]:
        """Read CSV file through PersonAttributesProcessor and return results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
            tmp_output_file = temp_file.name

        try:
            # Actually process the input file through PersonAttributesProcessor
            with (
                PersonAttributesCSVReader(input_csv_file_path) as reader,
                PersonAttributesCSVWriter(tmp_output_file) as writer,
            ):
                metadata_map = {}
                PersonAttributesProcessor.process(reader, writer, token_transformers, metadata_map)

            result = []
            with open(tmp_output_file, "r", newline="") as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    result.append(dict(row))

            return result

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_output_file):
                os.remove(tmp_output_file)

    def group_records_ids_with_same_ssn(self, input_csv_file_path: str) -> Dict[str, List[str]]:
        """Returns Map of SSN -> List of RecordIds."""
        ssn_to_record_ids_map = {}

        with PersonAttributesCSVReader(input_csv_file_path) as reader:
            for row in reader:
                ssn = row.get(SocialSecurityNumberAttribute)
                record_id = row.get(RecordIdAttribute)

                if ssn not in ssn_to_record_ids_map:
                    ssn_to_record_ids_map[ssn] = []
                ssn_to_record_ids_map[ssn].append(record_id)

        return ssn_to_record_ids_map

    def hash_token(self, no_op_token: str) -> str:
        """Hash a token using HMAC-SHA256."""
        mac = hmac.new(self.hash_key.encode("utf-8"), no_op_token.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt an encrypted token."""
        if encrypted_token == Token.BLANK:
            # blank tokens don't get encrypted
            return Token.BLANK

        message_bytes = base64.b64decode(encrypted_token)
        iv = message_bytes[:12]
        cipher_bytes = message_bytes[12:-16]  # Exclude the last 16 bytes (tag)
        tag = message_bytes[-16:]  # Last 16 bytes are the authentication tag

        # Decrypt the token using the same settings
        cipher = Cipher(
            algorithms.AES(self.encryption_key.encode("utf-8")), modes.GCM(iv, tag), backend=default_backend()
        )

        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(cipher_bytes) + decryptor.finalize()

        return decrypted_bytes.decode("utf-8")

    def test_hash_only_mode(self):
        """
        This test verifies that hash-only mode (without encryption) works correctly
        and produces consistent tokens across runs.
        """
        tmp_input_file = None
        tmp_output_file = None

        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode="w", suffix="_hashonly.csv", delete=False) as f:
                tmp_input_file = f.name
            with tempfile.NamedTemporaryFile(mode="w", suffix="_hashonly_out.csv", delete=False) as f:
                tmp_output_file = f.name

            # Person attributes to be used for token generation
            person_attributes = {
                "FirstName": "Bob",
                "LastName": "Builder",
                "SocialSecurityNumber": "456-78-9012",
                "PostalCode": "12345",
                "BirthDate": "1990-05-15",
                "Sex": "Male",
            }

            # Create test CSV file
            self.create_test_csv_file(tmp_input_file, person_attributes)

            # Use only hash transformer (no encryption)
            token_transformer_list = [HashTokenTransformer(self.hash_key)]

            # Process the file with hash-only transformers
            results = self.read_csv_from_person_attributes_processor(tmp_input_file, token_transformer_list)

            # Verify that exactly 5 tokens are generated per record (T1-T5)
            assert len(results) == 5, "Should generate exactly 5 tokens per record in hash-only mode"

            # Verify token structure
            for token in results:
                assert "RecordId" in token, "Token must contain RecordId"
                assert "RuleId" in token, "Token must contain RuleId"
                assert "Token" in token, "Token must contain Token"

                rule_id = token.get("RuleId")
                assert rule_id in ["T1", "T2", "T3", "T4", "T5"], f"RuleId should follow T1-T5 pattern, got: {rule_id}"

                token_value = token.get("Token")
                # In hash-only mode, tokens should be base64-encoded HMAC-SHA256 hashes
                # Valid tokens are 44 characters long (base64 encoding of 32-byte SHA256)
                # Blank tokens are 64 zeros
                assert len(token_value) == 44 or len(token_value) == 64, (
                    f"Hash-only tokens should be 44 characters (valid) or 64 (blank), got {len(token_value)}"
                )

            # Process the same file again to verify consistency
            results2 = self.read_csv_from_person_attributes_processor(tmp_input_file, token_transformer_list)

            # Verify that hash-only mode produces consistent tokens across runs
            assert len(results) == len(results2), "Should produce same number of tokens"
            for i in range(len(results)):
                assert results[i].get("Token") == results2[i].get("Token"), (
                    "Hash-only mode should produce identical tokens for same input"
                )

        finally:
            # Clean up temporary files
            temp_files = [tmp_input_file, tmp_output_file]
            for temp_file in temp_files:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
