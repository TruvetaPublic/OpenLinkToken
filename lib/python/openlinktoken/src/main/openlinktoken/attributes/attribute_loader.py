# SPDX-License-Identifier: MIT

from typing import Set

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.general.date_attribute import DateAttribute
from openlinktoken.attributes.general.decimal_attribute import DecimalAttribute
from openlinktoken.attributes.general.integer_attribute import IntegerAttribute
from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.attributes.general.string_attribute import StringAttribute
from openlinktoken.attributes.general.year_attribute import YearAttribute
from openlinktoken.attributes.person.age_attribute import AgeAttribute
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.birth_year_attribute import BirthYearAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute


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
