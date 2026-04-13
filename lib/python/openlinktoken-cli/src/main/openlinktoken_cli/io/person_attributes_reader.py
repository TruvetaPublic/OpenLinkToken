# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Dict, Iterator, Type

from openlinktoken.attributes.attribute import Attribute


class PersonAttributesReader(ABC, Iterator[Dict[Type[Attribute], str]]):
    """
    A generic interface for a streaming person attributes reader.
    """

    @abstractmethod
    def __next__(self) -> Dict[Type[Attribute], str]:
        """
        Retrieve the next set of person attributes from an input source.

        Example person attribute map:
        {
            RecordIdAttribute: "2ea45fee-90c3-494a-a503-36022c9e1281",
            FirstNameAttribute: "John",
            LastNameAttribute: "Doe",
            SexAttribute: "Male",
            BirthDateAttribute: "01/01/2001",
            PostalCodeAttribute: "54321",
            SocialSecurityNumberAttribute: "123-45-6789"
        }

        Returns:
            A person attributes map.
        """
        pass

    @abstractmethod
    def __iter__(self):
        """Return the iterator object."""
        return self

    @abstractmethod
    def close(self) -> None:
        """Close the reader and release any resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
