"""
Interoperability tests for OpenToken Java core library and Python CLI.

These tests validate two parity layers:
- the Python library reproduces the deterministic fixture values already asserted by
  the Java core-library integration test
- the Python CLI `tokenize` output matches a thin Java harness that uses the Java
  core library directly without any CLI layer
"""

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

# Add Python library to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "lib/python/opentoken/src/main"))


# These fixture values are intentionally kept aligned with the Java
# TokenGeneratorIntegrationTest so this interop job verifies the same
# deterministic library-level behavior from the Python side.
EXPECTED_TOKENS = {
    "T1": "02292af14559b4c2a28a772536b81760ad7b8ebac8ce49e8450ca0fa5044e37f",
    "T2": "0000000000000000000000000000000000000000000000000000000000000000",
    "T3": "a76c3bff664bec8d0f77b4b47ad555d212dc671949ed3cf1c1edef68733835b2",
    "T4": "21c3cf1fdb4fd45197e5def14d0228d26c56bcec1b8641079f9b9ec24f9a6a0b",
    "T5": "3756556f2323148cb57e1e13b1abcd457e1c1706a84ae83d522a3fc0ad43506d",
}


class InteroperabilityTooling:
    """Shared paths and test credentials for interoperability checks."""

    HASHING_KEY = "TestHashingKey123"
    JAVA_MAIN_CLASS = "com.truveta.opentoken.tools.TokenizeInteropHarness"

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.sample_csv = self.project_root / "resources/sample.csv"
        self.python_main = self.project_root / "lib/python/opentoken-cli/src/main/opentoken_cli/main.py"


class PythonCLI(InteroperabilityTooling):
    """Command-line wrapper for the Python OpenToken CLI."""

    def generate_tokenized_output(self, input_file: Path, output_file: Path) -> subprocess.CompletedProcess:
        """Run the Python CLI `tokenize` command and write CSV output."""
        cmd = [
            "python3",
            str(self.python_main),
            "tokenize",
            "-i",
            str(input_file),
            "-t",
            "csv",
            "-o",
            str(output_file),
            "-ot",
            "csv",
            "--hashingsecret",
            self.HASHING_KEY,
        ]

        env = {
            **os.environ,
            "PYTHONPATH": (
                f"{self.project_root / 'lib/python/opentoken/src/main'}:"
                f"{self.project_root / 'lib/python/opentoken-cli/src/main'}"
            ),
        }

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root, env=env, check=False)

        if result.returncode != 0:
            print(f"OpenToken-Python stderr: {result.stderr}")
            print(f"OpenToken-Python stdout: {result.stdout}")
            raise RuntimeError(f"OpenToken-Python failed with return code {result.returncode}: {result.stderr}")

        return result


class JavaLibraryHarness(InteroperabilityTooling):
    """Runs a thin Java harness built on the Java core library API."""

    def generate_tokenized_output(self, input_file: Path, output_file: Path) -> subprocess.CompletedProcess:
        """Run the Java harness that emits tokenize-compatible CSV output."""
        cmd = [
            "mvn",
            "-pl",
            "opentoken",
            "-DskipTests",
            "test-compile",
            "org.codehaus.mojo:exec-maven-plugin:3.5.0:java",
            f"-Dexec.mainClass={self.JAVA_MAIN_CLASS}",
            "-Dexec.classpathScope=test",
            f"-Dexec.args={input_file} {output_file} {self.HASHING_KEY}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root / "lib/java",
            check=False,
        )

        if result.returncode != 0:
            print(f"OpenToken-Java stderr: {result.stderr}")
            print(f"OpenToken-Java stdout: {result.stdout}")
            raise RuntimeError(f"OpenToken-Java failed with return code {result.returncode}: {result.stderr}")

        return result


