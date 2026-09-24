# SPDX-License-Identifier: MIT

import re

from openlinktoken_cli.util.ring_id_utils import resolve_ring_id


class TestResolveRingId:
    """Unit tests for resolve_ring_id()."""

    def test_none_returns_uuid(self):
        assert resolve_ring_id(None) is not None
        assert len(resolve_ring_id(None)) == 36  # standard UUID format with dashes

    def test_empty_string_returns_fresh_uuid(self):
        result = resolve_ring_id("")
        assert result is not None
        assert len(result) == 36

    def test_blank_string_returns_fresh_uuid(self):
        result = resolve_ring_id("    ")
        assert result is not None
        assert len(result) == 36

    def test_valid_string_passed_through(self):
        """A non-blank string should be returned as-is after stripping."""
        assert resolve_ring_id("abc-123") == "abc-123"

    def test_whitespace_stripped(self):
        """Leading and trailing whitespace should be stripped from the input."""
        assert resolve_ring_id("  def-456   ") == "def-456"

    def test_uuid_format_output(self):
        """Auto-generated UUIDs must match the v4 hex pattern."""
        result = resolve_ring_id(None)
        uuid_pattern = (
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        assert re.match(uuid_pattern, result) is not None

    def test_multiple_calls_produce_different_values(self):
        """Each call with None should produce a unique UUID."""
        first = resolve_ring_id(None)
        second = resolve_ring_id(None)
        assert first != second
