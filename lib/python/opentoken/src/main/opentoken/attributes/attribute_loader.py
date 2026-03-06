"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Set

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.general.date_attribute import DateAttribute
from opentoken.attributes.general.decimal_attribute import DecimalAttribute
from opentoken.attributes.general.integer_attribute import IntegerAttribute
from opentoken.attributes.general.record_id_attribute import RecordIdAttribute
from opentoken.attributes.general.string_attribute import StringAttribute
from opentoken.attributes.general.year_attribute import YearAttribute
from opentoken.attributes.person.age_attribute import AgeAttribute
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.birth_year_attribute import BirthYearAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute


class AttributeLoader:
    """
    Loads all available attribute implementations.
    """

    def __init__(self):
        raise RuntimeError("AttributeLoader should not be instantiated.")

    @staticmethod
    def load() -> Set[Attribute]:
        """Load all attribute implementations."""
        return {
            RecordIdAttribute(),
            StringAttribute(),
            DateAttribute(),
            DecimalAttribute(),
            IntegerAttribute(),
            YearAttribute(),
            FirstNameAttribute(),
            LastNameAttribute(),
            BirthDateAttribute(),
            AgeAttribute(),
            BirthYearAttribute(),
            SexAttribute(),
            SocialSecurityNumberAttribute(),
            PostalCodeAttribute(),
        }
