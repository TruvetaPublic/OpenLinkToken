from typing import List

from opentoken.attributes.serializable_attribute import SerializableAttribute
from opentoken.attributes.validation.not_null_or_empty_validator import NotNullOrEmptyValidator
from opentoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class BaseAttribute(SerializableAttribute):
    """A base implementation of the SerializableAttribute interface.

    This class provides a default implementation of the validate method
    that validates the attribute value against a set of validation rules.

    The default validation rules are:
    - Not null or empty
    """

    def __init__(self, validation_rules: List[SerializableAttributeValidator] = None):
        if validation_rules is None:
            validation_rules = []

        rule_list = [NotNullOrEmptyValidator()]
        rule_list.extend(validation_rules)
        self.validation_rules = rule_list

    def validate(self, value: str) -> bool:
        """Validates the attribute value against a set of validation rules."""
        if value is None:
            return False

        return all(rule.eval(value) for rule in self.validation_rules)
