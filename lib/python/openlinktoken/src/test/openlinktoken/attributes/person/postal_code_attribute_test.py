# src/test/openlinktoken/attributes/person/test_postal_code_attribute.py
"""
Copyright (c) Truveta. All rights reserved.
"""

import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute


class TestPostalCodeAttribute:
    """Test cases for PostalCodeAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.postal_code_attribute = PostalCodeAttribute()

    def test_get_name_should_return_postal_code(self):
        """Test that get_name returns 'PostalCode'."""
        assert self.postal_code_attribute.get_name() == "PostalCode"

    def test_get_aliases_should_return_postal_code_and_zip_code(self):
        """Test that get_aliases returns PostalCode, ZipCode, ZIP3, ZIP4, and ZIP5."""
        expected_aliases = ["PostalCode", "ZipCode", "ZIP3", "ZIP4", "ZIP5"]
        actual_aliases = self.postal_code_attribute.get_aliases()
        assert actual_aliases == expected_aliases

    def test_normalize_should_return_first_5_digits(self):
        """Test normalization returns first 5 digits for US ZIP codes."""
        assert self.postal_code_attribute.normalize("10001-6789") == "10001"
        assert self.postal_code_attribute.normalize("10001") == "10001"

    def test_normalize_should_handle_canadian_postal_codes(self):
        """Test normalization of Canadian postal codes."""
        assert self.postal_code_attribute.normalize("K1B0A6") == "K1B 0A6"
        assert self.postal_code_attribute.normalize("k1b0a6") == "K1B 0A6"
        assert self.postal_code_attribute.normalize("K1B 0A6") == "K1B 0A6"
        assert self.postal_code_attribute.normalize("m5v3l9") == "M5V 3L9"
        assert self.postal_code_attribute.normalize("H3Z2Y7") == "H3Z 2Y7"
        assert self.postal_code_attribute.normalize("t2x1v4") == "T2X 1V4"

    def test_validate_should_return_true_for_valid_postal_codes(self):
        """Test validation for valid US postal codes."""
        assert self.postal_code_attribute.validate("95123 ") is True
        assert self.postal_code_attribute.validate(" 95123") is True
        assert self.postal_code_attribute.validate("95123") is True
        assert self.postal_code_attribute.validate("95123-6789") is True
        assert self.postal_code_attribute.validate("65201-6789") is True

    def test_validate_should_return_true_for_valid_canadian_postal_codes(self):
        """Test validation for valid Canadian postal codes."""
        assert self.postal_code_attribute.validate("K1B 0A7") is True
        assert self.postal_code_attribute.validate("K1B0A7") is True
        assert self.postal_code_attribute.validate("k1a 0a7") is True
        assert self.postal_code_attribute.validate("k1b0a7") is True
        assert self.postal_code_attribute.validate("M5V 3L9") is True
        assert self.postal_code_attribute.validate("H3Z 2Y7") is True
        assert self.postal_code_attribute.validate("T2X 1V4") is True
        assert self.postal_code_attribute.validate(" K1B 0A7 ") is True
        assert self.postal_code_attribute.validate("  K1B0A7  ") is True

    def test_normalize_should_handle_whitespace(self):
        """Test different types of whitespace handling."""
        attribute = PostalCodeAttribute()

        # Test different types of whitespace
        assert attribute.normalize("10001") == "10001", "No whitespace"
        assert attribute.normalize(" 10001") == "10001", "Leading space"
        assert attribute.normalize("10001 ") == "10001", "Trailing space"
        assert attribute.normalize(" 10001 ") == "10001", "Leading and trailing spaces"
        assert attribute.normalize("  10   001  ") == "10   001", "Multiple spaces"

    def test_normalize_should_not_handle_inner_whitespace(self):
        """Test that inner whitespace is preserved."""
        attribute = PostalCodeAttribute()

        # Test inner whitespace
        assert attribute.normalize("1 0 0 0 1") == "1 0 0 0 1", "Spaces between digits"
        assert attribute.normalize("10\t001") == "10\t001", "Tab character"
        assert attribute.normalize("10\n001") == "10\n001", "Newline character"
        assert attribute.normalize("10\r\n001") == "10\r\n001", "Carriage return and newline"
        assert attribute.normalize("K1A  0A7") == "K1A  0A7", (
            "Inner space should not be normalized for Canadian postal code"
        )

    def test_validate_should_return_false_for_invalid_postal_codes(self):
        """Test validation for invalid postal codes."""
        assert self.postal_code_attribute.validate(None) is False, "Null value should not be allowed"
        assert self.postal_code_attribute.validate("") is False, "Empty value should not be allowed"
        # Note: "1234" is now VALID (ZIP-4) with minLength=3 and gets padded to "12340"
        assert self.postal_code_attribute.validate("12") is False, "Too short postal code should not be allowed"
        assert self.postal_code_attribute.validate("12345") is False, "Invalid postal code should not be allowed"
        assert self.postal_code_attribute.validate("54321") is False, "Invalid postal code should not be allowed"
        assert self.postal_code_attribute.validate("123456") is False, "Long postal code should not be allowed"
        assert self.postal_code_attribute.validate("1234-5678") is False, "Invalid format should not be allowed"
        assert self.postal_code_attribute.validate("abcde") is False, "Non-numeric should not be allowed"

        # Invalid Canadian postal code formats
        assert self.postal_code_attribute.validate("K1A") is False, (
            "Incomplete Canadian postal code should not be allowed"
        )
        assert self.postal_code_attribute.validate("K1A 0A") is False, (
            "Incomplete Canadian postal code should not be allowed"
        )
        assert self.postal_code_attribute.validate("K1B 0A67") is False, (
            "Too long Canadian postal code should not be allowed"
        )
        assert self.postal_code_attribute.validate("K11 0A6") is False, (
            "Invalid Canadian postal code format should not be allowed"
        )
        assert self.postal_code_attribute.validate("KAA 0A6") is False, (
            "Invalid Canadian postal code format should not be allowed"
        )
        assert self.postal_code_attribute.validate("K1A 0AA") is False, (
            "Invalid Canadian postal code format should not be allowed"
        )

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_postal_code = "10001-6789"
        expected_result = "10001"
        results = []

        def normalize_postal_code():
            """Function to be executed by each thread."""
            try:
                result = self.postal_code_attribute.normalize(test_postal_code)
                return result
            except Exception as e:
                pytest.fail(f"Thread failed with exception: {e}")

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all tasks
            futures = [executor.submit(normalize_postal_code) for _ in range(thread_count)]

            # Collect results
            for future in as_completed(futures, timeout=15):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Thread execution failed: {e}")

        # Verify all threads got the same result
        assert len(results) == thread_count, f"Expected {thread_count} results, got {len(results)}"

        for i, result in enumerate(results):
            assert result == expected_result, f"Thread {i} got unexpected result: {result}"

    def test_normalize_thread_safety_barrier_style(self):
        """Test thread safety using barrier-style synchronization (closer to Java version)."""
        thread_count = 50  # Reduced for faster execution
        test_postal_code = "10001-6789"
        expected_result = "10001"
        results = []
        barrier = threading.Barrier(thread_count)
        start_event = threading.Event()

        def worker():
            """Worker function that waits for synchronization."""
            try:
                # Wait for all threads to be ready
                start_event.wait(timeout=10)

                # Synchronize all threads to increase contention
                barrier.wait(timeout=10)

                # Perform normalization
                result = self.postal_code_attribute.normalize(test_postal_code)
                results.append(result)

            except Exception as e:
                pytest.fail(f"Worker thread failed: {e}")

        # Create and start threads
        threads = []
        for i in range(thread_count):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # Start all threads simultaneously
        start_event.set()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=15)
            if thread.is_alive():
                pytest.fail("Thread did not complete in time")

        # Verify results
        assert len(results) == thread_count
        for result in results:
            assert result == expected_result

    def test_normalize_should_handle_edge_cases(self):
        """Test edge cases for normalization."""
        # Test ZIP-4 padding (4 digits with trailing space)
        assert self.postal_code_attribute.normalize("1234 ") == "12340"
        # Test short postal codes (less than 3 characters) - returned as-is
        assert self.postal_code_attribute.normalize("12") == "12"
        assert self.postal_code_attribute.normalize("1") == "1"

        # Test ZIP-3 padding
        assert self.postal_code_attribute.normalize("123") == "12300"

        # Test null and empty values
        assert self.postal_code_attribute.normalize(None) is None
        assert self.postal_code_attribute.normalize("") == ""

        # Test exactly 5 characters
        assert self.postal_code_attribute.normalize("10001") == "10001"
        assert self.postal_code_attribute.normalize(" 10001") == "10001"
        assert self.postal_code_attribute.normalize("10001-6789") == "10001"
        assert self.postal_code_attribute.normalize("100016789") == "10001"

    def test_serialization(self):
        """Test serialization and deserialization."""
        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(self.postal_code_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various postal code values with both original and deserialized attributes
        test_values = [
            "10001",
            "10001-6789",
            "90210-1234",
            "30301",
            "60601-2345",
            "K1B 0A7",
            "k1b0a7",
            "M5V 3L9",
            "H3Z2Y7",
        ]

        for value in test_values:
            assert self.postal_code_attribute.get_name() == deserialized_attribute.get_name(), (
                "Attribute names should match"
            )

            assert self.postal_code_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            assert self.postal_code_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert self.postal_code_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    @pytest.mark.parametrize(
        "input_code,expected_output",
        [
            ("10001-6789", "10001"),
            ("10001", "10001"),
            ("K1B0A6", "K1B 0A6"),
            ("k1b0a6", "K1B 0A6"),
            ("K1B 0A6", "K1B 0A6"),
            ("m5v3l9", "M5V 3L9"),
            ("H3Z2Y7", "H3Z 2Y7"),
            ("t2x1v4", "T2X 1V4"),
            ("95123-6789", "95123"),
            ("90210-1234", "90210"),
            ("  10001  ", "10001"),
            ("100016789", "10001"),
        ],
    )
    def test_normalize_parametrized(self, input_code, expected_output):
        """Parametrized test for normalization with various postal codes."""
        assert self.postal_code_attribute.normalize(input_code) == expected_output

    @pytest.mark.parametrize(
        "valid_code",
        [
            "95123 ",
            " 95123",
            "95123",
            "95123-6789",
            "65201-6789",
            "K1B 0A7",
            "K1B0A7",
            "k1a 0a7",
            "k1b0a7",
            "M5V 3L9",
            "H3Z 2Y7",
            "T2X 1V4",
            " K1B 0A7 ",
            "  K1B0A7  ",
        ],
    )
    def test_validate_valid_codes_parametrized(self, valid_code):
        """Parametrized test for validation with valid postal codes."""
        assert self.postal_code_attribute.validate(valid_code) is True

    @pytest.mark.parametrize(
        "invalid_code",
        [
            None,
            "",
            # Note: "1234" is now VALID (ZIP-4) with minLength=3 and gets padded to "12340"
            "12",  # Too short (only 2 digits)
            "12345",  # Invalid US ZIP (starts with invalid prefix based on validation)
            "54321",  # Invalid US ZIP (starts with invalid prefix based on validation)
            "123456",  # Invalid format (6 digits, not US or Canadian)
            "1234-5678",  # Invalid format
            "abcde",  # Invalid characters
            "K1A",  # Invalid Canadian (starts with K1A which is reserved)
            "K1A 0A",  # Invalid partial Canadian
            "K1B 0A67",  # Too long for Canadian
            "K11 0A6",  # Invalid Canadian format (digit in first position)
            "KAA 0A6",  # Invalid Canadian format (two letters in second position)
            "K1A 0AA",  # Invalid Canadian format (two letters in last position)
        ],
    )
    def test_validate_invalid_codes_parametrized(self, invalid_code):
        """Parametrized test for validation with invalid postal codes."""
        assert self.postal_code_attribute.validate(invalid_code) is False

    def test_normalize_us_zip_codes(self):
        """Test normalization of various US ZIP code formats."""
        # Standard 5-digit ZIP codes
        assert self.postal_code_attribute.normalize("10001") == "10001"
        assert self.postal_code_attribute.normalize("90210") == "90210"
        assert self.postal_code_attribute.normalize("30301") == "30301"

        # ZIP+4 format (should return first 5 digits)
        assert self.postal_code_attribute.normalize("10001-6789") == "10001"
        assert self.postal_code_attribute.normalize("90210-1234") == "90210"
        assert self.postal_code_attribute.normalize("30301-5678") == "30301"

        # 9-digit format without dash (should return first 5 digits)
        assert self.postal_code_attribute.normalize("100016789") == "10001"
        assert self.postal_code_attribute.normalize("902101234") == "90210"
        assert self.postal_code_attribute.normalize("303015678") == "30301"

        # With whitespace
        assert self.postal_code_attribute.normalize("  10001  ") == "10001"
        assert self.postal_code_attribute.normalize("  10001-6789  ") == "10001"

    def test_normalize_canadian_postal_codes_comprehensive(self):
        """Test comprehensive normalization of Canadian postal codes."""
        # Various formats should all normalize to A1A 1A1 format
        test_cases = [
            ("K1B0A6", "K1B 0A6"),
            ("k1b0a6", "K1B 0A6"),
            ("K1B 0A6", "K1B 0A6"),
            ("K1b 0a6", "K1B 0A6"),
            ("k1B0A6", "K1B 0A6"),
            ("m5v3l9", "M5V 3L9"),
            ("M5V3L9", "M5V 3L9"),
            ("M5v 3l9", "M5V 3L9"),
            ("H3Z2Y7", "H3Z 2Y7"),
            ("h3z2y7", "H3Z 2Y7"),
            ("t2x1v4", "T2X 1V4"),
            ("T2X1V4", "T2X 1V4"),
            ("v6b1a1", "V6B 1A1"),
            ("V6B1A1", "V6B 1A1"),
            ("n2l3g1", "N2L 3G1"),
            ("N2L3G1", "N2L 3G1"),
        ]

        for input_code, expected_output in test_cases:
            assert self.postal_code_attribute.normalize(input_code) == expected_output, (
                f"Failed for input: {input_code}"
            )

    def test_validate_comprehensive_us_zip_codes(self):
        """Test validation of various US ZIP code scenarios."""
        # Valid US ZIP codes (these should be valid according to the validator)
        valid_us_codes = [
            "95123",
            "95123-6789",
            "90210",
            "90210-1234",
            "10001",
            "10001-5678",
            "65201-6789",
            " 95123 ",
            "  95123-6789  ",
        ]

        for code in valid_us_codes:
            assert self.postal_code_attribute.validate(code) is True, f"Should be valid: {code}"

    def test_validate_comprehensive_canadian_postal_codes(self):
        """Test validation of various Canadian postal code scenarios."""
        # Valid Canadian postal codes
        valid_canadian_codes = [
            "K1B 0A7",  # Note: Using 0A7 instead of 0A6 to avoid placeholder
            "K1B0A7",
            "k1a 0a7",
            "k1b0a7",
            "M5V 3L9",
            "H3Z 2Y7",
            "T2X 1V4",
            "V6B 1A1",
            "N2L 3G1",
            " K1B 0A7 ",
            "  K1B0A7  ",
        ]

        for code in valid_canadian_codes:
            assert self.postal_code_attribute.validate(code) is True, f"Should be valid: {code}"

    def test_edge_cases_whitespace_handling(self):
        """Test various edge cases for whitespace handling."""
        # Leading/trailing whitespace should be trimmed
        assert self.postal_code_attribute.normalize("   10001   ") == "10001"
        assert self.postal_code_attribute.normalize("\t10001\t") == "10001"
        assert self.postal_code_attribute.normalize("\n10001\n") == "10001"

        # Canadian postal codes with whitespace
        assert self.postal_code_attribute.normalize("   K1B0A6   ") == "K1B 0A6"
        assert self.postal_code_attribute.normalize("\tK1B0A6\t") == "K1B 0A6"

        # Mixed whitespace types
        assert self.postal_code_attribute.normalize(" \t 10001 \n ") == "10001"
        assert self.postal_code_attribute.normalize(" \t K1B0A6 \n ") == "K1B 0A6"
