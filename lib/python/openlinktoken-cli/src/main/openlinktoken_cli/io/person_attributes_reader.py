# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Dict, Iterator


class PersonAttributesReader(ABC, Iterator[Dict[object, str]]):
    """
    A generic interface for a streaming person attributes reader.

    Built-in readers emit field-ID string keys such as ``"FirstName"`` and
    ``"RecordId"``. For temporary compatibility, the processor also accepts
    legacy custom-reader rows keyed by :class:`openlinktoken.attributes.attribute.Attribute`
    subclasses. Built-in reader output should remain field-ID keyed.
    """

    @abstractmethod
    def row_count(self) -> int:
        """Return the total number of rows in the file."""
        pass

    @abstractmethod
    def __next__(self) -> Dict[object, str]:
        """
        Retrieve the next set of person attributes from an input source.

        Example person attribute map:
        {
            "RecordId": "2ea45fee-90c3-494a-a503-36022c9e1281",
            "FirstName": "John",
            "LastName": "Doe",
            "Sex": "Male",
            "BirthDate": "01/01/2001",
            "PostalCode": "54321",
            "SocialSecurityNumber": "123-45-6789"
        }

        Returns:
            A person attributes map keyed by field ID strings for built-in readers,
            or temporarily by legacy Attribute subclasses for compatible custom readers.
        """
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[Dict[object, str]]:
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
