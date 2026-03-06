"""
Copyright (c) Truveta. All rights reserved.
"""

import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from opentoken.attributes.person.sex_attribute import SexAttribute


class TestSexAttribute:
    """Test cases for SexAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.sex_attribute = SexAttribute()

    def test_get_name_should_return_sex(self):
        """Test that get_name returns 'Sex'."""
        assert self.sex_attribute.get_name() == "Sex"

    def test_get_aliases_should_return_sex_and_gender(self):
        """Test that get_aliases returns Sex and Gender."""
        expected_aliases = ["Sex", "Gender"]
        actual_aliases = self.sex_attribute.get_aliases()
        assert actual_aliases == expected_aliases

    def test_normalize_should_return_male_for_m_input(self):
        """Test normalization for male values."""
        assert self.sex_attribute.normalize("M") == "Male"
        assert self.sex_attribute.normalize("Male") == "Male"
        assert self.sex_attribute.normalize("m") == "Male"
        assert self.sex_attribute.normalize("male") == "Male"

    def test_normalize_should_return_female_for_f_input(self):
        """Test normalization for female values."""
        assert self.sex_attribute.normalize("F") == "Female"
        assert self.sex_attribute.normalize("Female") == "Female"
        assert self.sex_attribute.normalize("f") == "Female"
        assert self.sex_attribute.normalize("female") == "Female"

    def test_normalize_should_return_none_for_invalid_input(self):
        """Test normalization for invalid values."""
        assert self.sex_attribute.normalize("X") is None, "Invalid value should return None"
        assert self.sex_attribute.normalize("Other") is None, "Invalid value should return None"

    def test_validate_should_return_true_for_valid_values(self):
        """Test validation for valid sex values."""
        assert self.sex_attribute.validate("M") is True
        assert self.sex_attribute.validate("F") is True
        assert self.sex_attribute.validate("Male") is True
        assert self.sex_attribute.validate("Female") is True

    def test_validate_should_return_false_for_invalid_values(self):
        """Test validation for invalid sex values."""
        assert self.sex_attribute.validate("X") is False, "Invalid value should not be allowed"
        assert self.sex_attribute.validate("Other") is False, "Invalid value should not be allowed"
        assert self.sex_attribute.validate("") is False, "Empty value should not be allowed"
        assert self.sex_attribute.validate(None) is False, "None value should not be allowed"

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_sex = "m"
        expected_result = "Male"
        results = []

        def normalize_sex():
            """Function to be executed by each thread."""
            try:
                result = self.sex_attribute.normalize(test_sex)
                return result
            except Exception as e:
                pytest.fail(f"Thread failed with exception: {e}")

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all tasks
            futures = [executor.submit(normalize_sex) for _ in range(thread_count)]

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
        test_sex = "m"
        expected_result = "Male"
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
                result = self.sex_attribute.normalize(test_sex)
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

    def test_serialization(self):
        """Test serialization and deserialization of SexAttribute."""
        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(self.sex_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various sex values with both original and deserialized attributes
        test_values = ["M", "Male", "m", "male", "F", "Female", "f", "female", "U", "Unknown", "u", "unknown"]

        for value in test_values:
            # Test that attribute names match
            assert self.sex_attribute.get_name() == deserialized_attribute.get_name(), "Attribute names should match"

            # Test that attribute aliases match
            assert self.sex_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            # Test that normalization is identical
            original_normalized = self.sex_attribute.normalize(value)
            deserialized_normalized = deserialized_attribute.normalize(value)
            assert original_normalized == deserialized_normalized, (
                f"Normalization should be identical for value: {value}"
            )

            # Test that validation is identical
            original_valid = self.sex_attribute.validate(value)
            deserialized_valid = deserialized_attribute.validate(value)
            assert original_valid == deserialized_valid, f"Validation should be identical for value: {value}"

    @pytest.mark.parametrize(
        "input_value,expected_output",
        [
            ("M", "Male"),
            ("Male", "Male"),
            ("m", "Male"),
            ("male", "Male"),
            ("F", "Female"),
            ("Female", "Female"),
            ("f", "Female"),
            ("female", "Female"),
            ("X", None),
            ("Other", None),
            ("U", None),
            ("Unknown", None),
            ("", None),
            (None, None),
        ],
    )
    def test_normalize_parametrized(self, input_value, expected_output):
        """Parametrized test for normalization with various inputs."""
        assert self.sex_attribute.normalize(input_value) == expected_output

    @pytest.mark.parametrize("valid_value", ["M", "F", "Male", "Female", "m", "f", "male", "female"])
    def test_validate_valid_values_parametrized(self, valid_value):
        """Parametrized test for validation with valid values."""
        assert self.sex_attribute.validate(valid_value) is True

    @pytest.mark.parametrize(
        "invalid_value",
        ["X", "Other", "", None, "U", "Unknown", "u", "unknown", "MALE", "FEMALE", "Man", "Woman", "1", "0"],
    )
    def test_validate_invalid_values_parametrized(self, invalid_value):
        """Parametrized test for validation with invalid values."""
        assert self.sex_attribute.validate(invalid_value) is False

    def test_normalize_case_insensitivity(self):
        """Test that normalization is case insensitive for valid values."""
        # Test various case combinations for male
        assert self.sex_attribute.normalize("M") == "Male"
        assert self.sex_attribute.normalize("m") == "Male"
        assert self.sex_attribute.normalize("Male") == "Male"
        assert self.sex_attribute.normalize("male") == "Male"

        # Test various case combinations for female
        assert self.sex_attribute.normalize("F") == "Female"
        assert self.sex_attribute.normalize("f") == "Female"
        assert self.sex_attribute.normalize("Female") == "Female"
        assert self.sex_attribute.normalize("female") == "Female"

    def test_validate_case_insensitivity(self):
        """Test that validation is case insensitive for valid values."""
        # Test various case combinations for male
        assert self.sex_attribute.validate("M") is True
        assert self.sex_attribute.validate("m") is True
        assert self.sex_attribute.validate("Male") is True
        assert self.sex_attribute.validate("male") is True

        # Test various case combinations for female
        assert self.sex_attribute.validate("F") is True
        assert self.sex_attribute.validate("f") is True
        assert self.sex_attribute.validate("Female") is True
        assert self.sex_attribute.validate("female") is True

    def test_normalize_edge_cases(self):
        """Test edge cases for normalization."""
        # Test empty and None values
        assert self.sex_attribute.normalize("") is None
        assert self.sex_attribute.normalize(None) is None

        # Test whitespace handling
        assert self.sex_attribute.normalize(" M ") == "Male"
        assert self.sex_attribute.normalize("  F  ") == "Female"
        assert self.sex_attribute.normalize("\tMale\t") == "Male"
        assert self.sex_attribute.normalize("\nFemale\n") == "Female"

        # Test invalid values return None
        assert self.sex_attribute.normalize("X") is None
        assert self.sex_attribute.normalize("Other") is None
        assert self.sex_attribute.normalize("Unknown") is None
        assert self.sex_attribute.normalize("U") is None
        assert self.sex_attribute.normalize("Non-binary") is None
        assert self.sex_attribute.normalize("1") is None
        assert self.sex_attribute.normalize("0") is None

    def test_validate_edge_cases(self):
        """Test edge cases for validation."""
        # Test whitespace handling
        assert self.sex_attribute.validate(" M ") is True
        assert self.sex_attribute.validate("  F  ") is True
        assert self.sex_attribute.validate("\tMale\t") is True
        assert self.sex_attribute.validate("\nFemale\n") is True

        # Test whitespace-only values
        assert self.sex_attribute.validate("   ") is False
        assert self.sex_attribute.validate("\t") is False
        assert self.sex_attribute.validate("\n") is False

        # Test numeric values
        assert self.sex_attribute.validate("1") is False
        assert self.sex_attribute.validate("0") is False
        assert self.sex_attribute.validate("123") is False
