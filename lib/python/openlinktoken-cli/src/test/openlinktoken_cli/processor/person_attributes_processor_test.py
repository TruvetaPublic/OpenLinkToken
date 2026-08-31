# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import openlinktoken.tokens.token_generator as token_generator_module
from openlinktoken.metadata import Metadata
from openlinktoken.tokens.inference_signature_provider import InferenceBatchResult
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult
from openlinktoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.person_attributes_reader import PersonAttributesReader
from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter
from openlinktoken_cli.processor.person_attributes_processor import (
    PersonAttributesProcessor,
    _PendingRow,
)
from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenizationConfig,
    TokenRuleEntry,
)


class TestPersonAttributesProcessor:
    """Test cases for PersonAttributesProcessor."""

    def test_batched_ml1_does_not_run_single_row_inference(self, monkeypatch):
        """Batched ML1 processing invokes only the provider batch API."""

        class CountingProvider:
            def __init__(self):
                self.single_calls = 0
                self.batch_calls = 0

            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, row):
                self.single_calls += 1
                return "single"

            def generate_batch(self, rows):
                self.batch_calls += 1
                return InferenceBatchResult(["batch"] * len(rows))

        provider = CountingProvider()
        monkeypatch.setattr(token_generator_module, "_inference_provider", provider)
        monkeypatch.setattr(token_generator_module, "_provider_discovered", True)

        definition = Mock()
        definition.get_token_identifiers.return_value = {"ML1"}
        definition.get_token_definition.return_value = []
        token_generator = TokenGenerator(definition, PassthroughTokenizer([]))

        PersonAttributesProcessor._process_rows_with_batched_ml1(
            [{"LastName": "Smith"}],
            Mock(spec=PersonAttributesWriter),
            token_generator,
            {},
            {},
            None,
            None,
            {},
        )

        assert provider.single_calls == 0
        assert provider.batch_calls == 1

    def test_flush_pending_rows_uses_precomputed_ml1_signatures(self, monkeypatch):
        """Flushing applies supplied ML1 signatures without performing inference."""

        def fail_provider_lookup():
            raise AssertionError("flush must not discover or invoke the inference provider")

        monkeypatch.setattr(TokenGenerator, "get_inference_provider", fail_provider_lookup)

        token_generator = Mock(spec=TokenGenerator)
        token_generator_result = TokenGeneratorResult()
        pending_rows = [
            _PendingRow(
                row={"RecordId": "row-1"},
                row_counter=1,
                token_generator_result=token_generator_result,
            )
        ]

        PersonAttributesProcessor._flush_pending_rows(
            writer=Mock(spec=PersonAttributesWriter),
            token_generator=token_generator,
            invalid_attribute_count={},
            blank_tokens_by_rule_count={},
            encryption_key=None,
            ring_id=None,
            jwe_formatters={},
            pending_rows=pending_rows,
            ml1_signatures=["precomputed-signature"],
        )

        token_generator.store_raw_token.assert_called_once_with(
            token_generator_result,
            "ML1",
            "precomputed-signature",
        )

    def test_process_happy_path(self):
        """Test process happy path."""
        token_transformer_list = [Mock(spec=HashTokenTransformer)]
        data = {"RecordId": "TestRecordId", "FirstName": "John", "LastName": "Spencer"}

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))

        metadata_map = Metadata().initialize()
        PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

        # Verify writer was called at least 5 times (T1-T5; ML1 may also fire if openlinktoken-core-ai is installed)
        assert writer.write_attributes.call_count >= 5

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
        assert PersonAttributesProcessor.BLANK_TOKENS_BY_RULE_KEY in metadata_map, (
            "Metadata should contain blankTokensByRule key"
        )

        # The invalid attributes map should contain all attributes with zero counts
        invalid_attributes_map = metadata_map[PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE]
        assert len(invalid_attributes_map) > 0, "Invalid attributes map should contain all attributes initialized to 0"

        # Verify all invalid attribute values are 0 (no invalid attributes in this test)
        for count in invalid_attributes_map.values():
            assert count == 0, "All attribute counts should be 0 with valid data"

        # Verify blank tokens map contains all token rules
        blank_tokens_map = metadata_map[PersonAttributesProcessor.BLANK_TOKENS_BY_RULE_KEY]
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
        blank_tokens_map = metadata_map[PersonAttributesProcessor.BLANK_TOKENS_BY_RULE_KEY]
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
            column_mappings={
                "FirstName": AttributeMappingEntry(column_name="given_nm", type="GivenName"),
                "FamilyName": AttributeMappingEntry(column_name="family_nm", type="LastName"),
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

    def test_process_preserves_record_id_from_config_mapped_column(self):
        """Config-mapped RecordId column is used as output record ID, not replaced by a UUID.

        The field id ("EncounterId") intentionally differs from the type ("RecordId") to
        verify that the fix handles any RecordIdAttribute subclass key, not just ones named
        "RecordId".
        """
        config = TokenizationConfig(
            column_mappings={
                "EncounterId": AttributeMappingEntry(column_name="encounter_id", type="RecordId"),
                "FirstName": AttributeMappingEntry(column_name="given_nm", type="GivenName"),
            },
            token_rules={
                "T1": [TokenRuleEntry(field="FirstName", expression="T|U")],
            },
        )
        resolver = ConfiguredAttributeResolver(config)
        token_definition = DynamicTokenDefinition(config, resolver)

        # Simulate the per-row dict as produced by a config-driven reader:
        # keys are unique attribute subclasses, not plain strings.
        record_id_class = resolver.get_class_for_field("EncounterId")
        first_name_class = resolver.get_class_for_field("FirstName")
        row = {
            record_id_class: "enc-001",
            first_name_class: "Ana",
        }

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([row]))
        metadata_map = Metadata().initialize()

        PersonAttributesProcessor.process(reader, writer, [], metadata_map, token_definition=token_definition)

        written = writer.write_attributes.call_args[0][0]
        assert written["RecordId"] == "enc-001", "Source record ID must be preserved, not replaced by a UUID"

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

    def test_process_counts_invalid_rows_separately_from_invalid_attributes(self):
        """Counts one invalid row when multiple attributes in that row are invalid."""
        data = {
            "RecordId": "TestRecordId",
            "FirstName": "John",
            "LastName": "Spencer",
            "SocialSecurityNumber": "234-56-7890",
            "BirthDate": "",
            "Sex": "Unknown",
            "PostalCode": "98052",
        }

        reader = Mock(spec=PersonAttributesReader)
        writer = Mock(spec=PersonAttributesWriter)
        reader.__iter__ = Mock(return_value=iter([data]))
        metadata_map = Metadata().initialize()

        summary = PersonAttributesProcessor.process(
            reader,
            writer,
            [],
            metadata_map,
            token_definition=TokenDefinition(),
        )

        assert summary.total_rows_with_invalid_attributes == 1
        assert metadata_map[PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES] == 1
        assert summary.invalid_attributes_by_type["BirthDate"] == 1
        assert summary.invalid_attributes_by_type["Sex"] == 1

    def test_batched_ml1_progress_callback_fires_after_each_batch_flush(self, monkeypatch):
        """Progress callback fires once per flushed batch so counts reflect written records."""

        class StubProvider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_batch(self, rows):
                return InferenceBatchResult(["sig"] * len(rows))

        monkeypatch.setattr(token_generator_module, "_inference_provider", StubProvider())
        monkeypatch.setattr(token_generator_module, "_provider_discovered", True)

        # Patch batch_size to 2 so two flushes occur for 4 input rows.
        import openlinktoken.core.ai.tokens.ml1_inference_config as ml1_module

        monkeypatch.setattr(ml1_module.ML1InferenceConfig, "get_batch_size", staticmethod(lambda: 2))

        definition = Mock()
        definition.get_token_identifiers.return_value = {"ML1"}
        definition.get_token_definition.return_value = []
        token_generator = TokenGenerator(definition, PassthroughTokenizer([]))

        callback_counts: list[int] = []
        rows = [{"RecordId": str(i)} for i in range(4)]

        PersonAttributesProcessor._process_rows_with_batched_ml1(
            rows,
            Mock(spec=PersonAttributesWriter),
            token_generator,
            {},
            {},
            None,
            None,
            {},
            progress_callback=callback_counts.append,
        )

        # Callback must fire once per flush (batch_size=2, 4 rows → 2 flushes).
        # Each call must reflect the row count *after* the flush writes have completed.
        assert callback_counts == [2, 4], f"Expected [2, 4] (one call per flush), got {callback_counts}"

    def test_non_ml1_progress_callback_fires_every_ten_rows(self, monkeypatch):
        """Non-ML1 progress callback continues to fire at the existing per-row interval."""
        callback_counts: list[int] = []

        reader_rows = [{"RecordId": str(i)} for i in range(25)]
        writer = Mock(spec=PersonAttributesWriter)
        token_generator = Mock(spec=TokenGenerator)
        token_generator.get_all_tokens_via_field_id.return_value = TokenGeneratorResult()

        PersonAttributesProcessor._process_rows_without_batched_ml1(
            reader_rows,
            writer,
            token_generator,
            {},
            {},
            None,
            None,
            {},
            progress_callback=callback_counts.append,
        )

        # Every 10th row fires plus a final call for row 25 (25 % 10 != 0).
        assert 10 in callback_counts
        assert 20 in callback_counts
        assert 25 in callback_counts  # final flush of remainder

    def test_non_ml1_progress_callback_does_not_repeat_completed_interval(self):
        """A complete final interval should not produce a duplicate callback."""
        callback_counts: list[int] = []
        token_generator = Mock(spec=TokenGenerator)
        token_generator.get_all_tokens_via_field_id.return_value = TokenGeneratorResult()

        PersonAttributesProcessor._process_rows_without_batched_ml1(
            [{"RecordId": str(i)} for i in range(20)],
            Mock(spec=PersonAttributesWriter),
            token_generator,
            {},
            {},
            None,
            None,
            {},
            progress_callback=callback_counts.append,
        )

        assert callback_counts == [10, 20]
