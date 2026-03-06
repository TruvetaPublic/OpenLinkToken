# src/opentoken/attributes/person/birth_date_attribute.py
from datetime import date
from typing import List

from opentoken.attributes.general.date_attribute import DateAttribute
from opentoken.attributes.validation.date_range_validator import DateRangeValidator


class BirthDateAttribute(DateAttribute):
    """Represents the birth date attribute.

    This class extends DateAttribute and provides functionality for working with
    birth date fields. It recognizes "BirthDate" as a valid alias for this
    attribute type.

    The attribute performs normalization on input values, converting them to a
    standard format (yyyy-MM-dd).

    Supported formats:
    - yyyy-MM-dd
    - yyyy/MM/dd
    - MM/dd/yyyy
    - MM-dd-yyyy
    - dd.MM.yyyy
    """

    NAME = "BirthDate"
    ALIASES = [NAME]

    def __init__(self):
        # Birth dates must be between 1910-01-01 and today
        min_date = date(1910, 1, 1)
        validator = DateRangeValidator(min_date=min_date, use_current_as_max=True)
        super().__init__(additional_validators=[validator])

    def get_name(self) -> str:
        return self.NAME

    def get_aliases(self) -> List[str]:
        return self.ALIASES.copy()
