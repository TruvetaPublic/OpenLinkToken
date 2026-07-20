# SPDX-License-Identifier: MIT

import logging
from unittest.mock import Mock, call

import pytest

from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from openlinktoken.metadata import Metadata
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.person_attributes_reader import PersonAttributesReader
from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter
from openlinktoken_cli.processor.person_attributes_processor import PersonAttributesProcessor
from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenizationConfig,
    TokenRuleEntry,
)


def _complete_field_id_row() -> dict[str, str]:
    return {
        "RecordId": "A-1001",
        "FirstName": "Alice",
        "LastName": "Wonderland",
        "BirthDate": "1993-08-10",
        "Sex": "F",
        "SocialSecurityNumber": "345-54-6795",
        "PostalCode": "98052",
    }


def _complete_legacy_row() -> dict[type, str]:
    return {
        RecordIdAttribute: "A-1001",
        FirstNameAttribute: "Alice",
        LastNameAttribute: "Wonderland",
        BirthDateAttribute: "1993-08-10",
        SexAttribute: "F",
        SocialSecurityNumberAttribute: "345-54-6795",
        PostalCodeAttribute: "98052",
    }


class LegacyRecordIdAttribute(RecordIdAttribute):
    """Custom record ID attribute used by a legacy reader."""


def _written_payloads(writer: Mock) -> list[dict[str, str]]:
    return [write_call.args[0] for write_call in writer.write_attributes.call_args_list]


