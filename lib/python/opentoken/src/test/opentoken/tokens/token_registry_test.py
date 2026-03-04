"""
Copyright (c) Truveta. All rights reserved.
"""

from unittest.mock import patch

from opentoken.tokens.token_registry import TokenRegistry


def test_load_all_tokens_returns_non_empty_dict():
    """Test normal environment path - pkgutil.iter_modules works"""
    tokens = TokenRegistry.load_all_tokens()
    assert tokens, "Tokens dict should not be empty"

    expected_tokens = ["T1", "T2", "T3", "T4", "T5"]
    for token_id in expected_tokens:
        assert token_id in tokens, f"Tokens dict should contain {token_id}"
        definitions = tokens[token_id]
        assert definitions is not None, f"Definitions for {token_id} should not be None"
        assert definitions, f"Definitions for {token_id} should not be empty"


def test_load_all_tokens_with_empty_pkgutil_fallback_to_resources():
    """Test fallback path when pkgutil.iter_modules returns empty (e.g., bundled environment)"""
    with patch("opentoken.tokens.token_registry.pkgutil.iter_modules") as mock_iter_modules:
        # Simulate empty result from pkgutil (as in PyInstaller)
        mock_iter_modules.return_value = []

        tokens = TokenRegistry.load_all_tokens()

        # Should still load all tokens via importlib.resources fallback
        assert tokens, "Tokens dict should not be empty even with empty pkgutil"
        expected_tokens = ["T1", "T2", "T3", "T4", "T5"]
        for token_id in expected_tokens:
            assert token_id in tokens, f"Tokens dict should contain {token_id}"
            definitions = tokens[token_id]
            assert definitions is not None, f"Definitions for {token_id} should not be None"
            assert definitions, f"Definitions for {token_id} should not be empty"


def test_load_all_tokens_with_resources_fallback():
    """Test importlib.resources path explicitly"""
    with patch("opentoken.tokens.token_registry.pkgutil.iter_modules") as mock_iter_modules:
        # Simulate empty pkgutil result
        mock_iter_modules.return_value = []

        # Don't mock resources - let it actually work
        tokens = TokenRegistry.load_all_tokens()

        assert len(tokens) == 5, "Should load all 5 tokens via resources fallback"
        assert "T1" in tokens
        assert "T2" in tokens
        assert "T3" in tokens
        assert "T4" in tokens
        assert "T5" in tokens


def test_load_all_tokens_with_hardcoded_fallback():
    """Test final hardcoded fallback when both pkgutil and resources fail"""
    with (
        patch("opentoken.tokens.token_registry.pkgutil.iter_modules") as mock_iter_modules,
        patch("opentoken.tokens.token_registry.resources.files") as mock_resources,
    ):
        # Simulate empty pkgutil result
        mock_iter_modules.return_value = []

        # Simulate resources.files() failure
        mock_resources.side_effect = Exception("Resources not available")

        tokens = TokenRegistry.load_all_tokens()

        # Should still load all tokens via hardcoded fallback
        assert len(tokens) == 5, "Should load all 5 tokens via hardcoded fallback"
        expected_tokens = ["T1", "T2", "T3", "T4", "T5"]
        for token_id in expected_tokens:
            assert token_id in tokens, f"Hardcoded fallback should contain {token_id}"
            definitions = tokens[token_id]
            assert definitions is not None, f"Definitions for {token_id} should not be None"
            assert definitions, f"Definitions for {token_id} should not be empty"


def test_load_all_tokens_each_fallback_path():
    """Test that each fallback path is exercised in sequence"""

    # Test 1: Normal path (pkgutil works)
    tokens_normal = TokenRegistry.load_all_tokens()
    assert len(tokens_normal) == 5

    # Test 2: Resources fallback (pkgutil empty, resources works)
    with patch("opentoken.tokens.token_registry.pkgutil.iter_modules", return_value=[]):
        tokens_resources = TokenRegistry.load_all_tokens()
        assert len(tokens_resources) == 5
        # Verify same tokens loaded
        assert set(tokens_normal.keys()) == set(tokens_resources.keys())

    # Test 3: Hardcoded fallback (both pkgutil and resources fail)
    with (
        patch("opentoken.tokens.token_registry.pkgutil.iter_modules", return_value=[]),
        patch("opentoken.tokens.token_registry.resources.files", side_effect=Exception("Fail")),
    ):
        tokens_hardcoded = TokenRegistry.load_all_tokens()
        assert len(tokens_hardcoded) == 5
        # Verify same tokens loaded
        assert set(tokens_normal.keys()) == set(tokens_hardcoded.keys())


def test_load_all_tokens_consistency_across_fallbacks():
    """Ensure all fallback paths produce equivalent results"""

    # Load via normal path
    tokens_normal = TokenRegistry.load_all_tokens()

    # Load via resources fallback
    with patch("opentoken.tokens.token_registry.pkgutil.iter_modules", return_value=[]):
        tokens_resources = TokenRegistry.load_all_tokens()

    # Load via hardcoded fallback
    with (
        patch("opentoken.tokens.token_registry.pkgutil.iter_modules", return_value=[]),
        patch("opentoken.tokens.token_registry.resources.files", side_effect=Exception("Fail")),
    ):
        tokens_hardcoded = TokenRegistry.load_all_tokens()

    # All three should have same token IDs
    assert tokens_normal.keys() == tokens_resources.keys() == tokens_hardcoded.keys()

    # Each token should have same number of definitions
    for token_id in tokens_normal.keys():
        assert len(tokens_normal[token_id]) == len(tokens_resources[token_id])
        assert len(tokens_normal[token_id]) == len(tokens_hardcoded[token_id])
