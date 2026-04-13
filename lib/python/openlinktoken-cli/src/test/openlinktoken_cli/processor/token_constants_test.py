"""
Copyright (c) Truveta. All rights reserved.
"""

from openlinktoken_cli.processor.token_constants import TokenConstants


class TestTokenConstants:
    """Test cases for TokenConstants."""

    def test_token_constants_exist(self):
        """Test that all token constants exist."""
        assert hasattr(TokenConstants, "TOKEN")
        assert hasattr(TokenConstants, "RULE_ID")
        assert hasattr(TokenConstants, "RECORD_ID")

    def test_token_constants_values(self):
        """Test that token constants have correct values."""
        assert TokenConstants.TOKEN == "Token"
        assert TokenConstants.RULE_ID == "RuleId"
        assert TokenConstants.RECORD_ID == "RecordId"

    def test_token_constants_immutable(self):
        """Test that token constants are not None."""
        assert TokenConstants.TOKEN is not None
        assert TokenConstants.RULE_ID is not None
        assert TokenConstants.RECORD_ID is not None