class TestPersonAttributesProcessor:
    """Test cases for PersonAttributesProcessor."""

    def test_process_happy_path(self):
        """Test process happy path."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        data = {"RecordId": "TestRecordId", "FirstName": "John", "LastName": "Spencer"}

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))

        metadata_map = Metadata().initialize()
        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Verify writer was called 5 times (5 tokens generated)
        assert writer.write_attributes.call_count == 5

        # Verify metadata was populated
        assert len(metadata_map) > 0, "Metadata map should not be empty after processing"
        assert PersonAttributesProcessor.TOTAL_ROWS in metadata_map, "Metadata should contain totalRows key"

    def test_process_io_exception_writing_attributes(self):
        """Test process with IOException writing attributes."""
        token_transformer_list = [Mock(spec=TokenTransformer)]
        data = {"RecordId": "TestRecordId", "FirstName": "John", "LastName": "Spencer"}

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))

        # Configure writer to raise IOError (Python equivalent of IOException)
        writer.write_attributes.side_effect = IOError("Test Exception")

        metadata_map = Metadata().initialize()

        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Verify writer was called at least once
        assert writer.write_attributes.call_count >= 1

        # Verify metadata was populated
        assert len(metadata_map) > 0, "Metadata map should not be empty after processing"
        assert "TotalRows" in metadata_map, "Metadata should contain totalRows key"

    def test_metadata_map_contains_correct_values(self):
        """Test metadata map contains correct values."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        data = {"RecordId": "TestRecordId", "FirstName": "John", "LastName": "Spencer"}

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))

        metadata_map = Metadata().initialize()

        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Check that the metadata map contains all expected keys with correct values
        assert PersonAttributesProcessor.TOTAL_ROWS in metadata_map, "Metadata should contain totalRows key"
        assert PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES in metadata_map, (
            "Metadata should contain totalRowsWithInvalidAttributes key"
        )
        assert PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE in metadata_map, (
            "Metadata should contain invalidAttributesByType key"
        )

        # Verify values
        assert metadata_map[PersonAttributesProcessor.TOTAL_ROWS] == 1, "Total rows should be 1"
        assert metadata_map[PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES] == 0, (
            "Total rows with invalid attributes should be 0"
        )
        assert PersonAttributesProcessor.BLANK_TOKENS_BY_RULE in metadata_map, (
            "Metadata should contain blankTokensByRule key"
        )

        # The invalid attributes map should contain all attributes with zero counts
        invalid_attributes_map = metadata_map[PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE]
        assert len(invalid_attributes_map) > 0, "Invalid attributes map should contain all attributes initialized to 0"

        # Verify all invalid attribute values are 0 (no invalid attributes in this test)
        for count in invalid_attributes_map.values():
            assert count == 0, "All attribute counts should be 0 with valid data"

        # Verify blank tokens map contains all token rules
        blank_tokens_map = metadata_map[PersonAttributesProcessor.BLANK_TOKENS_BY_RULE]
        assert len(blank_tokens_map) > 0, "Blank tokens map should contain all token rules initialized to 0"

        # Note: This test data (FirstName, LastName only) will generate blank tokens
        # because required attributes like Sex, BirthDate, SSN, PostalCode are missing
        # So we just verify that the map is present and contains entries
        assert len(blank_tokens_map) > 0, "Blank tokens map should have entries for all token rules"

    def test_metadata_map_happy_path_all_attributes_present(self):
        """Test metadata map in happy path with all required attributes present."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        # Provide all required attributes so no blank tokens are generated
        data = {
            "RecordId": "TestRecordId",
            "FirstName": "John",
            "LastName": "Spencer",
            "SocialSecurityNumber": "234-56-7890",
            "BirthDate": "1990-01-15",
            "Sex": "Male",
            "PostalCode": "98052",
        }

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))

        metadata_map = Metadata().initialize()

        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Verify invalid attributes map contains all attributes with zero counts (happy path)
        invalid_attributes_map = metadata_map[PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE]
        assert len(invalid_attributes_map) > 0, "Invalid attributes map should contain all attributes initialized to 0"

        # Verify all invalid attribute values are 0 in the happy path
        for count in invalid_attributes_map.values():
            assert count == 0, "All attribute counts should be 0 in happy path"

        # Verify blank tokens map contains all token rules with zero counts (happy path)
        blank_tokens_map = metadata_map[PersonAttributesProcessor.BLANK_TOKENS_BY_RULE]
        assert len(blank_tokens_map) > 0, "Blank tokens map should contain all token rules initialized to 0"

        # Verify all blank token counts are 0 in the happy path (all required attributes present)
        for count in blank_tokens_map.values():
            assert count == 0, "All token rule counts should be 0 in happy path"

    def test_metadata_map_multiple_rows(self):
        """Test metadata map multiple rows."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]

        # Create three data records
        data1 = {"RecordId": "TestRecordId1", "FirstName": "John", "LastName": "Spencer"}
        data2 = {"RecordId": "TestRecordId2", "FirstName": "Jane", "LastName": "Doe"}
        data3 = {"RecordId": "TestRecordId3", "FirstName": "Alex", "LastName": "Smith"}

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data1, data2, data3]))

        metadata_map = Metadata().initialize()

        # Execute
        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Verify
        assert metadata_map[PersonAttributesProcessor.TOTAL_ROWS] == 3, "Total rows should be 3"
        assert metadata_map[PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES] == 0, (
            "Total rows with invalid attributes should be 0"
        )

    def test_metadata_map_preserves_existing_entries(self):
        """Test metadata map preserves existing entries."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        data = {"RecordId": "TestRecordId", "FirstName": "John", "LastName": "Spencer"}

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))

        metadata_map = Metadata().initialize()
        metadata_map["ExistingKey1"] = "ExistingValue1"
        metadata_map["ExistingKey2"] = "ExistingValue2"

        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Verify original entries are preserved
        assert "ExistingKey1" in metadata_map, "Metadata should preserve existing key1"
        assert "ExistingKey2" in metadata_map, "Metadata should preserve existing key2"
        assert metadata_map["ExistingKey1"] == "ExistingValue1", "Value for existing key1 should be preserved"
        assert metadata_map["ExistingKey2"] == "ExistingValue2", "Value for existing key2 should be preserved"

        # And new entries are added
        assert "TotalRows" in metadata_map, "Metadata should contain totalRows key"

    def test_process_with_custom_token_definition(self):
        """Processes records using a runtime-defined token definition from config."""
        config = TokenizationConfig(
            attributes={
                "given_nm": AttributeMappingEntry(field="FirstName", type="GivenName"),
                "family_nm": AttributeMappingEntry(field="FamilyName", type="LastName"),
            },
            token_rules={
                "T1": [
                    TokenRuleEntry(field="FamilyName", expression="T|U"),
                    TokenRuleEntry(field="FirstName", expression="T|S(0,1)|U"),
                ]
            },
        )
        resolver = ConfiguredAttributeResolver(config)
        token_definition = DynamicTokenDefinition(config, resolver)

        row = {
            "RecordId": "TestRecordId",
            "FirstName": "John",
            "FamilyName": "Spencer",
        }

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([row]))
        metadata_map = Metadata().initialize()

        summary = PersonAttributesProcessor.process(
            reader,
            writer,
            [],
            metadata_map,
            token_definition=token_definition,
        )

        assert summary.total_rows == 1
        assert writer.write_attributes.call_count == 1
        assert summary.blank_tokens_by_rule["T1"] == 0

    def test_process_tracks_unknown_invalid_attribute_name_without_crashing(self):
        """Handles invalid attribute names that were not pre-initialized in metadata maps."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        # Invalid birth date should surface as Date/BirthDate depending on attribute implementation.
        data = {
            "RecordId": "TestRecordId",
            "FirstName": "John",
            "LastName": "Spencer",
            "SocialSecurityNumber": "234-56-7890",
            "BirthDate": "",
            "Sex": "Male",
            "PostalCode": "98052",
        }

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))
        metadata_map = Metadata().initialize()

        summary = PersonAttributesProcessor.process(
            reader,
            writer,
            token_transformer_list,
            metadata_map,
            token_definition=TokenDefinition(),
        )

        assert summary.total_rows == 1
        assert summary.total_rows_with_invalid_attributes == 1

    def test_process_legacy_row_matches_field_id_writer_payloads(self):
        """Legacy class-keyed rows should emit the same tokens and record IDs as field-ID rows."""
        field_id_reader = Mock(spec=PersonAttributesReader)
        field_id_writer = Mock(spec=PersonAttributesWriter)
        field_id_reader.__iter__ = Mock(return_value=iter([_complete_field_id_row()]))

        legacy_reader = Mock(spec=PersonAttributesReader)
        legacy_writer = Mock(spec=PersonAttributesWriter)
        legacy_reader.__iter__ = Mock(return_value=iter([_complete_legacy_row()]))

        PersonAttributesProcessor.process(field_id_reader, field_id_writer, [], Metadata().initialize())
        PersonAttributesProcessor.process(legacy_reader, legacy_writer, [], Metadata().initialize())

        expected_payloads = _written_payloads(field_id_writer)

        assert legacy_writer.write_attributes.call_args_list == [call(payload) for payload in expected_payloads]
        assert {payload["RecordId"] for payload in _written_payloads(legacy_writer)} == {"A-1001"}

    def test_process_legacy_record_id_attribute_subclass_preserves_record_id(self):
        """Legacy rows keyed by a RecordIdAttribute subclass preserve their supplied ID."""
        row = {
            LegacyRecordIdAttribute: "legacy-record-id",
            FirstNameAttribute: "Alice",
            LastNameAttribute: "Wonderland",
            BirthDateAttribute: "1993-08-10",
            SexAttribute: "F",
            SocialSecurityNumberAttribute: "345-54-6795",
            PostalCodeAttribute: "98052",
        }
        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([row]))

        PersonAttributesProcessor.process(reader, writer, [], Metadata().initialize())

        payloads = _written_payloads(writer)
        assert payloads
        assert {payload["RecordId"] for payload in payloads} == {"legacy-record-id"}

    def test_process_legacy_rows_warn_once_when_reader_uses_deprecated_shape(self, caplog):
        """Legacy reader rows should emit a single deprecation warning per processing run."""
        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([_complete_legacy_row(), _complete_legacy_row()]))

        caplog.set_level(logging.WARNING, logger="openlinktoken_cli.processor.person_attributes_processor")

        PersonAttributesProcessor.process(reader, writer, [], Metadata().initialize())

        assert sum("deprecated" in message.lower() for message in caplog.messages) == 1

    @pytest.mark.parametrize(
        ("rows", "legacy_row_count"),
        [
            pytest.param([{}, _complete_legacy_row()], 1, id="empty-before-legacy"),
            pytest.param(
                [_complete_legacy_row(), {}, _complete_legacy_row()],
                2,
                id="empty-between-legacy",
            ),
            pytest.param([_complete_legacy_row(), {}], 1, id="empty-after-legacy"),
        ],
    )
    def test_process_empty_rows_preserve_established_legacy_shape(self, rows, legacy_row_count, caplog):
        """Empty rows should not prevent established legacy rows from using compatibility token generation."""
        expected_reader = Mock(spec=PersonAttributesReader)
        expected_writer = Mock(spec=PersonAttributesWriter)
        expected_reader.__iter__ = Mock(return_value=iter([_complete_legacy_row()]))

        caplog.set_level(logging.WARNING, logger="openlinktoken_cli.processor.person_attributes_processor")
        PersonAttributesProcessor.process(expected_reader, expected_writer, [], Metadata().initialize())
        expected_legacy_payloads = _written_payloads(expected_writer)
        caplog.clear()

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter(rows))

        summary = PersonAttributesProcessor.process(reader, writer, [], Metadata().initialize())

        legacy_payloads = [payload for payload in _written_payloads(writer) if payload["RecordId"] == "A-1001"]
        assert summary.total_rows == len(rows)
        assert legacy_payloads == expected_legacy_payloads * legacy_row_count
        assert sum("deprecated" in message.lower() for message in caplog.messages) == 1

    @pytest.mark.parametrize(
        "rows",
        [
            pytest.param(
                [_complete_legacy_row(), _complete_field_id_row()],
                id="legacy-to-field-id",
            ),
            pytest.param(
                [_complete_field_id_row(), _complete_legacy_row()],
                id="field-id-to-legacy",
            ),
        ],
    )
    def test_process_row_shape_change_raises_value_error(self, rows):
        """Readers must not switch row shapes mid-stream."""
        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter(rows))

        with pytest.raises(ValueError, match="row shape"):
            PersonAttributesProcessor.process(reader, writer, [], Metadata().initialize())

    def test_process_unsupported_row_key_type_raises_type_error(self):
        """Rows with unsupported key types should be rejected."""
        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([{1: "bad-key"}]))

        with pytest.raises(TypeError, match="unsupported key"):
            PersonAttributesProcessor.process(reader, writer, [], Metadata().initialize())

    def test_process_mixed_row_key_types_raises_type_error(self):
        """Rows mixing field-ID and Attribute-class keys should be rejected."""
        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([{"FirstName": "Alice", LastNameAttribute: "Wonderland"}]))

        with pytest.raises(TypeError, match="cannot mix"):
            PersonAttributesProcessor.process(reader, writer, [], Metadata().initialize())
