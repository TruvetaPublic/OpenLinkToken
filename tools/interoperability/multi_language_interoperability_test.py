"""
Interoperability tests for OpenToken Python CLI.

These tests validate that the Python CLI produces correct token output
and consistent metadata.
"""

import subprocess
import tempfile
import json
import os
import sys
import csv
from pathlib import Path
from typing import Dict, Any

# Add Python library to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib/python/opentoken/src/main"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

from decryptor.decryptor import decrypt_tokens


class OpenTokenCLI:
    """Base class for OpenToken CLI operations."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.python_main = self.project_root / "lib/python/opentoken-cli/src/main/opentoken_cli/main.py"
        self.sample_csv = self.project_root / "resources/sample.csv"
        self.decryptor_path = self.project_root / "tools/decryptor/decryptor.py"
        
        # Test credentials
        self.hashing_key = "TestHashingKey123"
        self.encryption_key = "TestEncryptionKey123456789012345"  # 32 chars for AES


class PythonCLI(OpenTokenCLI):
    """Command Line wrapper for OpenToken-Python."""

    def generate_tokens(self, input_file: Path, output_file: Path, ring_id: str = None) -> subprocess.CompletedProcess:
        """OpenToken-Python -- Generate tokens"""
        cmd = [
            "python3", str(self.python_main),
            "package",
            "-i", str(input_file),
            "-t", "csv",
            "-o", str(output_file),
            "-ot", "csv",
            "--hashingsecret", self.hashing_key,
            "--encryptionkey", self.encryption_key
        ]
        
        # Add ring-id if provided
        if ring_id:
            cmd.extend(["--ring-id", ring_id])
        
        env = {**os.environ, "PYTHONPATH": str(self.project_root / "lib/python/opentoken/src/main") + ":" + str(self.project_root / "lib/python/opentoken-cli/src/main")}
        
        print("Running Python\n")
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              cwd=self.project_root, env=env)
        
        if result.returncode != 0:
            print(f"OpenToken-Python stderr: {result.stderr}")
            print(f"OpenToken-Python stdout: {result.stdout}")
            raise RuntimeError(f"OpenToken-Python failed with return code {result.returncode}: {result.stderr}")
        
        return result


class TokenDecryptor:
    """Wrapper for the decryptor tool."""
    
    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key
        self.project_root = Path(__file__).parent.parent.parent
    
    def decrypt_file(self, input_file: Path, output_file: Path):
        """Decrypt tokens from input file to output file."""
        print(f"  Decrypting {input_file.name}...")
        
        # Use the decryptor function directly
        decrypt_tokens(self.encryption_key, str(input_file), str(output_file))
        
        if not output_file.exists():
            raise RuntimeError(f"Decryption failed - output file {output_file} not created")


class TokenValidator:
    """Utility class for validating and comparing tokens."""
    
    @staticmethod
    def load_csv_tokens(file_path: Path) -> Dict[str, Dict[str, str]]:
        """Load tokens from CSV file, indexed by RecordId and RuleId."""
        tokens = {}
        
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record_id = row.get('RecordId', '')
                rule_id = row.get('RuleId', '')
                token = row.get('Token', '')
                
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
            'total_records': len(all_record_ids),
            'matching_records': 0,
            'mismatched_records': [],
            'missing_in_file1': [],
            'missing_in_file2': [],
            'detailed_mismatches': {}
        }
        
        for record_id in all_record_ids:
            if record_id not in tokens1:
                comparison_results['missing_in_file1'].append(record_id)
                continue
            if record_id not in tokens2:
                comparison_results['missing_in_file2'].append(record_id)
                continue
            
            # Compare all rule IDs for this record
            all_rule_ids = set(tokens1[record_id].keys()) | set(tokens2[record_id].keys())
            record_matches = True
            record_mismatches = {}
            
            for rule_id in all_rule_ids:
                token1 = tokens1[record_id].get(rule_id, '')
                token2 = tokens2[record_id].get(rule_id, '')
                
                if token1 != token2:
                    record_matches = False
                    record_mismatches[rule_id] = {
                        'file1_token': token1,
                        'file2_token': token2
                    }
            
            if record_matches:
                comparison_results['matching_records'] += 1
            else:
                comparison_results['mismatched_records'].append(record_id)
                comparison_results['detailed_mismatches'][record_id] = record_mismatches
        
        return comparison_results


class TestTokenCompatibility:
    """Test token output consistency for OpenToken Python CLI."""
    
    def setup_method(self):
        """Set up environment for each method."""
        self.python_cli = PythonCLI()
        self.validator = TokenValidator()
                
        # Create decryptor
        self.decryptor = TokenDecryptor(self.python_cli.encryption_key)
    
    def test_metadata_consistency(self):
        """Test that the Python CLI produces metadata files with expected fields."""
        print("\nTesting Metadata Consistency")
        print("-" * 30)
        
        # Use fixed ring-id for consistent output
        test_ring_id = "test-ring-12345678-1234-5678-1234-567812345678"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            python_output = temp_path / "python_metadata_test.csv"
            
            # Generate tokens with Python CLI
            self.python_cli.generate_tokens(self.python_cli.sample_csv, python_output, ring_id=test_ring_id)
            
            # Check for metadata file
            python_metadata = python_output.with_suffix('.metadata.json')
            
            assert python_metadata.exists(), f"Python metadata file {python_metadata} not found"
            
            # Load and verify metadata has expected fields
            with open(python_metadata, 'r') as f:  
                python_meta = json.load(f)
            
            expected_fields = ['OutputFormat']
            for field in expected_fields:
                assert field in python_meta, f"Python metadata missing expected field '{field}'"
            
            print("✅ Metadata consistency verified!")
            print("-" * 30)

if __name__ == "__main__":
    # Run the test manually
    test = TestTokenCompatibility()
    test.setup_method()
    
    try:
        test.test_metadata_consistency()
                
        print("\n✅ ALL TESTS PASSED!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
