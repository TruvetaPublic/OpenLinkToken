from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.core.ai.tokens.ml1_onnx_signature_provider import (
    ML1OnnxSignatureProvider,
    _compute_blocking_key,
    _hash_rotation_values,
)
from openlinktoken.core.ai.tokens.ml1_token import ML1Token


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
