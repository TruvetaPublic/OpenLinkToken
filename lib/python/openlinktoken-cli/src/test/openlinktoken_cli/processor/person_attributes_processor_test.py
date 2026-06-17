# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from openlinktoken.metadata import Metadata
from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenRuleEntry,
    TokenizationConfig,
)
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.person_attributes_reader import PersonAttributesReader
from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter
from openlinktoken_cli.processor.person_attributes_processor import PersonAttributesProcessor


class TestPersonAttributesProcessor:
    """Test cases for PersonAttributesProcessor."""

    def test_process_happy_path(self):
        """Test process happy path."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        data = {RecordIdAttribute: "TestRecordId", FirstNameAttribute: "John", LastNameAttribute: "Spencer"}

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
        data = {RecordIdAttribute: "TestRecordId", FirstNameAttribute: "John", LastNameAttribute: "Spencer"}

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
        data = {RecordIdAttribute: "TestRecordId", FirstNameAttribute: "John", LastNameAttribute: "Spencer"}

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
            RecordIdAttribute: "TestRecordId",
            FirstNameAttribute: "John",
            LastNameAttribute: "Spencer",
            SocialSecurityNumberAttribute: "234-56-7890",
            BirthDateAttribute: "1990-01-15",
            SexAttribute: "Male",
            PostalCodeAttribute: "98052",
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
        data1 = {RecordIdAttribute: "TestRecordId1", FirstNameAttribute: "John", LastNameAttribute: "Spencer"}
        data2 = {RecordIdAttribute: "TestRecordId2", FirstNameAttribute: "Jane", LastNameAttribute: "Doe"}
        data3 = {RecordIdAttribute: "TestRecordId3", FirstNameAttribute: "Alex", LastNameAttribute: "Smith"}

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
        data = {RecordIdAttribute: "TestRecordId", FirstNameAttribute: "John", LastNameAttribute: "Spencer"}

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
                "given_nm": AttributeMappingEntry(field="GivenName", type="GivenName"),
                "family_nm": AttributeMappingEntry(field="FamilyName", type="LastName"),
            },
            token_rules={
                "T1": [
                    TokenRuleEntry(field="FamilyName", expression="T|U"),
                    TokenRuleEntry(field="GivenName", expression="T|S(0,1)|U"),
                ]
            },
        )
        factory = DynamicAttributeFactory(config)
        token_definition = DynamicTokenDefinition(config, factory)

        given_name_class = factory.get_class_for_field("GivenName")
        family_name_class = factory.get_class_for_field("FamilyName")
        row = {
            RecordIdAttribute: "TestRecordId",
            given_name_class: "John",
            family_name_class: "Spencer",
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
