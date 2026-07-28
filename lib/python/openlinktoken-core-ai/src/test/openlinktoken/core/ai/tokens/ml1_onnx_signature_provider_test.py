import pytest

from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig
from openlinktoken.core.ai.tokens.ml1_onnx_signature_provider import (
    ML1OnnxSignatureProvider,
    _compute_blocking_key,
    _hash_rotation_values,
)
from openlinktoken.core.ai.tokens.ml1_token import ML1Token
from openlinktoken.core.ai.tokens.rotation_config import RotationConfig
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult


@pytest.fixture(autouse=True)
def reset_runtime_config():
    """Restore process-wide ML1 and rotation settings after each test."""

    def restore():
        ML1InferenceConfig.configure(
            True,
            ML1InferenceConfig.DEFAULT_MODEL_PATH,
            ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
            ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
            ML1InferenceConfig.DEFAULT_BATCH_SIZE,
            ML1InferenceConfig.DEFAULT_NUM_THREADS,
        )
        RotationConfig.configure(enable=True, rotation_iv=RotationConfig.DEFAULT_IV)

    restore()
    yield
    restore()


def test_rotation_hash_uses_hashed_t1_blocking_key():
    """Verify rotation values are hashed with the normalized T1 blocking key."""
    person_attributes = {
        BirthDateAttribute: "1989-05-25",
        FirstNameAttribute: "Chelsea",
        LastNameAttribute: "Meister",
        PostalCodeAttribute: "06582",
        SexAttribute: "Female",
    }

    blocking_key = _compute_blocking_key(person_attributes)

    assert blocking_key == "f016a96ba8552da8c9d7ac327f91081e22740f0ddd71dc372fa4dbba2ca34253"
    assert _hash_rotation_values(["99 100 100 101"], blocking_key) == [
        "4ff691600f8c2df6142c405cbcd6f166a588ba83bd93ba6f028e082ef99decd8"
    ]


def test_provider_uses_ml1_token_identifier():
    """Provider and token definition must share the ML1 registry identifier."""
    assert ML1OnnxSignatureProvider().get_token_id() == ML1Token.TOKEN_ID


def test_build_ml1_payload_normalizes_fields_in_definition_order():
    """ML1 payloads should normalize values and preserve the model field order."""
    person_attributes = {
        PostalCodeAttribute: "95123",
        BirthDateAttribute: "1990-07-09",
        FirstNameAttribute: " Alice ",
        LastNameAttribute: " Smith ",
        SexAttribute: "female",
    }
    result = TokenGeneratorResult()

    payload = ML1OnnxSignatureProvider().build_ml1_payload(person_attributes, result)

    assert payload == (
        '{"PostalCode": "95123", "Birthdate": "1990-07-09", "GivenName": "Alice", '
        '"Surname": "Smith", "Gender": "Female"}'
    )
    assert result.invalid_attributes == set()


def test_build_ml1_payload_records_missing_required_field():
    """Missing required ML1 fields should produce no payload and record the field."""
    person_attributes = {
        PostalCodeAttribute: "95123",
        BirthDateAttribute: "1990-07-09",
        FirstNameAttribute: "Alice",
        LastNameAttribute: "Smith",
    }
    result = TokenGeneratorResult()

    payload = ML1OnnxSignatureProvider().build_ml1_payload(person_attributes, result)

    assert payload is None
    assert result.invalid_attributes == {SexAttribute.__name__}


def test_build_ml1_payload_records_invalid_field():
    """Invalid required ML1 fields should produce no payload and record the field."""
    person_attributes = {
        PostalCodeAttribute: "95123",
        BirthDateAttribute: "1990-07-09",
        FirstNameAttribute: "Alice",
        LastNameAttribute: "Smith",
        SexAttribute: "unknown",
    }
    result = TokenGeneratorResult()

    payload = ML1OnnxSignatureProvider().build_ml1_payload(person_attributes, result)

    assert payload is None
    assert result.invalid_attributes == {SexAttribute.__name__}


@pytest.mark.parametrize("enabled", [True, False])
def test_provider_enabled_state_matches_configuration(enabled):
    """Provider enablement should reflect the process-wide ML1 configuration."""
    ML1InferenceConfig.configure(
        enabled,
        ML1InferenceConfig.DEFAULT_MODEL_PATH,
        ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
        ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
        ML1InferenceConfig.DEFAULT_BATCH_SIZE,
        ML1InferenceConfig.DEFAULT_NUM_THREADS,
    )

    assert ML1OnnxSignatureProvider().is_enabled() is enabled


def test_generate_batch_returns_empty_signatures_for_all_invalid_rows():
    """A batch with no valid payloads should not initialize or call ONNX."""
    result = ML1OnnxSignatureProvider().generate_batch([{}, {}])

    assert result.signatures == [None, None]


def test_ml1_token_definition_is_empty():
    """ML1 input is the canonical payload rather than attribute expressions."""
    assert ML1Token().get_definition() == []
