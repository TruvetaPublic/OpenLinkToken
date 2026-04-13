"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC

from openlinktoken.attributes.validation.attribute_validator import AttributeValidator


class SerializableAttributeValidator(AttributeValidator, ABC):
    """
    An extension of the AttributeValidator interface that is also serializable.

    This interface should be implemented by validator classes that need to be
    serialized, such as when they are part of serializable attributes or need to
    be transmitted over a network.

    Implementing classes must ensure that all their fields are serializable or
    handled appropriately if they cannot be serialized.

    Note: In Python, most objects are serializable by default with pickle,
    but this class serves as a marker for validators that are explicitly
    designed to be serializable.
    """

    # This is a marker interface that combines AttributeValidator and serializable capability
    # No additional methods are required
    pass
