# SPDX-License-Identifier: MIT
"""
Notebook helpers for convenient token definition and experimentation.
This module provides a simplified API for creating custom tokens in Jupyter notebooks.
"""

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Type, Union

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from openlinktoken.exchange_config import derive_transport_encryption_key, resolve_exchange_config_inputs
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer

# Convenient attribute name mappings
ATTRIBUTE_MAP = {
    "first_name": FirstNameAttribute,
    "last_name": LastNameAttribute,
    "birth_date": BirthDateAttribute,
    "sex": SexAttribute,
    "postal_code": PostalCodeAttribute,
    "ssn": SocialSecurityNumberAttribute,
    "record_id": RecordIdAttribute,
}


class TokenBuilder:
    """
    A fluent builder for creating custom tokens with minimal code.

    Example:
        >>> token = TokenBuilder("T6") \\
        ...     .add("last_name", "T|U") \\
        ...     .add("first_name", "T|U") \\
        ...     .add("birth_date", "T|D") \\
        ...     .add("postal_code", "T|S(0,3)") \\
        ...     .add("sex", "T|U") \\
        ...     .build()
    """

    def __init__(self, token_id: str):
        """
        Initialize the token builder.

        Args:
            token_id: The identifier for the token (e.g., "T6", "T7").
        """
        self.token_id = token_id
        self.expressions: List[AttributeExpression] = []

    def add(self, attribute: Union[str, Type[Attribute]], expression: str = "T") -> "TokenBuilder":
        """
        Add an attribute expression to the token definition.

        Args:
            attribute: Either an attribute class or a string name (e.g., "first_name", "last_name").
            expression: The transformation expression (e.g., "T|U", "T|S(0,3)|U").

        Returns:
            Self for method chaining.

        Example:
            >>> builder.add("last_name", "T|U").add("first_name", "T|S(0,3)|U")
        """
        if isinstance(attribute, str):
            if attribute not in ATTRIBUTE_MAP:
                raise ValueError(f"Unknown attribute: {attribute}. Available: {', '.join(ATTRIBUTE_MAP.keys())}")
            attribute_class = ATTRIBUTE_MAP[attribute]
        else:
            attribute_class = attribute

        self.expressions.append(AttributeExpression(attribute_class, expression))
        return self

    def build(self) -> Token:
        """
        Build the custom token.

        Returns:
            A Token instance with the configured expressions.
        """
        token_id = self.token_id
        expressions = self.expressions

        class CustomToken(Token):
            """Dynamically created custom token."""

            ID = token_id

            def __init__(self):
                self._definition = expressions

            def get_identifier(self):
                return self.ID

            def get_definition(self):
                return self._definition

        return CustomToken()


class CustomTokenDefinition(BaseTokenDefinition):
    """
    A custom token definition that can include multiple custom tokens.

    Example:
        >>> definition = CustomTokenDefinition()
        >>> definition.add_token(t6_token)
        >>> definition.add_token(t7_token)
    """

    def __init__(self):
        """Initialize an empty custom token definition."""
        self.tokens: Dict[str, Token] = {}

    def add_token(self, token: Token) -> "CustomTokenDefinition":
        """
        Add a custom token to the definition.

        Args:
            token: The token to add.

        Returns:
            Self for method chaining.
        """
        token_id = token.get_identifier()
        self.tokens[token_id] = token
        return self

    def get_version(self) -> str:
        """Get the version of the token definition."""
        return "2.0-custom"

    def get_token_identifiers(self) -> set:
        """Get all token identifiers."""
        return set(self.tokens.keys())

    def get_token_definition(self, token_id: str) -> List[AttributeExpression]:
        """Get the token definition for a given token identifier."""
        token = self.tokens.get(token_id)
        if token:
            return token.get_definition()
        return None


def create_token_generator(
    hashing_secret: Union[str, bytes, None],
    encryption_key: Union[str, bytes],
    token_definition: Optional[BaseTokenDefinition] = None,
) -> TokenGenerator:
    """
    Create a token generator with the specified secrets and token definition.

    Args:
        hashing_secret: The secret used for HMAC-SHA256 hashing.
        encryption_key: The 32-character key used for AES-256 encryption.
        token_definition: Optional custom token definition. If None, uses default tokens.

    Returns:
        A configured TokenGenerator instance.

    Example:
        >>> # Use default tokens (T1-T5)
        >>> generator = create_token_generator("my-hash-secret", "my-32-character-encryption-key!")
        >>>
        >>> # Use custom tokens
        >>> custom_def = CustomTokenDefinition().add_token(t6_token)
        >>> generator = create_token_generator("secret", "key123...", custom_def)
    """
    if token_definition is None:
        from openlinktoken.tokens.token_definition import TokenDefinition

        token_definition = TokenDefinition()

    token_transformers = [HashTokenTransformer(hashing_secret), EncryptTokenTransformer(encryption_key)]

    return TokenGenerator.from_transformers(token_definition, token_transformers)


