"""
Tests for USPostalCodeAttribute.
"""

import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

from opentoken.attributes.person.us_postal_code_attribute import USPostalCodeAttribute


class TestUSPostalCodeAttribute:
    """Test cases for USPostalCodeAttribute."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.us_postal_code_attribute = USPostalCodeAttribute(min_length=3)

    def test_get_name_should_return_us_postal_code(self):
        """Test that get_name returns 'USPostalCode'."""
        assert self.us_postal_code_attribute.get_name() == "USPostalCode"

    def test_get_aliases_should_return_us_zip_code_aliases(self):
        """Test that get_aliases returns USPostalCode and USZipCode."""
        expected_aliases = ["USPostalCode", "USZipCode"]
        assert self.us_postal_code_attribute.get_aliases() == expected_aliases

    def test_normalize_should_return_first_5_digits(self):
        """Test normalization returns first 5 digits for US ZIP codes."""
        assert self.us_postal_code_attribute.normalize("10001-6789") == "10001"
        assert self.us_postal_code_attribute.normalize("10001") == "10001"
        assert self.us_postal_code_attribute.normalize("100016789") == "10001"
        assert self.us_postal_code_attribute.normalize("95123-6789") == "95123"
        assert self.us_postal_code_attribute.normalize("951236789") == "95123"
        assert self.us_postal_code_attribute.normalize("65201-6789") == "65201"
        assert self.us_postal_code_attribute.normalize("652016789") == "65201"

    def test_normalize_should_handle_whitespace(self):
        """Test normalization handles whitespace for US ZIP codes."""
        assert self.us_postal_code_attribute.normalize("10001") == "10001"
        assert self.us_postal_code_attribute.normalize(" 10001") == "10001"
        assert self.us_postal_code_attribute.normalize("10001 ") == "10001"
        assert self.us_postal_code_attribute.normalize(" 10001 ") == "10001"
        assert self.us_postal_code_attribute.normalize("1 0 0 0 1") == "10001"
        assert self.us_postal_code_attribute.normalize("10\t001") == "10001"
        assert self.us_postal_code_attribute.normalize("10\n001") == "10001"
        assert self.us_postal_code_attribute.normalize("10\r\n001") == "10001"
        assert self.us_postal_code_attribute.normalize("  10   001  ") == "10001"

    def test_validate_should_return_true_for_valid_us_zip_codes(self):
        """Test validation returns true for valid US ZIP codes."""
        assert self.us_postal_code_attribute.validate("95123 ") is True
        assert self.us_postal_code_attribute.validate(" 95123") is True
        assert self.us_postal_code_attribute.validate("95123") is True
        assert self.us_postal_code_attribute.validate("95123-6789") is True
        assert self.us_postal_code_attribute.validate("951236789") is True
        assert self.us_postal_code_attribute.validate("65201-6789") is True
        assert self.us_postal_code_attribute.validate("652016789") is True
        assert self.us_postal_code_attribute.validate("10001") is True
        assert self.us_postal_code_attribute.validate("100016789") is True
        assert self.us_postal_code_attribute.validate("90210-1234") is True
        assert self.us_postal_code_attribute.validate("902101234") is True

    def test_validate_should_return_false_for_null_and_empty(self):
        """Test validation returns false for null and empty values."""
        assert self.us_postal_code_attribute.validate(None) is False
        assert self.us_postal_code_attribute.validate("") is False

    def test_validate_should_return_false_for_invalid_formats(self):
        """Test validation returns false for invalid formats."""
        assert self.us_postal_code_attribute.validate("12") is False
        assert self.us_postal_code_attribute.validate("123456") is False
        assert self.us_postal_code_attribute.validate("1234-5678") is False
        assert self.us_postal_code_attribute.validate("abcde") is False
        assert self.us_postal_code_attribute.validate("K1A 0A6") is False

    def test_validate_should_return_false_for_placeholder_zip_codes(self):
        """Test validation returns false for placeholder ZIP codes."""
        invalid_zip_codes = [
            "12345",
            "54321",
            "01234",
            "98765",
            "00000",
            "11111",
            "22222",
            "33333",
            "55555",
            "66666",
            "77777",
            "88888",
            "99999",
        ]
        for zip_code in invalid_zip_codes:
            assert self.us_postal_code_attribute.validate(zip_code) is False

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_postal_code = "10001-6789"
        expected_result = "10001"
        results = []

        def normalize_postal_code():
            return self.us_postal_code_attribute.normalize(test_postal_code)

        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(normalize_postal_code) for _ in range(thread_count)]
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == thread_count
        assert all(result == expected_result for result in results)

    def test_normalize_should_handle_edge_cases(self):
        """Test normalization handles edge cases."""
        # Less than 3 digits - return trimmed original
        assert self.us_postal_code_attribute.normalize("12") == "12"
        assert self.us_postal_code_attribute.normalize("1") == "1"

        # Null and empty
        assert self.us_postal_code_attribute.normalize(None) is None
        assert self.us_postal_code_attribute.normalize("") == ""

        # 5+ digit codes
        assert self.us_postal_code_attribute.normalize("10001") == "10001"
        assert self.us_postal_code_attribute.normalize(" 10001") == "10001"
        assert self.us_postal_code_attribute.normalize("10001-1234") == "10001"
        assert self.us_postal_code_attribute.normalize("100011234") == "10001"

        # Non-US formats
        assert self.us_postal_code_attribute.normalize("K1B 0A7") == "K1B 0A7"
        assert self.us_postal_code_attribute.normalize("k1b0a7") == "k1b0a7"

    def test_normalize_should_pad_zip3_to_zip5(self):
        """Test ZIP-3 padding with '00'."""
        assert self.us_postal_code_attribute.normalize("951") == "95100"
        assert self.us_postal_code_attribute.normalize(" 951") == "95100"
        assert self.us_postal_code_attribute.normalize("951 ") == "95100"
        assert self.us_postal_code_attribute.normalize(" 951 ") == "95100"
        assert self.us_postal_code_attribute.normalize("123") == "12300"
        assert self.us_postal_code_attribute.normalize("980") == "98000"
        assert self.us_postal_code_attribute.normalize("303") == "30300"
        assert self.us_postal_code_attribute.normalize("606") == "60600"

    def test_normalize_should_pad_zip4_to_zip5(self):
        """Test ZIP-4 padding with '0'."""
        assert self.us_postal_code_attribute.normalize("1234") == "12340"
        assert self.us_postal_code_attribute.normalize(" 1234") == "12340"
        assert self.us_postal_code_attribute.normalize("1234 ") == "12340"
        assert self.us_postal_code_attribute.normalize(" 1234 ") == "12340"
        assert self.us_postal_code_attribute.normalize("5678") == "56780"
        assert self.us_postal_code_attribute.normalize("9021") == "90210"
        assert self.us_postal_code_attribute.normalize("3030") == "30300"

    def test_validate_should_return_true_for_valid_zip3(self):
        """Test validation returns true for valid ZIP-3 codes."""
        assert self.us_postal_code_attribute.validate("951") is True
        assert self.us_postal_code_attribute.validate(" 951") is True
        assert self.us_postal_code_attribute.validate("951 ") is True
        assert self.us_postal_code_attribute.validate("123") is True
        assert self.us_postal_code_attribute.validate("980") is True
        assert self.us_postal_code_attribute.validate("303") is True
        assert self.us_postal_code_attribute.validate("606") is True

    def test_validate_should_return_true_for_valid_zip4(self):
        """Test validation returns true for valid ZIP-4 codes."""
        assert self.us_postal_code_attribute.validate("1234") is True
        assert self.us_postal_code_attribute.validate(" 1234") is True
        assert self.us_postal_code_attribute.validate("1234 ") is True
        assert self.us_postal_code_attribute.validate("5678") is True
        assert self.us_postal_code_attribute.validate("9021") is True
        assert self.us_postal_code_attribute.validate("3030") is True
        assert self.us_postal_code_attribute.validate("6060") is True

    def test_validate_should_return_false_for_invalid_zip3(self):
        """Test validation returns false for invalid ZIP-3 codes."""
        # These are the invalid ZIP-3 prefixes
        assert self.us_postal_code_attribute.validate("000") is False
        assert self.us_postal_code_attribute.validate("555") is False
        assert self.us_postal_code_attribute.validate("888") is False

        # These should be valid (not in invalid list)
        assert self.us_postal_code_attribute.validate("111") is True
        assert self.us_postal_code_attribute.validate("222") is True
        assert self.us_postal_code_attribute.validate("987") is True

    def test_validate_should_return_false_for_invalid_zip4(self):
        """Test validation returns false for invalid ZIP-4 codes that start with invalid prefixes."""
        # These ZIP-4 codes start with invalid ZIP-3 prefixes
        assert self.us_postal_code_attribute.validate("0001") is False
        assert self.us_postal_code_attribute.validate("5555") is False
        assert self.us_postal_code_attribute.validate("8888") is False

        # These should be valid (not in invalid list)
        assert self.us_postal_code_attribute.validate("1111") is True
        assert self.us_postal_code_attribute.validate("1234") is True
        assert self.us_postal_code_attribute.validate("2222") is True
        assert self.us_postal_code_attribute.validate("9876") is True

    def test_serialization(self):
        """Test serialization and deserialization of USPostalCodeAttribute."""
        serialized_data = pickle.dumps(self.us_postal_code_attribute)
        deserialized_attribute = pickle.loads(serialized_data)

        test_values = ["10001", "10001-1234", "90210-5678", "30301", "60601-2345"]

        for value in test_values:
            assert self.us_postal_code_attribute.get_name() == deserialized_attribute.get_name()
            assert self.us_postal_code_attribute.get_aliases() == deserialized_attribute.get_aliases()
            assert self.us_postal_code_attribute.normalize(value) == deserialized_attribute.normalize(value)
            assert self.us_postal_code_attribute.validate(value) == deserialized_attribute.validate(value)
