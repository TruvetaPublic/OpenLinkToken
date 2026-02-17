"""
Interoperability tests for OpenToken Java, Python, and Node.js implementations.

These tests validate that all implementations produce identical results
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
        java_jar_dir = self.project_root / "lib/java/opentoken/target"
        jar_files = list(java_jar_dir.glob("opentoken-*.jar"))
        if not jar_files:
            raise FileNotFoundError(f"No OpenToken JAR found in {java_jar_dir}")
        self.java_jar_path = jar_files[0]
        self.python_main = self.project_root / "lib/python/opentoken/src/main/opentoken/main.py"
        self.nodejs_main = self.project_root / "lib/nodejs/opentoken/dist/Main.js"
        self.sample_csv = self.project_root / "resources/sample.csv"
        self.decryptor_path = self.project_root / "tools/decryptor/decryptor.py"
        
        # Test credentials
        self.hashing_key = "TestHashingKey123"
        self.encryption_key = "TestEncryptionKey123456789012345"  # 32 chars for AES


class JavaCLI(OpenTokenCLI):
    """Command Line wrapper for OpenToken-Java."""
    
    def generate_tokens(self, input_file: Path, output_file: Path) -> subprocess.CompletedProcess:
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
        
        print("Running Java\n")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        
        if result.returncode != 0:
            print(f"Java CLI stderr: {result.stderr}")
            print(f"Java CLI stdout: {result.stdout}")
            raise RuntimeError(f"Java CLI failed with return code {result.returncode}: {result.stderr}")
        
        return result


class PythonCLI(OpenTokenCLI):
    """Command Line wrapper for OpenToken-Python."""

    def generate_tokens(self, input_file: Path, output_file: Path) -> subprocess.CompletedProcess:
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
        
        env = {**os.environ, "PYTHONPATH": str(self.project_root / "lib/python/opentoken/src/main")}
        
        print("Running Python\n")
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              cwd=self.project_root, env=env)
        
        if result.returncode != 0:
            print(f"OpenToken-Python stderr: {result.stderr}")
            print(f"OpenToken-Python stdout: {result.stdout}")
            raise RuntimeError(f"OpenToken-Python failed with return code {result.returncode}: {result.stderr}")
        
        return result


class NodeJSCLI(OpenTokenCLI):
    """Command Line wrapper for OpenToken-Node.js."""

    def generate_tokens(self, input_file: Path, output_file: Path) -> subprocess.CompletedProcess:
        """OpenToken-Node.js -- Generate tokens"""
        cmd = [
            "node", str(self.nodejs_main),
            "-i", str(input_file),
            "-o", str(output_file),
            "-k", self.hashing_key,
            "-e", self.encryption_key
        ]
        
        print("Running Node.js\n")
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              cwd=self.project_root)
        
        if result.returncode != 0:
            print(f"OpenToken-Node.js stderr: {result.stderr}")
            print(f"OpenToken-Node.js stdout: {result.stdout}")
            raise RuntimeError(f"OpenToken-Node.js failed with return code {result.returncode}: {result.stderr}")
        
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
    """Test token compatibility between OpenToken-Java, OpenToken-Python, and OpenToken-Node.js."""
    
    def setup_method(self):
        """Set up environment for each method."""
        self.java_cli = JavaCLI()
        self.python_cli = PythonCLI()
        self.nodejs_cli = NodeJSCLI()
        self.validator = TokenValidator()
                
        # Create decryptor
        self.decryptor = TokenDecryptor(self.java_cli.encryption_key)
    
    def test_full_interoperability_pipeline(self):
        """
        Complete interoperability test:
        1. Run Java implementation on sample.csv
        2. Run Python implementation on sample.csv
        3. Run Node.js implementation on sample.csv
        4. Decrypt all outputs
        5. Compare decrypted tokens to ensure they're all identical
        """
        print("Running Java/Python/Node.js Interoperability Test")
        print("-" * 50)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Output files
            java_output = temp_path / "java_output.csv"
            python_output = temp_path / "python_output.csv"
            nodejs_output = temp_path / "nodejs_output.csv"
            java_decrypted = temp_path / "java_decrypted.csv"
            python_decrypted = temp_path / "python_decrypted.csv"
            nodejs_decrypted = temp_path / "nodejs_decrypted.csv"
            
            print("1. Running Java implementation...")
            
            # Generate tokens with Java
            self.java_cli.generate_tokens(
                input_file=self.java_cli.sample_csv,
                output_file=java_output
            )
            
            # Verify Java output exists
            assert java_output.exists(), f"Java output file {java_output} was not created"
            
            print("2. Running Python implementation...")
            
            # Generate tokens with Python
            self.python_cli.generate_tokens(
                input_file=self.python_cli.sample_csv,
                output_file=python_output
            )
            
            # Verify Python output exists
            assert python_output.exists(), f"Python output file {python_output} was not created"
            
            print("3. Running Node.js implementation...")
            
            # Generate tokens with Node.js
            self.nodejs_cli.generate_tokens(
                input_file=self.nodejs_cli.sample_csv,
                output_file=nodejs_output
            )
            
            # Verify Node.js output exists
            assert nodejs_output.exists(), f"Node.js output file {nodejs_output} was not created"
            
            print("4. Decrypting outputs...")
            
            # Decrypt Java output
            self.decryptor.decrypt_file(java_output, java_decrypted)
            assert java_decrypted.exists(), f"Java decrypted file {java_decrypted} was not created"
            
            # Decrypt Python output
            self.decryptor.decrypt_file(python_output, python_decrypted)
            assert python_decrypted.exists(), f"Python decrypted file {python_decrypted} was not created"
            
            # Decrypt Node.js output
            self.decryptor.decrypt_file(nodejs_output, nodejs_decrypted)
            assert nodejs_decrypted.exists(), f"Node.js decrypted file {nodejs_decrypted} was not created"
            
            print("5. Comparing results...")
            
            # Compare Java vs Python
            print("  Comparing Java vs Python...")
            comparison_java_python = self.validator.compare_token_files(java_decrypted, python_decrypted)
            
            # Compare Java vs Node.js
            print("  Comparing Java vs Node.js...")
            comparison_java_nodejs = self.validator.compare_token_files(java_decrypted, nodejs_decrypted)
            
            # Compare Python vs Node.js
            print("  Comparing Python vs Node.js...")
            comparison_python_nodejs = self.validator.compare_token_files(python_decrypted, nodejs_decrypted)
            
            # Print results
            print(f"\nJava vs Python: {comparison_java_python['matching_records']}/{comparison_java_python['total_records']} records match")
            print(f"Java vs Node.js: {comparison_java_nodejs['matching_records']}/{comparison_java_nodejs['total_records']} records match")
            print(f"Python vs Node.js: {comparison_python_nodejs['matching_records']}/{comparison_python_nodejs['total_records']} records match")
            
            # Check for mismatches
            all_comparisons = [comparison_java_python, comparison_java_nodejs, comparison_python_nodejs]
            comparison_names = ["Java vs Python", "Java vs Node.js", "Python vs Node.js"]
            
            for comp_name, comparison in zip(comparison_names, all_comparisons):
                if comparison['mismatched_records']:
                    print(f"⚠️  {comp_name}: {len(comparison['mismatched_records'])} mismatched records found")
                    for record_id in comparison['mismatched_records'][:3]:  # Show first 3
                        print(f"    • Record {record_id} differs")
                
                if comparison['missing_in_file1'] or comparison['missing_in_file2']:
                    print(f"⚠️  {comp_name}: Missing records - File1: {len(comparison['missing_in_file1'])}, File2: {len(comparison['missing_in_file2'])}")
            
            # Assert that all tokens match across all implementations
            for comp_name, comparison in zip(comparison_names, all_comparisons):
                assert comparison['matching_records'] == comparison['total_records'], \
                    f"{comp_name}: Token mismatch found! {len(comparison['mismatched_records'])} records don't match"
                
                assert len(comparison['missing_in_file1']) == 0, \
                    f"{comp_name}: Records missing in first file: {comparison['missing_in_file1']}"
                
                assert len(comparison['missing_in_file2']) == 0, \
                    f"{comp_name}: Records missing in second file: {comparison['missing_in_file2']}"
            
            print(f"\n✅ SUCCESS: All {comparison_java_python['total_records']} records have identical tokens across Java, Python, and Node.js!")
            print("-" * 50)
    
    def test_metadata_consistency(self):
        """Test that metadata files are consistent between implementations."""
        print("\nTesting Metadata Consistency")
        print("-" * 30)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            java_output = temp_path / "java_metadata_test.csv"
            python_output = temp_path / "python_metadata_test.csv"
            nodejs_output = temp_path / "nodejs_metadata_test.csv"
            
            # Generate tokens with all implementations
            self.java_cli.generate_tokens(self.java_cli.sample_csv, java_output)
            self.python_cli.generate_tokens(self.python_cli.sample_csv, python_output)
            self.nodejs_cli.generate_tokens(self.nodejs_cli.sample_csv, nodejs_output)
            
            # Check for metadata files
            java_metadata = java_output.with_suffix('.metadata.json')
            python_metadata = python_output.with_suffix('.metadata.json')
            nodejs_metadata = nodejs_output.with_suffix('.metadata.json')
            
            assert java_metadata.exists(), f"Java metadata file {java_metadata} not found"
            assert python_metadata.exists(), f"Python metadata file {python_metadata} not found"
            assert nodejs_metadata.exists(), f"Node.js metadata file {nodejs_metadata} not found"
            
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
        test.test_metadata_consistency()
                
        print("\nALL TESTS PASSED!")
        
    except Exception as e:
        print(f"\nTEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
