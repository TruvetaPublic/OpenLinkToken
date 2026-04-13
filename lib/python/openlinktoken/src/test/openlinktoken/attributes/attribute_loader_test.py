"""
Copyright (c) Truveta. All rights reserved.
"""

from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute


class TestAttributeLoader:
    """Test cases for AttributeLoader."""

    def test_load_attributes_should_load_attributes(self):
        """Test that load_attributes loads the expected attributes."""
        attributes_set = AttributeLoader.load()

        # Find RecordIdAttribute in the loaded attributes
        record_id_attribute = next((attr for attr in attributes_set if isinstance(attr, RecordIdAttribute)), None)
        assert record_id_attribute is not None, "RecordIdAttribute should be loaded"

        # Find LastNameAttribute in the loaded attributes
        last_name_attribute = next((attr for attr in attributes_set if isinstance(attr, LastNameAttribute)), None)
        assert last_name_attribute is not None, "LastNameAttribute should be loaded"
