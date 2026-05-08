"""
Tests for AttributeUtilities.
"""

import pytest

from openlinktoken.attributes.utilities.attribute_utilities import AttributeUtilities


class TestAttributeUtilities:
    """Test cases for AttributeUtilities."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Æ", "AE"),
            ("æ", "ae"),
            ("Ð", "D"),
            ("ð", "d"),
            ("Ø", "O"),
            ("ø", "o"),
            ("Þ", "TH"),
            ("þ", "th"),
            ("ß", "ss"),
            ("ẞ", "SS"),
            ("Đ", "D"),
            ("đ", "d"),
            ("Ħ", "H"),
            ("ħ", "h"),
            ("ı", "i"),
            ("Ĳ", "IJ"),
            ("ĳ", "ij"),
            ("Ŀ", "L"),
            ("ŀ", "l"),
            ("Ł", "L"),
            ("ł", "l"),
            ("ŉ", "n"),
            ("Ŋ", "NG"),
            ("ŋ", "ng"),
            ("Œ", "OE"),
            ("œ", "oe"),
            ("Ŧ", "T"),
            ("ŧ", "t"),
            ("ſ", "s"),
            ("Ƒ", "F"),
            ("ƒ", "f"),
            ("Ǆ", "DZ"),
            ("ǅ", "Dz"),
            ("ǆ", "dz"),
            ("Ǉ", "LJ"),
            ("ǈ", "Lj"),
            ("ǉ", "lj"),
            ("Ǌ", "NJ"),
            ("ǋ", "Nj"),
            ("ǌ", "nj"),
            ("Ǳ", "DZ"),
            ("ǲ", "Dz"),
            ("ǳ", "dz"),
            ("Ǽ", "AE"),
            ("ǽ", "ae"),
            ("Ǿ", "O"),
            ("ǿ", "o"),
        ],
    )
    def test_normalize_diacritics_transliterates_latin_extended_characters(self, value, expected):
        """normalize_diacritics should transliterate Latin Extended characters before NFD."""
        assert AttributeUtilities.normalize_diacritics(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Łukasz", "Lukasz"),
            ("Søren Kierkegård", "Soren Kierkegard"),
            ("Ægir Þór", "AEgir THor"),
            ("Đỗ", "Do"),
            ("Dvo\u0159\u00e1k\u20dd", "Dvorak"),
        ],
    )
    def test_normalize_diacritics_handles_real_name_examples(self, value, expected):
        """normalize_diacritics should preserve ASCII equivalents in representative names."""
        assert AttributeUtilities.normalize_diacritics(value) == expected

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
