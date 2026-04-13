"""
Utility to decrypt OpenLinkToken encrypted tokens.

OpenLinkToken uses AES-256-GCM encryption with random IVs. To compare tokens across
independently tokenized datasets, we need to decrypt them first to get the
underlying HMAC-SHA256 hash values, which are deterministic and comparable.
"""

import base64
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decrypt_token(encrypted_token, encryption_key):
    """
    Decrypt an OpenLinkToken encrypted token.

    Args:
        encrypted_token: Base64-encoded encrypted token with prepended IV
        encryption_key: 32-character encryption key (must match tokenization key)

    Returns:
        Decrypted token (the HMAC-SHA256 hash in Base64)
    """
    # Decode the base64-encoded message
    message_bytes = base64.b64decode(encrypted_token)

    # Extract IV (first 12 bytes) and ciphertext+tag (remaining bytes)
    iv = message_bytes[:12]
    ciphertext_and_tag = message_bytes[12:]

    # Create AESGCM cipher
    aesgcm = AESGCM(encryption_key.encode("utf-8"))

    # Decrypt and verify
    try:
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext_and_tag, None)
        decrypted_token = decrypted_bytes.decode("utf-8")
        return decrypted_token
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


def main():
    """Test decryption with a sample token."""
    if len(sys.argv) < 3:
        print("Usage: python decrypt_tokens.py <encrypted_token> <encryption_key>")
        print("\nExample:")
        print('python decrypt_tokens.py "Twka9NYy5iplVdXe..." "SuperHero-Encryption-Key-32chars"')
        sys.exit(1)

    encrypted_token = sys.argv[1]
    encryption_key = sys.argv[2]

    if len(encryption_key) != 32:
        print(f"Error: Encryption key must be exactly 32 characters (got {len(encryption_key)})")
        sys.exit(1)

    try:
        decrypted = decrypt_token(encrypted_token, encryption_key)
        print(f"Decrypted token: {decrypted}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
