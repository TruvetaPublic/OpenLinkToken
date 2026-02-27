"""
Copyright (c) Truveta. All rights reserved.
"""

from opentoken_cli.util import StringMaskingUtil, mask_string


class TestStringMaskingUtil:
    """Unit tests for string masking utilities."""

    def test_mask_string_with_none(self):
        """None should be masked as <null>."""
        assert StringMaskingUtil.mask_string(None) == "<null>"

    def test_mask_string_with_short_value(self):
        """Strings with length <= 3 should be fully masked."""
        assert StringMaskingUtil.mask_string("abc") == "***"

    def test_mask_string_with_longer_value(self):
        """Strings with length > 3 should keep first 3 chars."""
        assert StringMaskingUtil.mask_string("TestSecretValue") == "Tes************"

    def test_module_level_mask_string_function(self):
        """Package-level function should delegate to StringMaskingUtil."""
        assert mask_string("TestSecretValue") == "Tes************"
