import pytest
from multi_language_syncer import MultiLanguageSyncer


def test_python_cli_is_not_an_active_sync_language():
    assert "python-cli" not in MultiLanguageSyncer.LANGUAGES


def test_python_crypto_suite_module_maps_to_java_crypto_package():
    """Check that the Python crypto-suite source maps to the Java crypto package path.

    Args:
        None; this function takes no arguments.

    Returns:
        None.
    """
    syncer = MultiLanguageSyncer()

    corresponding = syncer.get_corresponding_files(
        "lib/python/openlinktoken/src/main/openlinktoken/crypto/crypto_suite.py",
        "python",
    )

    assert corresponding["java"] == "lib/java/openlinktoken/src/main/java/org/openlinktoken/crypto/CryptoSuite.java"


def test_java_crypto_suite_module_maps_to_python_crypto_package():
    """Check that the Java crypto-suite source maps to the Python crypto package path.

    Args:
        None; this function takes no arguments.

    Returns:
        None.
    """
    syncer = MultiLanguageSyncer()

    corresponding = syncer.get_corresponding_files(
        "lib/java/openlinktoken/src/main/java/org/openlinktoken/crypto/CryptoSuite.java",
        "java",
    )

    assert corresponding["python"] == "lib/python/openlinktoken/src/main/openlinktoken/crypto/crypto_suite.py"


@pytest.mark.parametrize(
    ("source_file", "expected_java_file"),
    [
        (
            "lib/python/openlinktoken/src/main/openlinktoken/tokens/tokenizer/sha3_token_digest.py",
            "lib/java/openlinktoken/src/main/java/org/openlinktoken/tokens/tokenizer/SHA3TokenDigest.java",
        ),
        (
            "lib/python/openlinktoken/src/main/openlinktoken/tokens/tokenizer/shake256_token_digest.py",
            "lib/java/openlinktoken/src/main/java/org/openlinktoken/tokens/tokenizer/SHAKE256TokenDigest.java",
        ),
    ],
)
def test_python_digest_modules_map_to_java_acronym_names(source_file, expected_java_file):
    """Asserts Python digest source paths map to Java class paths with acronyms preserved.

    Args:
        source_file: Python digest module path.
        expected_java_file: Expected Java class path for the module.

    Returns:
        None.
    """
    syncer = MultiLanguageSyncer()

    corresponding = syncer.get_corresponding_files(source_file, "python")

    assert corresponding["java"] == expected_java_file
