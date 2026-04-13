# SPDX-License-Identifier: MIT

from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class NotNullOrEmptyValidator(SerializableAttributeValidator):
    """
    A Validator that asserts the value is NOT None and not blank.
    """

    def eval(self, value: str) -> bool:
        """
        Validate that the attribute value is not None or blank.

        Args:
            value: The attribute value to validate

        Returns:
            True if value is not None and not blank, False otherwise
        """
        return value is not None and value.strip() != ""
