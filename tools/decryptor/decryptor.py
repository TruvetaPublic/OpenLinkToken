"""
OpenToken Decryptor Tool

Decrypts AES-GCM encrypted tokens from CSV files.
Supports both legacy base64-encoded tokens and V1 JWE tokens (ot.V1.<JWE>).

Usage: python decryptor.py -e "encryption_key" -i input.csv -o output.csv
Requirements: pycryptodome library, jwcrypto library, CSV with RuleId,Token,RecordId columns
"""

import argparse
import base64
import csv
import json
from Crypto.Cipher import AES

try:
    from jwcrypto import jwe, jwk
    JWE_SUPPORT = True
except ImportError:
    JWE_SUPPORT = False

PROGRAM = 'decryptor.py'
UTF8 = 'utf-8'
BLANK_TOKEN = '0000000000000000000000000000000000000000000000000000000000000000'
V1_TOKEN_PREFIX = 'ot.V1.'

def decrypt_v1_token(token, encryption_key):
    """Decrypt V1 JWE token and return the underlying token value.

    V1 payloads currently store the legacy AES-GCM token in `ppid[0]`.
    For interoperability checks, attempt to unwrap that inner token too.
    """
    if not JWE_SUPPORT:
        raise RuntimeError("jwcrypto library required for V1 token decryption. Install with: pip install jwcrypto")
    
    # Remove the ot.V1. prefix
    jwe_compact = token[len(V1_TOKEN_PREFIX):]
    
    # Create JWK from encryption key
    key_bytes = encryption_key.encode('utf-8')
    key_b64 = base64.urlsafe_b64encode(key_bytes).decode('utf-8').rstrip('=')
    jwk_key = jwk.JWK(kty="oct", k=key_b64)
    
    # Decrypt the JWE
    jwe_token = jwe.JWE()
    jwe_token.deserialize(jwe_compact)
    jwe_token.decrypt(jwk_key)
    
    # Parse the payload
    payload = json.loads(jwe_token.payload.decode('utf-8'))
    
    # Extract the PPID (first element if it's an array)
    ppid = payload.get('ppid', [])
    if isinstance(ppid, list) and len(ppid) > 0:
        ppid_value = ppid[0]
    else:
        ppid_value = str(ppid)

    if not isinstance(ppid_value, str) or not ppid_value:
        return ppid_value

    try:
        return decrypt_legacy_token(ppid_value, encryption_key)
    except Exception:
        # Keep compatibility with any future payloads that store plaintext PPIDs.
        return ppid_value


def decrypt_legacy_token(token, encryption_key):
    """Decrypt legacy base64-encoded AES-GCM token."""
    # decode the token first
    decoded_token = base64.b64decode(token)

    # extract the IV from the decoded token (first 12 bytes)
    iv = decoded_token[:12]
    ciphertext = decoded_token[12:]

    # Decrypt using AES-GCM
    cipher = AES.new(encryption_key.encode(UTF8), AES.MODE_GCM, nonce=iv)
    decrypted_text = cipher.decrypt_and_verify(
        ciphertext[:-16], ciphertext[-16:])
    return decrypted_text.decode(UTF8)


def decrypt_tokens(key, input_file, output_file):
    """
    Decrypt tokens from CSV using AES-GCM. 
    Supports both legacy base64 tokens and V1 JWE tokens (ot.V1.<JWE>).
    """
    with open(output_file, mode='w', encoding=UTF8, newline='') as outfile:
        columns = ['RuleId', 'Token', 'RecordId']
        writer = csv.DictWriter(outfile, fieldnames=columns)
        writer.writeheader()

        with open(input_file) as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                token = row['Token']

                if token != BLANK_TOKEN:
                    try:
                        # Check if it's a V1 JWE token
                        if token.startswith(V1_TOKEN_PREFIX):
                            token = decrypt_v1_token(token, key)
                        else:
                            # Legacy base64-encoded token
                            token = decrypt_legacy_token(token, key)
                    except Exception as e:
                        print(f"Original token: {token}")
                        print(
                            f"Decryption error for RuleId {row['RuleId']}, RecordId {row['RecordId']}: {e}")
                        raise

                # write the decrypted token back
                writer.writerow({
                    'RuleId': row['RuleId'],
                    'Token': token,
                    'RecordId': row['RecordId']
                })


def parse_args():
    """Parse command-line arguments for encryption key, input file, and output file."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='Decrypts tokens from OpenToken CSV files using AES-GCM encryption'
    )
    parser.add_argument('-e', '--encryption-key', required=True, 
                        help='Symmetric encryption key.')
    parser.add_argument('-i', '--input-file', required=True,
                        help='The input file with encrypted tokens.')
    parser.add_argument('-o', '--output-file', required=True,
                        help='The output file with decrypted tokens.')
    return parser.parse_args()

def main():
    """Main entry point - parses args and orchestrates decryption."""
    try:
        args = parse_args()
        print(f'Encryption key: {args.encryption_key}')
        print(f'Input file: {args.input_file}')
        print(f'Output file: {args.output_file}')
        
        decrypt_tokens(args.encryption_key, args.input_file, args.output_file)
        print(
            f'Tokens from {args.input_file} are successfully decrypted and written to {args.output_file}')
    except Exception:
        print('Failed to decrypt tokens')
        raise


if __name__ == "__main__":
    # For direct function testing, uncomment:
    # decrypt_tokens("your-encryption-key", "input.csv", "output.csv")
    main()
