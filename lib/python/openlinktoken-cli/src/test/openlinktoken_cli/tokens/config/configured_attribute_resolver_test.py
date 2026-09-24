# SPDX-License-Identifier: MIT

import pytest

from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig


class TestConfiguredAttributeResolver:
    """
    Test resolution of configured attributes by field identifier.
    """

    def test_maps_same_base_type_to_same_class_with_distinct_field_ids(self):
        """
        Verify that maps same base type to same class with distinct field ids.
        """
        config = TokenizationConfig(
            column_mappings={
                "PatientZip": AttributeMappingEntry(column_name="patient_zip", type="PostalCode"),
                "HospitalZip": AttributeMappingEntry(column_name="hospital_zip", type="PostalCode"),
            },
            token_rules={},
        )

        resolver = ConfiguredAttributeResolver(config)
        patient_class = resolver.get_class_for_field("PatientZip")
        hospital_class = resolver.get_class_for_field("HospitalZip")

        # Both fields map to the same base class; field IDs are the distinguishing keys.
        assert issubclass(patient_class, PostalCodeAttribute)
        assert issubclass(hospital_class, PostalCodeAttribute)
        # Each field gets a distinct dynamic subclass so they don't collide.
        assert patient_class is not hospital_class
        assert resolver.get_field_for_column("patient_zip") == "PatientZip"
        assert resolver.get_field_for_column("hospital_zip") == "HospitalZip"

    def test_build_field_registry_contains_all_configured_fields(self):
        """
        Verify that build field registry contains all configured fields.
        """
        config = TokenizationConfig(
            column_mappings={
                "PatientZip": AttributeMappingEntry(column_name="patient_zip", type="PostalCode"),
                "HospitalZip": AttributeMappingEntry(column_name="hospital_zip", type="PostalCode"),
            },
            token_rules={},
        )

        resolver = ConfiguredAttributeResolver(config)
        registry = resolver.build_field_registry()

        assert "PatientZip" in registry.get_field_ids()
        assert "HospitalZip" in registry.get_field_ids()
        assert registry.get_attribute("PatientZip") is not None
        assert registry.get_attribute("HospitalZip") is not None
        assert isinstance(registry.get_attribute("PatientZip"), PostalCodeAttribute)

    def test_unknown_field_lookup_raises_key_error(self):
        """
        Verify that unknown field lookup raises key error.
        """
        config = TokenizationConfig(
            column_mappings={
                "PatientZip": AttributeMappingEntry(column_name="patient_zip", type="PostalCode"),
            },
            token_rules={},
        )

        resolver = ConfiguredAttributeResolver(config)

        with pytest.raises(KeyError):
            resolver.get_class_for_field("DoesNotExist")

    def test_unknown_attribute_type_raises_value_error(self):
        """
        Verify that unknown attribute type raises value error.
        """
        config = TokenizationConfig(
            column_mappings={
                "SomeField": AttributeMappingEntry(column_name="some_column", type="NotARealType"),
            },
            token_rules={},
        )

        with pytest.raises(ValueError, match="Unknown attribute type"):
            ConfiguredAttributeResolver(config)

    def test_conflicting_aliases_raise_value_error(self, monkeypatch):
        """
        Verify that conflicting aliases raise value error.

        Args:
            monkeypatch: Pytest fixture for temporarily patching environment variables and process state.
        """

        class FirstAttribute:
            """
            Test attribute implementation for the first configured person field.
            """

            def get_name(self):
                """
                Retrieve name.

                Returns:
                    The name.
                """
                return "TypeOne"

            def get_aliases(self):
                """
                Retrieve aliases.

                Returns:
                    The aliases.
                """
                return ["SharedAlias"]

        class SecondAttribute:
            """
            Test attribute implementation for the second configured person field.
            """

            def get_name(self):
                """
                Retrieve name.

                Returns:
                    The name.
                """
                return "TypeTwo"

            def get_aliases(self):
                """
                Retrieve aliases.

                Returns:
                    The aliases.
                """
                return ["SharedAlias"]

        monkeypatch.setattr(AttributeLoader, "load", lambda: [FirstAttribute(), SecondAttribute()])

        config = TokenizationConfig(
            column_mappings={
                "SomeField": AttributeMappingEntry(column_name="source", type="SharedAlias"),
            },
            token_rules={},
        )

        with pytest.raises(ValueError, match="Conflicting attribute type mapping for 'SharedAlias'"):
            ConfiguredAttributeResolver(config)
