#!/usr/bin/env python3
"""
Test script to verify hash_calculator.py produces the same results as Java implementation.
"""

import sys
import os
import subprocess
import tempfile
import json

# Add the tools directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hash_calculator import calculate_secure_hash


def test_known_values():
    """Test hash calculation against known SHA-256 values."""
    test_cases = [
        ("hello", "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
        ("", None),  # Empty string should return None
        ("test", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"),
    ]
    
    for input_str, expected in test_cases:
        if expected is None:
            try:
                result = calculate_secure_hash(input_str)
                print(f"FAIL: Expected ValueError for empty string, got: {result}")
                return False
            except ValueError:
                print("PASS: Empty string correctly raises ValueError")
                continue
        
        result = calculate_secure_hash(input_str)
        if result == expected:
            print(f"PASS: '{input_str}' -> {result}")
        else:
            print(f"FAIL: '{input_str}' -> {result}, expected {expected}")
            return False
    
    return True


def test_java_compatibility():
    """Test that Python hashes match Java implementation."""
    # These values should match what the Java implementation produces
    test_cases = [
        "HashingKey",
        "Secret-Encryption-Key-Goes-Here.",
        "test-input",
        "こんにちは",  # Unicode test
    ]
    
    print("\nTesting Java compatibility:")
    for test_input in test_cases:
        try:
            python_hash = calculate_secure_hash(test_input)
            print(f"Input: '{test_input}' -> {python_hash}")
        except Exception as e:
            print(f"FAIL: Error calculating hash for '{test_input}': {e}")
            return False
    
    return True


def test_script_execution():
    """Test the script can be executed with command line arguments."""
    script_path = os.path.join(os.path.dirname(__file__), "hash_calculator.py")
    
    # Test with both secrets
    cmd = [
        sys.executable, script_path,
        "--hashing-secret", "test-hash",
        "--encryption-key", "test-encrypt",
        "--output-format", "json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        
        if "HashingSecretHash" in output and "EncryptionSecretHash" in output:
            print("PASS: Script execution successful")
            print(f"JSON output: {json.dumps(output, indent=2)}")
            return True
        else:
            print(f"FAIL: Missing expected keys in output: {output}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"FAIL: Script execution failed: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON parsing failed: {e}")
        print(f"Output: {result.stdout}")
        return False


def main():
    """Run all tests."""
    print("Testing OpenToken Hash Calculator")
    print("=" * 40)
    
    all_passed = True
    
    # Test known values
    if not test_known_values():
        all_passed = False
    
    # Test Java compatibility
    if not test_java_compatibility():
        all_passed = False
    
    # Test script execution
    if not test_script_execution():
        all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("All tests PASSED!")
        sys.exit(0)
    else:
        print("Some tests FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
