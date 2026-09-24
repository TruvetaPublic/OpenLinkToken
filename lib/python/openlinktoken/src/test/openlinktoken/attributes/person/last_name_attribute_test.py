# src/test/openlinktoken/attributes/person/test_last_name_attribute.py
# SPDX-License-Identifier: MIT

import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute


class TestLastNameAttribute:
    """Test cases for LastNameAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.last_name_attribute = LastNameAttribute()

    def test_get_name_should_return_last_name(self):
        """Test that get_name returns 'LastName'."""
        assert self.last_name_attribute.get_name() == "LastName"

    def test_get_aliases_should_return_last_name_and_surname(self):
        """Test that get_aliases returns LastName and Surname."""
        expected_aliases = ["LastName", "Surname"]
        actual_aliases = self.last_name_attribute.get_aliases()
        assert actual_aliases == expected_aliases

    def test_normalize_should_process_last_name(self):
        """Test basic normalization functionality."""
        input_name = "Doe"
        assert self.last_name_attribute.normalize(input_name) == "Doe", "Last name should be properly normalized"

    def test_normalize_accent(self):
        """Test normalization of names with accents."""
        name1 = "Gómez"
        name2 = "Gutiérrez"
        name3 = "Hernández"
        name4 = "Mäder"
        assert self.last_name_attribute.normalize(name1) == "Gomez"
        assert self.last_name_attribute.normalize(name2) == "Gutierrez"
        assert self.last_name_attribute.normalize(name3) == "Hernandez"
        assert self.last_name_attribute.normalize(name4) == "Mader"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Øst", "Ost"),
            ("Đỗ", "Do"),
            ("Œberg", "OEberg"),
        ],
    )
    def test_normalize_should_transliterate_latin_extended_last_names(self, value, expected):
        """Test normalization of last names that rely on Latin Extended transliteration."""
        assert self.last_name_attribute.normalize(value) == expected

    @pytest.mark.parametrize("value", ["Øst", "Đỗ", "Œberg"])
    def test_validate_should_accept_latin_extended_last_names(self, value):
        """Test validation acceptance for last names that rely on Latin Extended transliteration."""
        assert self.last_name_attribute.validate(value) is True
        assert self.last_name_attribute.validate(self.last_name_attribute.normalize(value)) is True

    def test_validate_should_return_true_for_valid_last_names_part1(self):
        """Test validation for valid last names (part 1)."""
        # Names with 3+ characters
        assert self.last_name_attribute.validate("Doe") is True, "3+ character last name should be allowed"
        assert self.last_name_attribute.validate("Smith-Jones") is True, "Hyphenated last name should be allowed"
        assert self.last_name_attribute.validate("  Wang  ") is True, "Name with whitespace should be allowed"

        # 2-character names with at least one vowel
        assert self.last_name_attribute.validate("Li") is True, "2-character name with a vowel should be allowed"
        assert self.last_name_attribute.validate("Wu") is True, "2-character name with a vowel should be allowed"
        assert self.last_name_attribute.validate("Ai") is True, "2-character name with a vowel should be allowed"
        assert self.last_name_attribute.validate("Im") is True, "2-character name with a vowel should be allowed"

    def test_validate_should_return_true_for_valid_last_names_part2(self):
        """Test validation for valid last names (part 2)."""
        # More 2-character names with at least one vowel
        assert self.last_name_attribute.validate("Ek") is True, "2-character name with a vowel should be allowed"
        assert self.last_name_attribute.validate("Ox") is True, "2-character name with a vowel should be allowed"
        assert self.last_name_attribute.validate("Uk") is True, "2-character name with a vowel should be allowed"

        # Special case for "Ng"
        assert self.last_name_attribute.validate("Ng") is True, "Ng should be allowed as a special case"
        assert self.last_name_attribute.validate("ng") is True, (
            "ng should be allowed as a special case (case insensitive)"
        )
        assert self.last_name_attribute.validate("NG") is True, (
            "NG should be allowed as a special case (case insensitive)"
        )

    def test_validate_should_return_false_for_invalid_last_names(self):
        """Test validation for invalid last names."""
        # Null or empty
        assert self.last_name_attribute.validate(None) is False, "Null value should not be allowed"
        assert self.last_name_attribute.validate("") is False, "Empty value should not be allowed"
        assert self.last_name_attribute.validate("  ") is False, "Whitespace-only value should not be allowed"

        # Single character
        assert self.last_name_attribute.validate("D") is False, "Single character last name should not be allowed"

        # 2-character names with no vowels (except Ng)
        assert self.last_name_attribute.validate("Mn") is False, "2-character name with no vowels should not be allowed"
        assert self.last_name_attribute.validate("Pq") is False, "2-character name with no vowels should not be allowed"
        assert self.last_name_attribute.validate("Xz") is False, "2-character name with no vowels should not be allowed"

    def test_validate_should_return_false_for_basic_placeholder_values(self):
        """Test basic placeholder values."""
        assert self.last_name_attribute.validate("Unknown") is False, "Unknown should not be allowed"
        assert self.last_name_attribute.validate("N/A") is False, "N/A should not be allowed"
        assert self.last_name_attribute.validate("None") is False, "None should not be allowed"
        assert self.last_name_attribute.validate("Test") is False, "Test should not be allowed"
        assert self.last_name_attribute.validate("Sample") is False, "Sample should not be allowed"
        assert self.last_name_attribute.validate("Anonymous") is False, "Anonymous should not be allowed"

    def test_validate_should_return_false_for_medical_placeholder_values(self):
        """Test medical/healthcare specific placeholders."""
        assert self.last_name_attribute.validate("Donor") is False, "Donor should not be allowed"
        assert self.last_name_attribute.validate("Patient") is False, "Patient should not be allowed"
        assert self.last_name_attribute.validate("patient not found") is False, (
            "patient not found should not be allowed"
        )
        assert self.last_name_attribute.validate("patientnotfound") is False, "patientnotfound should not be allowed"
        assert self.last_name_attribute.validate("<masked>") is False, "<masked> should not be allowed"

    def test_validate_should_return_false_for_testing_placeholder_values(self):
        """Test automation/testing specific placeholders."""
        assert self.last_name_attribute.validate("Automation Test") is False, "Automation Test should not be allowed"
        assert self.last_name_attribute.validate("Automationtest") is False, "Automationtest should not be allowed"
        assert self.last_name_attribute.validate("zzztrash") is False, "zzztrash should not be allowed"

    def test_validate_should_return_false_for_data_availability_placeholders(self):
        """Test data availability placeholders."""
        assert self.last_name_attribute.validate("Missing") is False, "Missing should not be allowed"
        assert self.last_name_attribute.validate("Unavailable") is False, "Unavailable should not be allowed"
        assert self.last_name_attribute.validate("Not Available") is False, "Not Available should not be allowed"
        assert self.last_name_attribute.validate("NotAvailable") is False, "NotAvailable should not be allowed"

    def test_validate_should_return_false_for_case_insensitive_placeholders(self):
        """Test case insensitivity (NotInValidator uses case-insensitive comparison)."""
        assert self.last_name_attribute.validate("UNKNOWN") is False, "UNKNOWN (uppercase) should not be allowed"
        assert self.last_name_attribute.validate("unknown") is False, "unknown (lowercase) should not be allowed"
        assert self.last_name_attribute.validate("UnKnOwN") is False, "UnKnOwN (mixed case) should not be allowed"

        assert self.last_name_attribute.validate("SAMPLE") is False, "SAMPLE (uppercase) should not be allowed"
        assert self.last_name_attribute.validate("sample") is False, "sample (lowercase) should not be allowed"

        assert self.last_name_attribute.validate("MISSING") is False, "MISSING (uppercase) should not be allowed"
        assert self.last_name_attribute.validate("missing") is False, "missing (lowercase) should not be allowed"

    def test_validate_should_return_true_for_valid_common_last_names(self):
        """Test validation for common legitimate last names."""
        # Common legitimate last names (all 3+ characters)
        assert self.last_name_attribute.validate("Smith") is True, "Smith should be allowed"
        assert self.last_name_attribute.validate("Johnson") is True, "Johnson should be allowed"
        assert self.last_name_attribute.validate("García") is True, "García should be allowed"
        assert self.last_name_attribute.validate("O'Connor") is True, "O'Connor should be allowed"
        assert self.last_name_attribute.validate("Smith-Jones") is True, "Smith-Jones should be allowed"
        assert self.last_name_attribute.validate("MacDonald") is True, "MacDonald should be allowed"
        assert self.last_name_attribute.validate("De La Cruz") is True, "De La Cruz should be allowed"

    def test_validate_should_return_true_for_two_character_last_names(self):
        """Test validation for two-character last names."""
        # Two-character last names with vowels
        assert self.last_name_attribute.validate("Lo") is True, "Lo should be allowed (2 chars with vowel)"
        assert self.last_name_attribute.validate("Wu") is True, "Wu should be allowed (2 chars with vowel)"
        assert self.last_name_attribute.validate("Xu") is True, "Xu should be allowed (2 chars with vowel)"

    def test_validate_should_return_true_for_edge_cases(self):
        """Test edge cases for validation."""
        # Edge cases for validation rule
        assert self.last_name_attribute.validate(" Ng ") is True, "Ng with spaces should be allowed"
        assert self.last_name_attribute.validate(" Wu ") is True, "Wu with spaces should be allowed"
        assert self.last_name_attribute.validate(" Ai ") is True, "Ai with spaces should be allowed"

    def test_validate_should_return_true_for_last_names_close_to_placeholders(self):
        """Test last names that might be similar to placeholders but are legitimate."""
        assert self.last_name_attribute.validate("Tester") is True, "Tester should be allowed (different from Test)"
        assert self.last_name_attribute.validate("Samples") is True, "Samples should be allowed (different from Sample)"
        assert self.last_name_attribute.validate("Patton") is True, "Patton should be allowed (different from Patient)"
        assert self.last_name_attribute.validate("Anderson") is True, (
            "Anderson should be allowed (different from Anonymous)"
        )

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_name = "Hernández"
        expected_result = "Hernandez"
        results = []

        def normalize_name():
            """Function to be executed by each thread."""
            try:
                result = self.last_name_attribute.normalize(test_name)
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

    def test_normalize_should_remove_generational_suffixes(self):
        """Test removal of various generational suffix formats."""
        # Test various generational suffix formats
        assert self.last_name_attribute.normalize("Smith Jr.") == "Smith"
        assert self.last_name_attribute.normalize("Johnson Junior") == "Johnson"
        assert self.last_name_attribute.normalize("Williams Sr.") == "Williams"
        assert self.last_name_attribute.normalize("Brown Senior") == "Brown"
        assert self.last_name_attribute.normalize("Davis II") == "Davis"
        assert self.last_name_attribute.normalize("Miller III") == "Miller"
        assert self.last_name_attribute.normalize("Wilson IV") == "Wilson"
        assert self.last_name_attribute.normalize("Moore V") == "Moore"
        assert self.last_name_attribute.normalize("Taylor VI") == "Taylor"
        assert self.last_name_attribute.normalize("Anderson VII") == "Anderson"
        assert self.last_name_attribute.normalize("Thomas VIII") == "Thomas"
        assert self.last_name_attribute.normalize("Jackson IX") == "Jackson"
        assert self.last_name_attribute.normalize("White X") == "White"

        # Test numeric suffixes
        assert self.last_name_attribute.normalize("Garcia 1st") == "Garcia"
        assert self.last_name_attribute.normalize("Martinez 2nd") == "Martinez"
        assert self.last_name_attribute.normalize("Robinson 3rd") == "Robinson"
        assert self.last_name_attribute.normalize("Clark 4th") == "Clark"
        assert self.last_name_attribute.normalize("Rodriguez 5th") == "Rodriguez"

        # Test case insensitive matching
        assert self.last_name_attribute.normalize("Lewis jr.") == "Lewis"
        assert self.last_name_attribute.normalize("Lee SENIOR") == "Lee"
        assert self.last_name_attribute.normalize("Walker ii") == "Walker"
        assert self.last_name_attribute.normalize("Hall JR") == "Hall"

        # Test suffixes without periods
        assert self.last_name_attribute.normalize("Allen Jr") == "Allen"
        assert self.last_name_attribute.normalize("Young Sr") == "Young"

    def test_normalize_should_remove_special_characters(self):
        """Test removal of dashes, spaces, and other special characters."""
        # Test removal of dashes, spaces, and other non-alphanumeric characters
        assert self.last_name_attribute.normalize("O'Connor") == "OConnor"
        assert self.last_name_attribute.normalize("Smith-Jones") == "SmithJones"
        assert self.last_name_attribute.normalize("Van Der Berg") == "VanDerBerg"
        assert self.last_name_attribute.normalize("Mc Donald") == "McDonald"
        assert self.last_name_attribute.normalize("De la Rosa") == "DelaRosa"

        # Test various special characters
        assert self.last_name_attribute.normalize("Smith@#$") == "Smith"
        assert self.last_name_attribute.normalize("Johnson_123") == "Johnson"
        assert self.last_name_attribute.normalize("Williams&Co") == "WilliamsCo"
        assert self.last_name_attribute.normalize("Brown*") == "Brown"
        assert self.last_name_attribute.normalize("Davis(Test)") == "DavisTest"
        assert self.last_name_attribute.normalize("Miller+Wilson") == "MillerWilson"
        assert self.last_name_attribute.normalize("García-López") == "GarciaLopez"

        # Test numbers mixed with letters
        assert self.last_name_attribute.normalize("Smith123") == "Smith"
        assert self.last_name_attribute.normalize("John5son") == "Johnson"
        assert self.last_name_attribute.normalize("Te$t123") == "Tet"

    def test_normalize_should_handle_generational_suffixes_and_special_characters(self):
        """Test combination of generational suffixes and special characters."""
        # Test combination of generational suffixes and special characters
        assert self.last_name_attribute.normalize("O'Connor Jr.") == "OConnor"
        assert self.last_name_attribute.normalize("Smith-Jones Senior") == "SmithJones"
        assert self.last_name_attribute.normalize("Mc Donald III") == "McDonald"
        assert self.last_name_attribute.normalize("Van Der Berg II") == "VanDerBerg"

        # Test with accents, suffixes, and special characters
        assert self.last_name_attribute.normalize("García-López Jr.") == "GarciaLopez"
        assert self.last_name_attribute.normalize("Hernández-Martinez Sr.") == "HernandezMartinez"
        assert self.last_name_attribute.normalize("Rodríguez O'Brien III") == "RodriguezOBrien"

    def test_normalize_should_handle_complex_combinations(self):
        """Test names with accents, special characters, and suffixes all together."""
        # Test names with accents, special characters, and suffixes all together
        assert self.last_name_attribute.normalize("Gómez-Rodríguez Jr.") == "GomezRodriguez"
        assert self.last_name_attribute.normalize("De-la-Croix Sr.") == "DelaCroix"
        assert self.last_name_attribute.normalize("O'Brien-McCarthy III") == "OBrienMcCarthy"
        assert self.last_name_attribute.normalize("Vander-Waal IV") == "VanderWaal"

        # Test edge cases
        assert self.last_name_attribute.normalize("Te$t-N@me Jr.") == "TetNme"
        assert self.last_name_attribute.normalize("Cömplex-Nâme123 Senior") == "ComplexName"

    def test_serialization(self):
        """Test serialization and deserialization."""
        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(self.last_name_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various values with both original and deserialized attributes
        test_values = [
            "Smith",
            "Johnson",
            "García",
            "Gómez",
            "Mäder",
            "van der Berg",
            "O'Connor",
            "Smith-Jones",
            "McDonald",
        ]

        for value in test_values:
            assert self.last_name_attribute.get_name() == deserialized_attribute.get_name(), (
                "Attribute names should match"
            )

            assert self.last_name_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            assert self.last_name_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert self.last_name_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    def test_validate_should_accept_special_case_ng_and_two_letter_names_with_vowels(self):
        """Test special case Ng and two-letter names with vowels."""
        # Special case: Ng (case variations)
        assert self.last_name_attribute.validate("Ng") is True, "Ng should be allowed as a special case"
        assert self.last_name_attribute.validate("NG") is True, "NG should be allowed as a special case"
        assert self.last_name_attribute.validate("ng") is True, "ng should be allowed as a special case"

        # Two-letter last names with vowels (consonant+vowel)
        assert self.last_name_attribute.validate("Li") is True, "Li should be allowed (consonant+vowel)"
        assert self.last_name_attribute.validate("Wu") is True, "Wu should be allowed (consonant+vowel)"
        assert self.last_name_attribute.validate("Xu") is True, "Xu should be allowed (consonant+vowel)"
        assert self.last_name_attribute.validate("Yi") is True, "Yi should be allowed (consonant+vowel)"

        # Two-letter last names with vowels (vowel+consonant)
        assert self.last_name_attribute.validate("Ox") is True, "Ox should be allowed (vowel+consonant)"
        assert self.last_name_attribute.validate("An") is True, "An should be allowed (vowel+consonant)"

    def test_validate_idempotency_should_be_stable(self):
        """Test that validation is idempotent: validate(x) == validate(normalize(x))"""
        # This ensures that normalized values can be re-validated successfully

        test_cases = [
            "N.M.",  # Normalizes to "NM" (2 consonants)
            "A.B.",  # Normalizes to "AB" (2 consonants)
            "J-K",  # Normalizes to "JK" (2 consonants)
            "Smith-Jones",  # Normalizes to "SmithJones"
            "O'Connor",  # Normalizes to "OConnor"
            "Van Der Berg",  # Normalizes to "VanDerBerg"
            "García-López",  # Normalizes to "GarciaLopez"
        ]

        for test_case in test_cases:
            normalized = self.last_name_attribute.normalize(test_case)
            valid_original = self.last_name_attribute.validate(test_case)
            valid_normalized = self.last_name_attribute.validate(normalized)

            # If original is valid, normalized should also be valid (idempotency)
            if valid_original:
                assert valid_normalized, (
                    f"Idempotency failed: '{test_case}' is valid but normalized '{normalized}' is not"
                )

            # Double normalization should produce the same result
            double_normalized = self.last_name_attribute.normalize(normalized)
            assert normalized == double_normalized, (
                f"Normalization not idempotent: normalize('{normalized}') != normalize(normalize('{test_case}'))"
            )

    def test_validate_normalized_values_should_pass_validation(self):
        """Specific test for the idempotency requirement"""
        # Validation should be stable: validate(x) == validate(normalize(x))

        # Test case 1: "N.M." normalizes to "NM" (2 consonants - INVALID)
        input1 = "N.M."
        normalized1 = self.last_name_attribute.normalize(input1)
        assert normalized1 == "NM", "N.M. should normalize to NM"

        valid1 = self.last_name_attribute.validate(input1)
        valid_normalized1 = self.last_name_attribute.validate(normalized1)
        assert valid1 == valid_normalized1, "Validation should be idempotent: validate('N.M.') == validate('NM')"
        assert not valid1, "N.M. should be invalid (normalizes to 2 consonants)"

        # Test case 2: "A.I." normalizes to "AI" (2 vowels - VALID)
        input2 = "A.I."
        normalized2 = self.last_name_attribute.normalize(input2)
        assert normalized2 == "AI", "A.I. should normalize to AI"

        valid2 = self.last_name_attribute.validate(input2)
        valid_normalized2 = self.last_name_attribute.validate(normalized2)
        assert valid2 == valid_normalized2, "Validation should be idempotent: validate('A.I.') == validate('AI')"
        assert valid2, "A.I. should be valid (normalizes to 2 vowels)"

    def test_validate_should_reject_values_normalizing_to_placeholders(self):
        """Test that values which normalize to placeholder values are rejected"""
        # This ensures idempotency: validate(x) should equal validate(normalize(x))

        # "TEST16" normalizes to "TEST" which is a placeholder
        assert self.last_name_attribute.validate("TEST16") is False, (
            "TEST16 should be rejected (normalizes to placeholder TEST)"
        )

        # "SAMPLE123" normalizes to "SAMPLE" which is a placeholder
        assert self.last_name_attribute.validate("SAMPLE123") is False, (
            "SAMPLE123 should be rejected (normalizes to placeholder SAMPLE)"
        )

        # "Unknown999" normalizes to "Unknown" which is a placeholder
        assert self.last_name_attribute.validate("Unknown999") is False, (
            "Unknown999 should be rejected (normalizes to placeholder Unknown)"
        )

        # "Patient-123" normalizes to "Patient123" then "Patient" which is a placeholder
        assert self.last_name_attribute.validate("Patient-123") is False, (
            "Patient-123 should be rejected (normalizes to placeholder Patient)"
        )

        # Verify normalization produces placeholder values
        assert self.last_name_attribute.normalize("TEST16") == "TEST"
        assert self.last_name_attribute.normalize("SAMPLE123") == "SAMPLE"
        assert self.last_name_attribute.normalize("Unknown999") == "Unknown"
        assert self.last_name_attribute.normalize("Patient-123") == "Patient"

        # Verify the normalized values themselves are invalid
        assert self.last_name_attribute.validate("TEST") is False, "TEST is a placeholder"
        assert self.last_name_attribute.validate("SAMPLE") is False, "SAMPLE is a placeholder"
        assert self.last_name_attribute.validate("Unknown") is False, "Unknown is a placeholder"
        assert self.last_name_attribute.validate("Patient") is False, "Patient is a placeholder"
