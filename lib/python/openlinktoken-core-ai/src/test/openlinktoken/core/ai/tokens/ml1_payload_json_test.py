# SPDX-License-Identifier: MIT

from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import ml1_payload_to_json


class TestML1PayloadToJson:
    """Tests for ml1_payload_to_json JSON canonicalization.

    The payload string is fed directly into the ONNX tokenizer. It must match
    generate_embeddings.py: Python's default json.dumps separators (", " and ": "),
    with non-ASCII characters escaped as \\uXXXX (ensure_ascii=True default).
    Field order follows EP: PostalCode, Birthdate, GivenName, Surname, Gender.
    """

    def test_default_separators_with_spaces(self):
        """Preserve Python's default spaces after commas and colons."""
        payload = {
            "PostalCode": "98052",
            "Birthdate": "1980-01-01",
            "GivenName": "John",
            "Surname": "Doe",
            "Gender": "M",
        }
        result = ml1_payload_to_json(payload)
        expected = (
            '{"PostalCode": "98052", "Birthdate": "1980-01-01", "GivenName": "John", "Surname": "Doe", "Gender": "M"}'
        )
        assert result == expected

    def test_space_after_colon(self):
        """Include a space after each JSON object colon."""
        result = ml1_payload_to_json({"Key": "Value"})
        assert '": "' in result, "Expected space after colon to match generate_embeddings.py"

    def test_space_after_comma(self):
        """Include a space after each JSON object comma."""
        result = ml1_payload_to_json({"A": "1", "B": "2"})
        assert '", "' in result, "Expected space after comma to match generate_embeddings.py"

    def test_non_ascii_escaped(self):
        """Escape non-ASCII characters using JSON unicode escapes."""
        result = ml1_payload_to_json({"Surname": "Müller"})
        assert "\\u00fc" in result, "Non-ASCII chars must be escaped as \\uXXXX"
        assert "ü" not in result, "Raw non-ASCII must not appear in output"

    def test_key_order_preserved(self):
        """Keep payload fields in the insertion order supplied by the caller."""
        keys = ["PostalCode", "Birthdate", "GivenName", "Surname", "Gender"]
        payload = {k: str(i) for i, k in enumerate(keys)}
        result = ml1_payload_to_json(payload)
        positions = [result.index(f'"{k}"') for k in keys]
        assert positions == sorted(positions), "Key order not preserved in JSON output"
