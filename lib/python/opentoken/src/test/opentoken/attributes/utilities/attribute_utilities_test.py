"""
Tests for AttributeUtilities.
"""

import pytest

from opentoken.attributes.utilities.attribute_utilities import AttributeUtilities


class TestAttributeUtilities:
    """Test cases for AttributeUtilities."""

    def test_cannot_instantiate(self):
        """AttributeUtilities is a utility class and should not be instantiatable."""
        with pytest.raises(RuntimeError):
            AttributeUtilities()

    def test_normalize_diacritics_raises_on_none(self):
        """normalize_diacritics should raise AttributeError for None input."""
        with pytest.raises(AttributeError):
            AttributeUtilities.normalize_diacritics(None)

    def test_remove_whitespace_returns_none_for_none(self):
        """remove_whitespace should return None when given None."""
        assert AttributeUtilities.remove_whitespace(None) is None

    def test_remove_non_alphabetic_returns_none_for_none(self):
        """remove_non_alphabetic_characters should return None when given None."""
        assert AttributeUtilities.remove_non_alphabetic_characters(None) is None

    def test_remove_non_alphabetic_removes_digits_and_symbols(self):
        """remove_non_alphabetic_characters should strip digits and symbols."""
        assert AttributeUtilities.remove_non_alphabetic_characters("ABC123!") == "ABC"

    def test_remove_generational_suffix_returns_none_for_none(self):
        """remove_generational_suffix should return None when given None."""
        assert AttributeUtilities.remove_generational_suffix(None) is None

    def test_get_common_placeholder_names_returns_copy(self):
        """get_common_placeholder_names should return a copy of the set."""
        result = AttributeUtilities.get_common_placeholder_names()
        assert isinstance(result, set)
        assert "Unknown" in result
        # Mutating the copy should not affect the original
        result.add("__test__")
        assert "__test__" not in AttributeUtilities.get_common_placeholder_names()