class TokenValidator:
    """Utility class for validating and comparing tokens."""

    @staticmethod
    def load_csv_tokens(file_path: Path) -> Dict[str, Dict[str, str]]:
        """Load tokens from a CSV file, indexed by record and rule identifier."""
        tokens: Dict[str, Dict[str, str]] = {}

        with open(file_path, "r", encoding="utf-8") as file_handle:
            reader = csv.DictReader(file_handle)
            for row in reader:
                record_id = row.get("RecordId", "")
                rule_id = row.get("RuleId", "")
                token = row.get("Token", "")

                if record_id not in tokens:
                    tokens[record_id] = {}
                tokens[record_id][rule_id] = token

        return tokens

    @staticmethod
    def compare_token_files(file1: Path, file2: Path) -> Dict[str, Any]:
        """Compare two token CSV files and return detailed comparison results."""
        tokens1 = TokenValidator.load_csv_tokens(file1)
        tokens2 = TokenValidator.load_csv_tokens(file2)

        all_record_ids = set(tokens1.keys()) | set(tokens2.keys())

        comparison_results = {
            "total_records": len(all_record_ids),
            "matching_records": 0,
            "mismatched_records": [],
            "missing_in_file1": [],
            "missing_in_file2": [],
            "detailed_mismatches": {},
        }

        for record_id in all_record_ids:
            if record_id not in tokens1:
                comparison_results["missing_in_file1"].append(record_id)
                continue
            if record_id not in tokens2:
                comparison_results["missing_in_file2"].append(record_id)
                continue

            all_rule_ids = set(tokens1[record_id].keys()) | set(tokens2[record_id].keys())
            record_matches = True
            record_mismatches = {}

            for rule_id in all_rule_ids:
                token1 = tokens1[record_id].get(rule_id, "")
                token2 = tokens2[record_id].get(rule_id, "")

                if token1 != token2:
                    record_matches = False
                    record_mismatches[rule_id] = {
                        "file1_token": token1,
                        "file2_token": token2,
                    }

            if record_matches:
                comparison_results["matching_records"] += 1
            else:
                comparison_results["mismatched_records"].append(record_id)
                comparison_results["detailed_mismatches"][record_id] = record_mismatches

        return comparison_results


class TestTokenCompatibility:
    """Test token parity between the Java core library and the Python CLI."""

    def setup_method(self):
        """Set up environment for each method."""
        self.python_cli = PythonCLI()
        self.java_harness = JavaLibraryHarness()
        self.validator = TokenValidator()

    def test_python_library_matches_known_java_fixture_values(self):
        """Verify the Python library matches the deterministic Java fixture tokens."""
        from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
        from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
        from opentoken.attributes.person.last_name_attribute import LastNameAttribute
        from opentoken.attributes.person.sex_attribute import SexAttribute
        from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
        from opentoken.tokens.token_definition import TokenDefinition
        from opentoken.tokens.token_generator import TokenGenerator

        token_generator = TokenGenerator.from_transformers(TokenDefinition(), [])
        person_attributes = {
            FirstNameAttribute: "Alice",
            LastNameAttribute: "Wonderland",
            SocialSecurityNumberAttribute: "345-54-6795",
            SexAttribute: "F",
            BirthDateAttribute: "1993-08-10",
        }

        tokens = token_generator.get_all_tokens(person_attributes).tokens
        assert tokens == EXPECTED_TOKENS

    def test_java_library_harness_matches_python_cli_tokenize_output(self):
        """Compare Java library output with Python CLI tokenize output for the sample CSV."""
        print("\nTesting Java library harness against Python CLI tokenize output")
        print("-" * 30)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            java_output = temp_path / "java_tokenize_output.csv"
            python_output = temp_path / "python_tokenize_output.csv"

            self.java_harness.generate_tokenized_output(self.java_harness.sample_csv, java_output)
            self.python_cli.generate_tokenized_output(self.python_cli.sample_csv, python_output)

            comparison = self.validator.compare_token_files(java_output, python_output)

            assert not comparison["missing_in_file1"], f"Missing in Java output: {comparison['missing_in_file1']}"
            assert not comparison["missing_in_file2"], f"Missing in Python output: {comparison['missing_in_file2']}"
            assert not comparison["mismatched_records"], f"Token mismatches: {comparison['detailed_mismatches']}"
            assert comparison["total_records"] == comparison["matching_records"], comparison

            print("✅ Java core library and Python CLI token outputs match!")
            print("-" * 30)

    def test_metadata_consistency(self):
        """Test that the Python CLI produces metadata files with expected fields."""
        print("\nTesting Metadata Consistency")
        print("-" * 30)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            python_output = temp_path / "python_metadata_test.csv"

            self.python_cli.generate_tokenized_output(self.python_cli.sample_csv, python_output)

            python_metadata = python_output.with_suffix(".metadata.json")
            assert python_metadata.exists(), f"Python metadata file {python_metadata} not found"

            with open(python_metadata, "r", encoding="utf-8") as file_handle:
                python_meta = json.load(file_handle)

            expected_fields = ["Platform", "PythonVersion", "OpenTokenVersion", "TotalRows", "HashingSecretHash"]
            for field in expected_fields:
                assert field in python_meta, f"Python metadata missing expected field '{field}'"

            assert python_meta["Platform"] == "Python", (
                f"Expected Platform 'Python', got '{python_meta['Platform']}'"
            )

            print("✅ Metadata consistency verified!")
            print("-" * 30)


if __name__ == "__main__":
    test = TestTokenCompatibility()
    test.setup_method()

    try:
        test.test_python_library_matches_known_java_fixture_values()
        test.test_java_library_harness_matches_python_cli_tokenize_output()
        test.test_metadata_consistency()
        print("\n✅ ALL TESTS PASSED!")
    except Exception as error:
        print(f"\n❌ TEST FAILED: {str(error)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
