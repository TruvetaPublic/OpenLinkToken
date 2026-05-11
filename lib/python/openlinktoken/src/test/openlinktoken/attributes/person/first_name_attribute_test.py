# src/test/openlinktoken/attributes/person/test_first_name_attribute.py
# SPDX-License-Identifier: MIT

import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute


class TestFirstNameAttribute:
    """Test cases for FirstNameAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.first_name_attribute = FirstNameAttribute()

    def test_get_name_should_return_first_name(self):
        """Test that get_name returns 'FirstName'."""
        assert self.first_name_attribute.get_name() == "FirstName"

    def test_get_aliases_should_return_first_name_and_given_name(self):
        """Test that get_aliases returns FirstName and GivenName."""
        expected_aliases = ["FirstName", "GivenName"]
        actual_aliases = self.first_name_attribute.get_aliases()
        assert actual_aliases == expected_aliases

    def test_normalize_should_return_unchanged_value(self):
        """Test that normalize returns the input value unchanged for basic names."""
        input_value = "John"
        assert self.first_name_attribute.normalize(input_value) == input_value

    def test_normalize_accent(self):
        """Test normalization of names with accents."""
        name1 = "José"
        name2 = "Vũ"
        name3 = "François"
        name4 = "Renée"
        assert self.first_name_attribute.normalize(name1) == "Jose"
        assert self.first_name_attribute.normalize(name2) == "Vu"
        assert self.first_name_attribute.normalize(name3) == "Francois"
        assert self.first_name_attribute.normalize(name4) == "Renee"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Łukasz", "Lukasz"),
            ("Søren", "Soren"),
            ("Ægir", "AEgir"),
        ],
    )
    def test_normalize_should_transliterate_latin_extended_names(self, value, expected):
        """Test normalization of first names that rely on Latin Extended transliteration."""
        assert self.first_name_attribute.normalize(value) == expected

    @pytest.mark.parametrize("value", ["Łukasz", "Søren", "Ægir"])
    def test_validate_should_accept_latin_extended_names(self, value):
        """Test validation acceptance for first names that rely on Latin Extended transliteration."""
        assert self.first_name_attribute.validate(value) is True
        assert self.first_name_attribute.validate(self.first_name_attribute.normalize(value)) is True

    def test_validate_should_return_true_for_any_non_empty_string(self):
        """Test validation for non-empty strings."""
        assert self.first_name_attribute.validate("John") is True
        assert self.first_name_attribute.validate("Jane Doe") is True
        assert self.first_name_attribute.validate("J") is True

    def test_validate_should_return_false_for_null_or_empty_string(self):
        """Test validation for null or empty strings."""
        assert self.first_name_attribute.validate(None) is False, "Null value should not be allowed"
        assert self.first_name_attribute.validate("") is False, "Empty value should not be allowed"
        assert self.first_name_attribute.validate("John123") is True, "Non-empty value should be allowed"

    def test_validate_should_return_false_for_basic_placeholder_values(self):
        """Test basic placeholder values."""
        assert self.first_name_attribute.validate("Unknown") is False, "Unknown should not be allowed"
        assert self.first_name_attribute.validate("N/A") is False, "N/A should not be allowed"
        assert self.first_name_attribute.validate("None") is False, "None should not be allowed"
        assert self.first_name_attribute.validate("Test") is False, "Test should not be allowed"
        assert self.first_name_attribute.validate("Sample") is False, "Sample should not be allowed"
        assert self.first_name_attribute.validate("Anonymous") is False, "Anonymous should not be allowed"

    def test_validate_should_return_false_for_medical_placeholder_values(self):
        """Test medical/healthcare specific placeholders."""
        assert self.first_name_attribute.validate("Donor") is False, "Donor should not be allowed"
        assert self.first_name_attribute.validate("Patient") is False, "Patient should not be allowed"
        assert self.first_name_attribute.validate("patient not found") is False, (
            "patient not found should not be allowed"
        )
        assert self.first_name_attribute.validate("patientnotfound") is False, "patientnotfound should not be allowed"
        assert self.first_name_attribute.validate("<masked>") is False, "<masked> should not be allowed"

    def test_validate_should_return_false_for_testing_placeholder_values(self):
        """Test automation/testing specific placeholders."""
        assert self.first_name_attribute.validate("Automation Test") is False, "Automation Test should not be allowed"
        assert self.first_name_attribute.validate("Automationtest") is False, "Automationtest should not be allowed"
        assert self.first_name_attribute.validate("zzztrash") is False, "zzztrash should not be allowed"

    def test_validate_should_return_false_for_data_availability_placeholders(self):
        """Test data availability placeholders."""
        assert self.first_name_attribute.validate("Missing") is False, "Missing should not be allowed"
        assert self.first_name_attribute.validate("Unavailable") is False, "Unavailable should not be allowed"
        assert self.first_name_attribute.validate("Not Available") is False, "Not Available should not be allowed"
        assert self.first_name_attribute.validate("NotAvailable") is False, "NotAvailable should not be allowed"

    def test_validate_should_return_false_for_case_insensitive_placeholders(self):
        """Test case insensitivity (NotInValidator uses case-insensitive comparison)."""
        assert self.first_name_attribute.validate("UNKNOWN") is False, "UNKNOWN (uppercase) should not be allowed"
        assert self.first_name_attribute.validate("unknown") is False, "unknown (lowercase) should not be allowed"
        assert self.first_name_attribute.validate("UnKnOwN") is False, "UnKnOwN (mixed case) should not be allowed"

        assert self.first_name_attribute.validate("SAMPLE") is False, "SAMPLE (uppercase) should not be allowed"
        assert self.first_name_attribute.validate("sample") is False, "sample (lowercase) should not be allowed"

        assert self.first_name_attribute.validate("MISSING") is False, "MISSING (uppercase) should not be allowed"
        assert self.first_name_attribute.validate("missing") is False, "missing (lowercase) should not be allowed"

    def test_validate_should_return_true_for_valid_names(self):
        """Test that legitimate names are still allowed."""
        assert self.first_name_attribute.validate("John") is True, "John should be allowed"
        assert self.first_name_attribute.validate("Jane") is True, "Jane should be allowed"
        assert self.first_name_attribute.validate("Michael") is True, "Michael should be allowed"
        assert self.first_name_attribute.validate("Sarah") is True, "Sarah should be allowed"
        assert self.first_name_attribute.validate("José") is True, "José should be allowed"
        assert self.first_name_attribute.validate("François") is True, "François should be allowed"
        assert self.first_name_attribute.validate("Mary-Jane") is True, "Mary-Jane should be allowed"
        assert self.first_name_attribute.validate("Jean-Luc") is True, "Jean-Luc should be allowed"

    def test_validate_should_return_true_for_names_close_to_placeholders(self):
        """Test names that might be similar to placeholders but are legitimate."""
        assert self.first_name_attribute.validate("Tester") is True, "Tester should be allowed (different from Test)"
        assert self.first_name_attribute.validate("Samples") is True, (
            "Samples should be allowed (different from Sample)"
        )
        assert self.first_name_attribute.validate("Patrice") is True, (
            "Patrice should be allowed (different from Patient)"
        )
        assert self.first_name_attribute.validate("Ana") is True, "Ana should be allowed (different from Anonymous)"

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_name = "François"
        expected_result = "Francois"
        results = []

        def normalize_name():
            """Function to be executed by each thread."""
            try:
                result = self.first_name_attribute.normalize(test_name)
                return result
            except Exception as e:
                pytest.fail(f"Thread failed with exception: {e}")

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all tasks
            futures = [executor.submit(normalize_name) for _ in range(thread_count)]

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

    def test_normalize_should_remove_titles(self):
        """Test various title formats."""
        assert self.first_name_attribute.normalize("Mr. John") == "John"
        assert self.first_name_attribute.normalize("Mrs. Jane") == "Jane"
        assert self.first_name_attribute.normalize("Ms. Sarah") == "Sarah"
        assert self.first_name_attribute.normalize("Miss Emily") == "Emily"
        assert self.first_name_attribute.normalize("Dr. Robert") == "Robert"
        assert self.first_name_attribute.normalize("Prof. Alice") == "Alice"
        assert self.first_name_attribute.normalize("Capt. James") == "James"
        assert self.first_name_attribute.normalize("Sir William") == "William"
        assert self.first_name_attribute.normalize("Col. David") == "David"
        assert self.first_name_attribute.normalize("Gen. Michael") == "Michael"
        assert self.first_name_attribute.normalize("Cmdr. Thomas") == "Thomas"
        assert self.first_name_attribute.normalize("Lt. Daniel") == "Daniel"
        assert self.first_name_attribute.normalize("Rabbi Samuel") == "Samuel"
        assert self.first_name_attribute.normalize("Father Joseph") == "Joseph"
        assert self.first_name_attribute.normalize("Brother Francis") == "Francis"
        assert self.first_name_attribute.normalize("Sister Mary") == "Mary"
        assert self.first_name_attribute.normalize("Hon. Charles") == "Charles"
        assert self.first_name_attribute.normalize("Honorable George") == "George"
        assert self.first_name_attribute.normalize("Reverend Matthew") == "Matthew"
        assert self.first_name_attribute.normalize("Doctor Andrew") == "Andrew"

        # Test titles without periods
        assert self.first_name_attribute.normalize("Mr John") == "John"
        assert self.first_name_attribute.normalize("Dr Jane") == "Jane"

        # Test case insensitive titles
        assert self.first_name_attribute.normalize("MR. John") == "John"
        assert self.first_name_attribute.normalize("dr. Jane") == "Jane"
        assert self.first_name_attribute.normalize("MS Sarah") == "Sarah"

    def test_normalize_should_remove_middle_initials(self):
        """Test middle initial removal."""
        assert self.first_name_attribute.normalize("John A") == "John"
        assert self.first_name_attribute.normalize("Jane B") == "Jane"
        assert self.first_name_attribute.normalize("Robert C") == "Robert"
        assert self.first_name_attribute.normalize("Mary X") == "Mary"

        # Test with periods in middle initials
        assert self.first_name_attribute.normalize("John A.") == "John"
        assert self.first_name_attribute.normalize("Jane B.") == "Jane"

        # Test names that shouldn't have initials removed
        assert self.first_name_attribute.normalize("Jo") == "Jo"
        assert self.first_name_attribute.normalize("A") == "A"

    def test_normalize_should_handle_titles_and_initials_together(self):
        """Test combination of title and middle initial."""
        assert self.first_name_attribute.normalize("Dr. John A") == "John"
        assert self.first_name_attribute.normalize("Mrs. Jane B.") == "Jane"
        assert self.first_name_attribute.normalize("Prof. Robert C") == "Robert"
        assert self.first_name_attribute.normalize("Miss Mary X") == "Mary"

        # Test with accents, titles, and initials
        assert self.first_name_attribute.normalize("Mr. José A") == "Jose"
        assert self.first_name_attribute.normalize("Dr. François B.") == "Francois"

    def test_normalize_should_remove_non_alphabetic_characters(self):
        """Test removal of dashes, spaces, and other non-alphanumeric characters."""
        assert self.first_name_attribute.normalize("John-Doe") == "JohnDoe"
        assert self.first_name_attribute.normalize("Mary Jane") == "MaryJane"
        assert self.first_name_attribute.normalize("Ann-Marie") == "AnnMarie"
        assert self.first_name_attribute.normalize("Jean-Luc") == "JeanLuc"

        # Test with numbers and special characters
        assert self.first_name_attribute.normalize("John123") == "John"
        assert self.first_name_attribute.normalize("Jane@#$") == "Jane"
        assert self.first_name_attribute.normalize("Robert_Smith") == "RobertSmith"

    def test_serialization_should_preserve_state(self):
        """Test serialization and deserialization."""
        original_attribute = FirstNameAttribute()

        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(original_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        test_values = [
            "John",
            "Mr. John A",
            "Dr. Jane B.",
            "José",
            "François",
            "John-Paul",
            "Mary Jane",
            "Prof. Robert C",
        ]

        for value in test_values:
            assert original_attribute.get_name() == deserialized_attribute.get_name(), "Attribute names should match"

            assert original_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            assert original_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert original_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    def test_normalize_should_handle_edge_cases_in_title_removal(self):
        """Test edge cases for title removal."""
        assert self.first_name_attribute.normalize("Mr.") == "Mr"
        assert self.first_name_attribute.normalize("Sir") == "Sir"
        assert self.first_name_attribute.normalize("Prof.") == "Prof"
        assert self.first_name_attribute.normalize("General") == "General"

        # Test titles with only spaces after
        assert self.first_name_attribute.normalize("Mr. ") == "Mr"
        assert self.first_name_attribute.normalize("    Dr.   ") == "Dr"

        # Test multiple titles (should only remove the first one)
        assert self.first_name_attribute.normalize("Mr. Smith") == "Smith"
        assert self.first_name_attribute.normalize("Dr. Johnson") == "Johnson"

        # Test names that start with title-like words but aren't titles
        assert self.first_name_attribute.normalize("Drew") == "Drew"
        assert self.first_name_attribute.normalize("Profeta") == "Profeta"
        assert self.first_name_attribute.normalize("Missy") == "Missy"

        # Test titles with unusual spacing
        assert self.first_name_attribute.normalize("Mr.John") == "MrJohn"
        assert self.first_name_attribute.normalize("Dr.  Jane") == "Jane"

    def test_normalize_should_remove_generational_suffixes(self):
        """Test various generational suffix formats in first names."""
        assert self.first_name_attribute.normalize("John Jr.") == "John"
        assert self.first_name_attribute.normalize("Jane Junior") == "Jane"
        assert self.first_name_attribute.normalize("Robert Sr.") == "Robert"
        assert self.first_name_attribute.normalize("Mary Senior") == "Mary"
        assert self.first_name_attribute.normalize("William II") == "William"
        assert self.first_name_attribute.normalize("Elizabeth III") == "Elizabeth"
        assert self.first_name_attribute.normalize("Charles IV") == "Charles"
        assert self.first_name_attribute.normalize("David V") == "David"
        assert self.first_name_attribute.normalize("Michael VI") == "Michael"
        assert self.first_name_attribute.normalize("Sarah VII") == "Sarah"
        assert self.first_name_attribute.normalize("James VIII") == "James"
        assert self.first_name_attribute.normalize("Anna IX") == "Anna"
        assert self.first_name_attribute.normalize("Thomas X") == "Thomas"

        # Test numeric suffixes
        assert self.first_name_attribute.normalize("Daniel 1st") == "Daniel"
        assert self.first_name_attribute.normalize("Emily 2nd") == "Emily"
        assert self.first_name_attribute.normalize("Andrew 3rd") == "Andrew"
        assert self.first_name_attribute.normalize("Jennifer 4th") == "Jennifer"
        assert self.first_name_attribute.normalize("Christopher 5th") == "Christopher"

        # Test case insensitive matching
        assert self.first_name_attribute.normalize("Matthew jr.") == "Matthew"
        assert self.first_name_attribute.normalize("Jessica SENIOR") == "Jessica"
        assert self.first_name_attribute.normalize("Nicholas ii") == "Nicholas"
        assert self.first_name_attribute.normalize("Amanda JR") == "Amanda"

        # Test suffixes without periods
        assert self.first_name_attribute.normalize("Joshua Jr") == "Joshua"
        assert self.first_name_attribute.normalize("Michelle Sr") == "Michelle"

    def test_normalize_should_handle_titles_and_generational_suffixes_together(self):
        """Test combination of titles and generational suffixes."""
        assert self.first_name_attribute.normalize("Dr. John Jr.") == "John"
        assert self.first_name_attribute.normalize("Mrs. Jane Sr.") == "Jane"
        assert self.first_name_attribute.normalize("Prof. Robert III") == "Robert"
        assert self.first_name_attribute.normalize("Miss Mary II") == "Mary"
        assert self.first_name_attribute.normalize("Mr. William Senior") == "William"
        assert self.first_name_attribute.normalize("Dr. Elizabeth Junior") == "Elizabeth"

        # Test with accents, titles, and generational suffixes
        assert self.first_name_attribute.normalize("Mr. José Jr.") == "Jose"
        assert self.first_name_attribute.normalize("Dr. François Sr.") == "Francois"
        assert self.first_name_attribute.normalize("Mrs. María III") == "Maria"

        # Test with middle initials, titles, and suffixes
        assert self.first_name_attribute.normalize("Dr. John A. Jr.") == "John"
        assert self.first_name_attribute.normalize("Mrs. Jane B Sr.") == "Jane"
        assert self.first_name_attribute.normalize("Prof. Robert C III") == "Robert"

        # Test different orders and combinations
        assert self.first_name_attribute.normalize("Sir Charles IV") == "Charles"
        assert self.first_name_attribute.normalize("Col. David V") == "David"
        assert self.first_name_attribute.normalize("Gen. Michael VI") == "Michael"

    @pytest.mark.parametrize(
        "input_name,expected_output",
        [
            ("José", "Jose"),
            ("Vũ", "Vu"),
            ("François", "Francois"),
            ("Renée", "Renee"),
            ("Mr. John", "John"),
            ("Dr. Jane B.", "Jane"),
            ("John-Paul", "JohnPaul"),
            ("Mary Jane", "MaryJane"),
            ("Prof. Robert C", "Robert"),
        ],
    )
    def test_normalize_parametrized(self, input_name, expected_output):
        """Parametrized test for normalization with various inputs."""
        assert self.first_name_attribute.normalize(input_name) == expected_output

    @pytest.mark.parametrize(
        "valid_name",
        [
            "John",
            "Jane",
            "Michael",
            "Sarah",
            "José",
            "François",
            "Mary-Jane",
            "Jean-Luc",
            "Tester",
            "Samples",
            "Patrice",
            "Ana",
        ],
    )
    def test_validate_valid_names_parametrized(self, valid_name):
        """Parametrized test for validation with valid names."""
        assert self.first_name_attribute.validate(valid_name) is True

    @pytest.mark.parametrize(
        "invalid_name",
        [
            None,
            "",
            "Unknown",
            "N/A",
            "None",
            "Test",
            "Sample",
            "Anonymous",
            "Donor",
            "Patient",
            "patient not found",
            "patientnotfound",
            "<masked>",
            "Automation Test",
            "Automationtest",
            "zzztrash",
            "Missing",
            "Unavailable",
            "Not Available",
            "NotAvailable",
            "UNKNOWN",
            "unknown",
            "UnKnOwN",
        ],
    )
    def test_validate_invalid_names_parametrized(self, invalid_name):
        """Parametrized test for validation with invalid names."""
        assert self.first_name_attribute.validate(invalid_name) is False

    def test_validate_idempotency_should_be_stable(self):
        """Test that validation is idempotent: validate(x) == validate(normalize(x))"""
        # This ensures that normalized values can be re-validated successfully

        test_cases = [
            "A.B.",  # Normalizes to "AB"
            "N.M.",  # Normalizes to "NM"
            "Dr. John",  # Normalizes to "John"
            "Mary-Ann",  # Normalizes to "MaryAnn"
            "José",  # Normalizes to "Jose"
            "Jean-Marc",  # Normalizes to "JeanMarc"
        ]

        for test_case in test_cases:
            normalized = self.first_name_attribute.normalize(test_case)
            valid_original = self.first_name_attribute.validate(test_case)
            valid_normalized = self.first_name_attribute.validate(normalized)

            # If original is valid, normalized should also be valid (idempotency)
            if valid_original:
                assert valid_normalized, (
                    f"Idempotency failed: '{test_case}' is valid but normalized '{normalized}' is not"
                )

            # Double normalization should produce the same result
            double_normalized = self.first_name_attribute.normalize(normalized)
            assert normalized == double_normalized, (
                f"Normalization not idempotent: normalize('{normalized}') != normalize(normalize('{test_case}'))"
            )

    def test_validate_normalized_values_should_pass_validation(self):
        """Specific test for idempotency issue"""
        # "A.B." should normalize to "AB" and "AB" should still be valid

        input_value = "A.B."
        normalized = self.first_name_attribute.normalize(input_value)

        assert normalized == "AB", "A.B. should normalize to AB"

        # The normalized value should pass validation
        original_valid = self.first_name_attribute.validate(input_value)
        normalized_valid = self.first_name_attribute.validate(normalized)

        if original_valid:
            assert normalized_valid, "Normalized value 'AB' should be valid if original 'A.B.' was valid"

    def test_validate_should_reject_values_normalizing_to_placeholders(self):
        """Test that values which normalize to placeholder values are rejected"""
        # This ensures idempotency: validate(x) should equal validate(normalize(x))

        # "TEST16" normalizes to "TEST" which is a placeholder
        assert self.first_name_attribute.validate("TEST16") is False, (
            "TEST16 should be rejected (normalizes to placeholder TEST)"
        )

        # "SAMPLE123" normalizes to "SAMPLE" which is a placeholder
        assert self.first_name_attribute.validate("SAMPLE123") is False, (
            "SAMPLE123 should be rejected (normalizes to placeholder SAMPLE)"
        )

        # "Unknown999" normalizes to "Unknown" which is a placeholder
        assert self.first_name_attribute.validate("Unknown999") is False, (
            "Unknown999 should be rejected (normalizes to placeholder Unknown)"
        )

        # "Patient-123" normalizes to "Patient123" then "Patient" which is a placeholder
        assert self.first_name_attribute.validate("Patient-123") is False, (
            "Patient-123 should be rejected (normalizes to placeholder Patient)"
        )

        # Verify normalization produces placeholder values
        assert self.first_name_attribute.normalize("TEST16") == "TEST"
        assert self.first_name_attribute.normalize("SAMPLE123") == "SAMPLE"
        assert self.first_name_attribute.normalize("Unknown999") == "Unknown"
        assert self.first_name_attribute.normalize("Patient-123") == "Patient"

        # Verify the normalized values themselves are invalid
        assert self.first_name_attribute.validate("TEST") is False, "TEST is a placeholder"
        assert self.first_name_attribute.validate("SAMPLE") is False, "SAMPLE is a placeholder"
        assert self.first_name_attribute.validate("Unknown") is False, "Unknown is a placeholder"
        assert self.first_name_attribute.validate("Patient") is False, "Patient is a placeholder"
