"""
Copyright (c) Truveta. All rights reserved.
"""

import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute


class TestSocialSecurityNumberAttribute:
    """Test cases for SocialSecurityNumberAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.ssn_attribute = SocialSecurityNumberAttribute()

    def test_get_name_should_return_social_security_number(self):
        """Test that get_name returns 'SocialSecurityNumber'."""
        assert self.ssn_attribute.get_name() == "SocialSecurityNumber"

    def test_get_aliases_should_return_social_security_number_and_national_identification_number(self):
        """Test that get_aliases returns SocialSecurityNumber and NationalIdentificationNumber."""
        expected_aliases = ["SocialSecurityNumber", "NationalIdentificationNumber"]
        actual_aliases = self.ssn_attribute.get_aliases()
        assert actual_aliases == expected_aliases

    def test_normalize_should_format_with_dashes(self):
        """Test normalization formats SSNs with dashes."""
        assert self.ssn_attribute.normalize("123456789") == "123-45-6789"
        assert self.ssn_attribute.normalize("123-45-6789") == "123-45-6789"
        assert self.ssn_attribute.normalize("123456789.0") == "123-45-6789"
        assert self.ssn_attribute.normalize("1234567") == "001-23-4567"
        assert self.ssn_attribute.normalize("1234567.0") == "001-23-4567"

    def test_normalize_should_handle_edge_cases(self):
        """Test normalization handles edge cases."""
        assert self.ssn_attribute.normalize("1234567890") == "1234567890"
        assert self.ssn_attribute.normalize("12345678901.0") == "12345678901.0"
        assert self.ssn_attribute.normalize("12345678901") == "12345678901"
        assert self.ssn_attribute.normalize("12345.0") == "12345.0"
        assert self.ssn_attribute.normalize("Unknown") == "Unknown"
        assert self.ssn_attribute.normalize("ABC-12-DEFG") == "ABC-12-DEFG"

    def test_normalize_should_handle_short_inputs_without_crashing(self):
        """Test normalization handles short inputs without crashing."""
        assert self.ssn_attribute.normalize("123456") == "123456"
        assert self.ssn_attribute.normalize("12345") == "12345"
        assert self.ssn_attribute.normalize("1234") == "1234"
        assert self.ssn_attribute.normalize("123") == "123"
        assert self.ssn_attribute.normalize("12") == "12"
        assert self.ssn_attribute.normalize("1") == "1"
        assert self.ssn_attribute.normalize("") == ""

    def test_normalize_should_handle_spaces(self):
        """Test normalization handles spaces."""
        assert self.ssn_attribute.normalize("123 45 6789") == "123-45-6789"
        assert self.ssn_attribute.normalize("123  45  6789") == "123-45-6789"
        assert self.ssn_attribute.normalize(" 123456789 ") == "123-45-6789"

    def test_normalize_should_handle_mixed_formatting(self):
        """Test normalization handles mixed formatting."""
        assert self.ssn_attribute.normalize("123 45-6789") == "123-45-6789"
        assert self.ssn_attribute.normalize("123-45 6789") == "123-45-6789"
        assert self.ssn_attribute.normalize(" 123-456789") == "123-45-6789"

    def test_normalize_should_handle_null_and_empty_values(self):
        """Test normalization handles null and empty values."""
        assert self.ssn_attribute.normalize(None) is None
        assert self.ssn_attribute.normalize("") == ""

    def test_validate_should_return_true_for_valid_ssns(self):
        """Test validation returns true for valid SSNs."""
        assert self.ssn_attribute.validate("223-45-6789") is True
        assert self.ssn_attribute.validate("223456789") is True
        assert self.ssn_attribute.validate("2234567") is True
        assert self.ssn_attribute.validate("22345678") is True
        assert self.ssn_attribute.validate("223456789.0") is True
        assert self.ssn_attribute.validate("2234567.0") is True
        assert self.ssn_attribute.validate("22345678.00") is True

    def test_validate_should_return_false_for_invalid_ssns(self):
        """Test validation returns false for invalid SSNs."""
        assert self.ssn_attribute.validate(None) is False
        assert self.ssn_attribute.validate("") is False
        assert self.ssn_attribute.validate("12345") is False
        assert self.ssn_attribute.validate("123456") is False
        assert self.ssn_attribute.validate("1234567890") is False
        assert self.ssn_attribute.validate("000-00-0000") is False
        assert self.ssn_attribute.validate("666-00-0000") is False
        assert self.ssn_attribute.validate("123-11-0000") is False
        assert self.ssn_attribute.validate("123-00-1234") is False
        assert self.ssn_attribute.validate("000-45-6789") is False
        assert self.ssn_attribute.validate("900-45-6789") is False
        assert self.ssn_attribute.validate("999-45-6789") is False
        assert self.ssn_attribute.validate("ABCDEFGHI") is False
        assert self.ssn_attribute.validate("123-45-67AB") is False
        assert self.ssn_attribute.validate("123.456.789") is False
        assert self.ssn_attribute.validate("123456789.123") is False

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_ssn = "123456789"
        expected_result = "123-45-6789"
        results = []

        def normalize_ssn():
            """Function to be executed by each thread."""
            try:
                result = self.ssn_attribute.normalize(test_ssn)
                return result
            except Exception as e:
                pytest.fail(f"Thread failed with exception: {e}")

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all tasks
            futures = [executor.submit(normalize_ssn) for _ in range(thread_count)]

            # Collect results
            for future in as_completed(futures, timeout=15):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Thread execution failed: {e}")

        # Verify all threads got the same result
        assert len(results) == thread_count, f"Expected {thread_count} results, got {len(results)}"

        for result in results:
            assert result == expected_result

    def test_serialization(self):
        """Test serialization and deserialization of SocialSecurityNumberAttribute."""
        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(self.ssn_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various SSN values with both original and deserialized attributes
        test_values = ["123456789", "123-45-6789", "001-23-4567", "001234567", "999-99-9999", "999999999"]

        for value in test_values:
            # Test that attribute names match
            assert self.ssn_attribute.get_name() == deserialized_attribute.get_name()

            # Test that attribute aliases match
            assert self.ssn_attribute.get_aliases() == deserialized_attribute.get_aliases()

            # Test that normalization is identical
            assert self.ssn_attribute.normalize(value) == deserialized_attribute.normalize(value)

            # Test that validation is identical
            assert self.ssn_attribute.validate(value) == deserialized_attribute.validate(value)
