# SPDX-License-Identifier: MIT

import pytest

from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig


class TestDynamicAttributeFactory:
    def test_creates_unique_dynamic_classes_for_same_base_type(self):
        config = TokenizationConfig(
            attributes={
                "patient_zip": AttributeMappingEntry(field="PatientZip", type="PostalCode"),
                "hospital_zip": AttributeMappingEntry(field="HospitalZip", type="PostalCode"),
            },
            token_rules={},
        )

        factory = DynamicAttributeFactory(config)
        patient_class = factory.get_class_for_field("PatientZip")
        hospital_class = factory.get_class_for_field("HospitalZip")

        assert patient_class is not hospital_class
        assert issubclass(patient_class, PostalCodeAttribute)
        assert issubclass(hospital_class, PostalCodeAttribute)
        assert factory.get_class_for_csv_column("patient_zip") is patient_class
        assert factory.get_class_for_csv_column("hospital_zip") is hospital_class

    def test_unknown_field_lookup_raises_key_error(self):
        config = TokenizationConfig(
            attributes={
                "patient_zip": AttributeMappingEntry(field="PatientZip", type="PostalCode"),
            },
            token_rules={},
        )

        factory = DynamicAttributeFactory(config)

        with pytest.raises(KeyError):
            factory.get_class_for_field("DoesNotExist")

    def test_unknown_attribute_type_raises_value_error(self):
        config = TokenizationConfig(
            attributes={
                "some_column": AttributeMappingEntry(field="SomeField", type="NotARealType"),
            },
            token_rules={},
        )

        with pytest.raises(ValueError, match="Unknown attribute type"):
            DynamicAttributeFactory(config)
