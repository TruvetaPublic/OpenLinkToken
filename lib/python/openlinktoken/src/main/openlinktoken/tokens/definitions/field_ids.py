# SPDX-License-Identifier: MIT


class FieldIds:
    """
    Field identifiers referenced by the built-in T1-T5 token definitions.

    Centralizing these values avoids duplicating the same field-id strings across
    multiple token definition modules.
    """

    LAST_NAME = "LastName"
    FIRST_NAME = "FirstName"
    SEX = "Sex"
    BIRTH_DATE = "BirthDate"
    POSTAL_CODE = "PostalCode"
    SOCIAL_SECURITY_NUMBER = "SocialSecurityNumber"