def create_token_generator_from_exchange_config(
    exchange_config_path: Union[str, Path, None] = None,
    exchange_config_value: Union[str, bytes, Mapping[str, Any], None] = None,
    private_key_path: Union[str, Path, None] = None,
    private_key_env: Optional[str] = None,
    private_key_value: Union[str, bytes, None] = None,
    token_definition: Optional[BaseTokenDefinition] = None,
) -> TokenGenerator:
    """
    Create a token generator from an exchange config and private-key inputs.

    Args:
        exchange_config_path: Optional exchange-config path. Uses the default path when omitted.
        exchange_config_value: Optional in-memory exchange-config JSON or decoded mapping.
        private_key_path: Optional private-key PEM path.
        private_key_env: Optional environment-variable name containing private-key PEM text.
        private_key_value: Optional in-memory private-key PEM text or bytes.
        token_definition: Optional custom token definition. If None, uses default tokens.

    Returns:
        A configured TokenGenerator instance using the exchange hashing secret and transport key.
    """
    exchange = resolve_exchange_config_inputs(
        exchange_config_path=exchange_config_path,
        exchange_config_value=exchange_config_value,
        private_key_path=private_key_path,
        private_key_env=private_key_env,
        private_key_value=private_key_value,
    )
    return create_token_generator(
        hashing_secret=exchange.hashing_secret,
        encryption_key=derive_transport_encryption_key(exchange),
        token_definition=token_definition,
    )


def quick_token(
    token_id: str,
    attributes: List[tuple],
    hashing_secret: Union[str, bytes, None],
    encryption_key: Union[str, bytes],
) -> TokenGenerator:
    """
    Create a custom token and generator in one quick call.

    Args:
        token_id: The identifier for the new token (e.g., "T6").
        attributes: List of (attribute_name, expression) tuples.
        hashing_secret: The secret used for HMAC-SHA256 hashing.
        encryption_key: The 32-character key used for AES-256 encryption.

    Returns:
        A TokenGenerator configured with the custom token.

    Example:
        >>> generator = quick_token(
        ...     "T6",
        ...     [
        ...         ("last_name", "T|U"),
        ...         ("first_name", "T|U"),
        ...         ("birth_date", "T|D"),
        ...         ("postal_code", "T|S(0,3)"),
        ...         ("sex", "T|U")
        ...     ],
        ...     "my-hashing-secret",
        ...     "my-32-character-encryption-key!"
        ... )
    """
    builder = TokenBuilder(token_id)
    for attr_name, expr in attributes:
        builder.add(attr_name, expr)

    token = builder.build()
    definition = CustomTokenDefinition().add_token(token)

    return create_token_generator(hashing_secret, encryption_key, definition)


def quick_token_from_exchange_config(
    token_id: str,
    attributes: List[tuple],
    exchange_config_path: Union[str, Path, None] = None,
    exchange_config_value: Union[str, bytes, Mapping[str, Any], None] = None,
    private_key_path: Union[str, Path, None] = None,
    private_key_env: Optional[str] = None,
    private_key_value: Union[str, bytes, None] = None,
) -> TokenGenerator:
    """
    Create a custom token generator from exchange-config inputs in one quick call.

    Args:
        token_id: The identifier for the new token (e.g., "T6").
        attributes: List of (attribute_name, expression) tuples.
        exchange_config_path: Optional exchange-config path. Uses the default path when omitted.
        exchange_config_value: Optional in-memory exchange-config JSON or decoded mapping.
        private_key_path: Optional private-key PEM path.
        private_key_env: Optional environment-variable name containing private-key PEM text.
        private_key_value: Optional in-memory private-key PEM text or bytes.

    Returns:
        A TokenGenerator configured with the custom token and exchange-derived secrets.
    """
    builder = TokenBuilder(token_id)
    for attr_name, expr in attributes:
        builder.add(attr_name, expr)

    token = builder.build()
    definition = CustomTokenDefinition().add_token(token)

    return create_token_generator_from_exchange_config(
        exchange_config_path=exchange_config_path,
        exchange_config_value=exchange_config_value,
        private_key_path=private_key_path,
        private_key_env=private_key_env,
        private_key_value=private_key_value,
        token_definition=definition,
    )


# Convenience function to list available attributes
def list_attributes() -> Dict[str, Type[Attribute]]:
    """
    Get a dictionary of available attribute names and their classes.

    Returns:
        Dictionary mapping attribute names to their classes.

    Example:
        >>> attrs = list_attributes()
        >>> print(attrs.keys())
        dict_keys(['first_name', 'last_name', 'birth_date', 'sex', 'postal_code', 'ssn', 'record_id'])
    """
    return ATTRIBUTE_MAP.copy()


def expression_help() -> str:
    """
    Get help text about expression syntax.

    Returns:
        A string describing the expression syntax.
    """
    return """
Expression Syntax Guide:
========================

Components (separated by |):
- T           : Trim whitespace
- U           : Convert to uppercase
- S(start,end): Substring (e.g., S(0,3) for first 3 characters)
- D           : Format as date (yyyy-MM-dd)
- M(regex)    : Match regular expression
- R(old,new)  : Replace string

Examples:
- "T|U"         : Trim and uppercase (e.g., "  john  " → "JOHN")
- "T|S(0,3)|U"  : Trim, take first 3 chars, uppercase (e.g., "john" → "JOH")
- "T|D"         : Trim and format as date (e.g., "1990-01-15" → "1990-01-15")
- "T|S(0,5)"    : Trim and take first 5 chars (e.g., "98101-1234" → "98101")

Common Patterns:
- Names:        "T|U" or "T|S(0,3)|U"
- Dates:        "T|D"
- Postal codes: "T|S(0,3)" or "T|S(0,5)"
- Gender/Sex:   "T|U"
"""
