# SPDX-License-Identifier: MIT

from openlinktoken_core_ai.tokens.ml1_onnx_signature_generator import ml1_payload_to_json


class TestML1PayloadToJson:
    """Tests for ml1_payload_to_json JSON canonicalization.

    The payload string is fed directly into the ONNX tokenizer, so its format
    must be byte-identical to what Java's Jackson ObjectMapper produces with
    default settings: compact JSON, no spaces around separators.
    """

    def test_compact_separators_no_spaces(self):
        payload = {
            "PostalCode": "98052",
            "Birthdate": "1980-01-01",
            "GivenName": "John",
            "Surname": "Doe",
            "Gender": "M",
        }
        result = ml1_payload_to_json(payload)
        # Must match Jackson ObjectMapper.writeValueAsString() default output exactly.
        assert result == '{"PostalCode":"98052","Birthdate":"1980-01-01","GivenName":"John","Surname":"Doe","Gender":"M"}'

    def test_no_space_after_colon(self):
        result = ml1_payload_to_json({"Key": "Value"})
        assert '": "' not in result, "Space around colon separator diverges from Java Jackson output"

    def test_no_space_after_comma(self):
        result = ml1_payload_to_json({"A": "1", "B": "2"})
        assert '", "' not in result, "Space after comma separator diverges from Java Jackson output"

    def test_key_order_preserved(self):
        # Insertion order must be preserved so the tokenizer input is deterministic.
        keys = ["PostalCode", "Birthdate", "GivenName", "Surname", "Gender"]
        payload = {k: str(i) for i, k in enumerate(keys)}
        result = ml1_payload_to_json(payload)
        positions = [result.index(f'"{k}"') for k in keys]
        assert positions == sorted(positions), "Key order not preserved in JSON output"
