"""
Interoperability tests for OpenToken Java and Python implementations.

These tests validate that both implementations produce identical results
and can work with each other's outputs.
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
        java_jar_dir = self.project_root / "lib/java/opentoken-cli/target"
        jar_files = list(java_jar_dir.glob("opentoken-cli-*.jar"))
        if not jar_files:
            raise FileNotFoundError(f"No OpenToken CLI JAR found in {java_jar_dir}")
        self.java_jar_path = jar_files[0]
        self.python_main = self.project_root / "lib/python/opentoken-cli/src/main/opentoken_cli/main.py"
        self.sample_csv = self.project_root / "resources/sample.csv"
        self.decryptor_path = self.project_root / "tools/decryptor/decryptor.py"
        
        # Test credentials
        self.hashing_key = "TestHashingKey123"
        self.encryption_key = "TestEncryptionKey123456789012345"  # 32 chars for AES


class JavaCLI(OpenTokenCLI):
    """Command Line wrapper for OpenToken-Java."""
    
    def generate_tokens(self, input_file: Path, output_file: Path, ring_id: str = None) -> subprocess.CompletedProcess:
        """OpenToken-Java -- Generate tokens."""
        cmd = [
            "java", "-jar", str(self.java_jar_path),
            "-i", str(input_file),
            "-t", "csv",
            "-o", str(output_file),
            "-ot", "csv",
            "-h", self.hashing_key,
            "-e", self.encryption_key
        ]
        
        # Add ring-id if provided
        if ring_id:
            cmd.extend(["--ring-id", ring_id])
        
        print("Running Java\n")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        
        if result.returncode != 0:
            print(f"Java CLI stderr: {result.stderr}")
            print(f"Java CLI stdout: {result.stdout}")
            raise RuntimeError(f"Java CLI failed with return code {result.returncode}: {result.stderr}")
        
        return result


class PythonCLI(OpenTokenCLI):
    """Command Line wrapper for OpenToken-Python."""

    def generate_tokens(self, input_file: Path, output_file: Path, ring_id: str = None) -> subprocess.CompletedProcess:
        """OpenToken-Python -- Generate tokens"""
        cmd = [
            "python3", str(self.python_main),
            "-i", str(input_file),
            "-t", "csv",
            "-o", str(output_file),
            "-ot", "csv",
            "-h", self.hashing_key,
            "-e", self.encryption_key
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
    """Test token compatibility between OpenToken-Java and OpenToken-Python."""
    
    def setup_method(self):
        """Set up environment for each method."""
        self.java_cli = JavaCLI()
        self.python_cli = PythonCLI()
        self.validator = TokenValidator()
                
        # Create decryptor
        self.decryptor = TokenDecryptor(self.java_cli.encryption_key)
    
    def test_full_interoperability_pipeline(self):
        """
        Complete interoperability test with V1 tokens:
        1. Run Java implementation with fixed ring-id on sample.csv
        2. Run Python implementation with same ring-id on sample.csv  
        3. Decrypt both outputs
        4. Compare decrypted tokens to ensure they're identical
        5. Verify tokens have V1 format (ot.V1. prefix)
        """
        print("Running Java/Python V1 Token Interoperability Test")
        print("-" * 50)
        
        # Use fixed ring-id for both implementations to ensure identical outputs
        test_ring_id = "test-ring-12345678-1234-5678-1234-567812345678"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Output files
            java_output = temp_path / "java_output.csv"
            python_output = temp_path / "python_output.csv"
            java_decrypted = temp_path / "java_decrypted.csv"
            python_decrypted = temp_path / "python_decrypted.csv"
            
            print(f"Using ring-id: {test_ring_id}")
            print("1. Running Java implementation...")
            
            # Generate tokens with Java (with ring-id)
            self.java_cli.generate_tokens(
                input_file=self.java_cli.sample_csv,
                output_file=java_output,
                ring_id=test_ring_id
            )
            
            # Verify Java output exists
            assert java_output.exists(), f"Java output file {java_output} was not created"
            
            # Verify V1 format
            with open(java_output, 'r') as f:
                reader = csv.DictReader(f)
                first_row = next(reader)
                first_token = first_row['Token']
                assert first_token.startswith('ot.V1.'), \
                    f"Java token doesn't have V1 prefix: {first_token[:20]}..."
                print(f"   ✓ Java produces V1 tokens: {first_token[:30]}...")
            
            print("2. Running Python implementation...")
            
            # Generate tokens with Python (with same ring-id)
            self.python_cli.generate_tokens(
                input_file=self.python_cli.sample_csv,
                output_file=python_output,
                ring_id=test_ring_id
            )
            
            # Verify Python output exists
            assert python_output.exists(), f"Python output file {python_output} was not created"
            
            # Verify V1 format
            with open(python_output, 'r') as f:
                reader = csv.DictReader(f)
                first_row = next(reader)
                first_token = first_row['Token']
                assert first_token.startswith('ot.V1.'), \
                    f"Python token doesn't have V1 prefix: {first_token[:20]}..."
                print(f"   ✓ Python produces V1 tokens: {first_token[:30]}...")
            
            print("3. Decrypting outputs...")
            
            # Decrypt Java output
            self.decryptor.decrypt_file(java_output, java_decrypted)
            assert java_decrypted.exists(), f"Java decrypted file {java_decrypted} was not created"
            
            # Decrypt Python output
            self.decryptor.decrypt_file(python_output, python_decrypted)
            assert python_decrypted.exists(), f"Python decrypted file {python_decrypted} was not created"
            
            print("4. Comparing results...")
            
            # Compare decrypted outputs
            comparison = self.validator.compare_token_files(java_decrypted, python_decrypted)
            
            print(f"\nResults: {comparison['matching_records']}/{comparison['total_records']} records match")
            
            if comparison['mismatched_records']:
                print(f"⚠️  {len(comparison['mismatched_records'])} mismatched records found")
                for record_id in comparison['mismatched_records'][:3]:  # Show first 3
                    print(f"  • Record {record_id} differs")
            
            if comparison['missing_in_file1'] or comparison['missing_in_file2']:
                print(f"⚠️  Missing records - Java: {len(comparison['missing_in_file1'])}, Python: {len(comparison['missing_in_file2'])}")
            
            # Assert that all tokens match
            assert comparison['matching_records'] == comparison['total_records'], \
                f"Token mismatch found! {len(comparison['mismatched_records'])} records don't match"
            
            assert len(comparison['missing_in_file1']) == 0, \
                f"Records missing in Java output: {comparison['missing_in_file1']}"
            
            assert len(comparison['missing_in_file2']) == 0, \
                f"Records missing in Python output: {comparison['missing_in_file2']}"
            
            print(f"✅ SUCCESS: All {comparison['total_records']} records have identical V1 tokens!")
            print("-" * 50)
    
    def test_v1_token_interoperability(self):
        """
        Test V1 token format interoperability:
        1. Run Java implementation with ring-id on sample.csv
        2. Run Python implementation with same ring-id on sample.csv
        3. Decrypt both outputs
        4. Compare decrypted tokens to ensure they're identical
        5. Verify tokens have V1 format (ot.V1. prefix)
        """
        print("\nRunning Java/Python V1 Token Interoperability Test")
        print("-" * 50)
        
        test_ring_id = "test-ring-12345678-1234-5678-1234-567812345678"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Output files
            java_output = temp_path / "java_v1_output.csv"
            python_output = temp_path / "python_v1_output.csv"
            java_decrypted = temp_path / "java_v1_decrypted.csv"
            python_decrypted = temp_path / "python_v1_decrypted.csv"
            
            print(f"Using ring-id: {test_ring_id}")
            print("1. Running Java implementation with V1 format...")
            
            # Generate V1 tokens with Java
            self.java_cli.generate_tokens(
                input_file=self.java_cli.sample_csv,
                output_file=java_output,
                ring_id=test_ring_id
            )
            
            assert java_output.exists(), f"Java V1 output file {java_output} was not created"
            
            # Verify V1 format
            with open(java_output, 'r') as f:
                reader = csv.DictReader(f)
                first_row = next(reader)
                first_token = first_row['Token']
                assert first_token.startswith('ot.V1.'), \
                    f"Java token doesn't have V1 prefix: {first_token[:20]}..."
                print(f"   ✓ Java produces V1 tokens: {first_token[:30]}...")
            
            print("2. Running Python implementation with V1 format...")
            
            # Generate V1 tokens with Python
            self.python_cli.generate_tokens(
                input_file=self.python_cli.sample_csv,
                output_file=python_output,
                ring_id=test_ring_id
            )
            
            assert python_output.exists(), f"Python V1 output file {python_output} was not created"
            
            # Verify V1 format
            with open(python_output, 'r') as f:
                reader = csv.DictReader(f)
                first_row = next(reader)
                first_token = first_row['Token']
                assert first_token.startswith('ot.V1.'), \
                    f"Python token doesn't have V1 prefix: {first_token[:20]}..."
                print(f"   ✓ Python produces V1 tokens: {first_token[:30]}...")
            
            print("3. Decrypting V1 outputs...")
            
            # Decrypt Java output
            self.decryptor.decrypt_file(java_output, java_decrypted)
            assert java_decrypted.exists(), f"Java V1 decrypted file {java_decrypted} was not created"
            
            # Decrypt Python output
            self.decryptor.decrypt_file(python_output, python_decrypted)
            assert python_decrypted.exists(), f"Python V1 decrypted file {python_decrypted} was not created"
            
            print("4. Comparing results...")
            
            # Compare decrypted outputs
            comparison = self.validator.compare_token_files(java_decrypted, python_decrypted)
            
            print(f"\nResults: {comparison['matching_records']}/{comparison['total_records']} records match")
            
            if comparison['mismatched_records']:
                print(f"⚠️  {len(comparison['mismatched_records'])} mismatched records found")
                for record_id in comparison['mismatched_records'][:3]:
                    print(f"  • Record {record_id} differs")
            
            if comparison['missing_in_file1'] or comparison['missing_in_file2']:
                print(f"⚠️  Missing records - Java: {len(comparison['missing_in_file1'])}, Python: {len(comparison['missing_in_file2'])}")
            
            # Assert that all tokens match
            assert comparison['matching_records'] == comparison['total_records'], \
                f"V1 Token mismatch found! {len(comparison['mismatched_records'])} records don't match"
            
            assert len(comparison['missing_in_file1']) == 0, \
                f"Records missing in Java V1 output: {comparison['missing_in_file1']}"
            
            assert len(comparison['missing_in_file2']) == 0, \
                f"Records missing in Python V1 output: {comparison['missing_in_file2']}"
            
            print(f"✅ SUCCESS: All {comparison['total_records']} V1 records have identical tokens!")
            print("-" * 50)
    
    def test_metadata_consistency(self):
        """Test that metadata files are consistent between implementations."""
        print("\nTesting Metadata Consistency")
        print("-" * 30)
        
        # Use fixed ring-id for consistent comparison
        test_ring_id = "test-ring-12345678-1234-5678-1234-567812345678"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            java_output = temp_path / "java_metadata_test.csv"
            python_output = temp_path / "python_metadata_test.csv"
            
            # Generate tokens with both implementations (with same ring-id)
            self.java_cli.generate_tokens(self.java_cli.sample_csv, java_output, ring_id=test_ring_id)
            self.python_cli.generate_tokens(self.python_cli.sample_csv, python_output, ring_id=test_ring_id)
            
            # Check for metadata files
            java_metadata = java_output.with_suffix('.metadata.json')
            python_metadata = python_output.with_suffix('.metadata.json')
            
            assert java_metadata.exists(), f"Java metadata file {java_metadata} not found"
            assert python_metadata.exists(), f"Python metadata file {python_metadata} not found"
            
            # Load and compare metadata
            with open(java_metadata, 'r') as f:
                java_meta = json.load(f)
            
            with open(python_metadata, 'r') as f:  
                python_meta = json.load(f)
            
            # Compare essential fields (platform-specific fields will differ)
            essential_fields = ['OutputFormat']
            
            for field in essential_fields:
                if field in java_meta and field in python_meta:
                    assert java_meta[field] == python_meta[field], \
                        f"Metadata field '{field}' differs: Java={java_meta[field]}, Python={python_meta[field]}"
            
            print("✅ Metadata consistency verified!")
            print("-" * 30)

if __name__ == "__main__":
    # Run the test manually
    test = TestTokenCompatibility()
    test.setup_method()
    
    try:
        test.test_full_interoperability_pipeline()
        test.test_v1_token_interoperability()
        test.test_metadata_consistency()
                
        print("\n✅ ALL TESTS PASSED!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
