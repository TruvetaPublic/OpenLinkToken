# SPDX-License-Identifier: MIT
"""
An attribute expression determines how the value of an attribute is normalized for consumption.

Below are the components used to compose the attribute expression:
- `T` - trim
- `U` - convert to upper case
- `S(start_index, end_index)` - substring of value
- `D` - treat as date
- `M(regex)` - match the regular expression
- `R(oldString, newString)` - replace old string with new string
- `|` - expression separator

Examples of attribute expressions:
- `T|S(0,3)|U` - trim the value, then take first 3 characters, and then convert to upper case.
- `T|D` - trim the value, treat the value as a date in the yyyy-MM-dd format.
- `T|M("\\d+")` - trim the value, then make sure that the value matches the regular expression.
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from openlinktoken.attributes.attribute import Attribute


class AttributeExpression:
    """
    An attribute expression determines how the value of an attribute is normalized for consumption.
    """

    EXPRESSION_PATTERN = re.compile(r"\s*(?P<expr>[^ (]+)(?:\((?P<args>[^\)]+)\))?")

    def __init__(self, attribute_class: Type["Attribute"], expressions: Optional[str]):
        """
        Initialize the AttributeExpression.

        Args:
            attribute_class: The class of the attribute being processed.
            expressions: The string of expressions to apply.
        """
        self.attribute_class = attribute_class
        self.expressions = expressions

    def get_effective_value(self, value: Optional[str]) -> str:
        """
        Get the effective value for an attribute after application of the attribute expression.

        Args:
            value: The attribute value.

        Returns:
            The effective value after applying the attribute expression.
        """
        if value is None or value.strip() == "":
            return ""

        if self.expressions is None or self.expressions.strip() == "":
            return value

        result = value
        expression_parts = self.expressions.split("|")
        for expression in expression_parts:
            result = self._eval(result, expression)
        return result

    @staticmethod
    def _eval_error(value: str, expression: str, inner_exception: Optional[Exception] = None) -> ValueError:
        """
        Create an error for failed expression evaluation.

        Args:
            value: The value being processed.
            expression: The expression being applied.
            inner_exception: The exception that occurred.

        Returns:
            The error with a detailed message.
        """
        message = f"Unable to evaluate expression [{expression}] over value [{value}]."
        if inner_exception:
            raise ValueError(message) from inner_exception
        return ValueError(message)

    @classmethod
    def _eval(cls, value: str, expression: str) -> str:
        """
        Evaluate a single expression on the given value.

        Args:
            value: The value to process.
            expression: The expression to apply.

        Returns:
            The processed value.
        """
        if value is None or expression is None:
            raise cls._eval_error(value, expression)

        matcher = cls.EXPRESSION_PATTERN.match(expression)
        if not matcher:
            raise cls._eval_error(value, expression)

        expr = matcher.group("expr")
        args = None
        if matcher.group("args"):
            args = matcher.group("args").strip().split(",")

        expr_upper = expr.upper()

        if expr_upper == "U":
            return value.upper()
        elif expr_upper == "T":
            return value.strip()
        elif expr_upper == "S":
            if args is None:
                raise cls._eval_error(value, expression)
            return cls._substring(value, expression, args)
        elif expr_upper == "R":
            if args is None:
                raise cls._eval_error(value, expression)
            return cls._replace(value, expression, args)
        elif expr_upper == "M":
            if args is None:
                raise cls._eval_error(value, expression)
            return cls._match(value, expression, args)
        elif expr_upper == "D":
            return cls._date(value, expression)
        else:
            raise cls._eval_error(value, expression)

    @classmethod
    def _substring(cls, value: str, expression: str, args: list[str]) -> str:
        """
        Substring expression S(start, end).

        Args:
            value: The value to process.
            expression: The expression being applied.
            args: The arguments for the substring operation.

        Returns:
            The extracted substring.
        """
        if len(args) != 2:
            raise cls._eval_error(value, expression)

        try:
            start = max(0, int(args[0]))
            end = min(len(value), int(args[1]))
            return value[start:end]
        except (ValueError, IndexError) as ex:
            raise cls._eval_error(value, expression, ex)

    @classmethod
    def _replace(cls, value: str, expression: str, args: list[str]) -> str:
        """
        Replace expression R(oldString, newString).

        Args:
            value: The value to process.
            expression: The expression being applied.
            args: The arguments for the replace operation.

        Returns:
            The value with replacements applied.
        """
        if len(args) != 2:
            raise cls._eval_error(value, expression)

        if len(args[0]) < 2 or len(args[1]) < 2:
            raise cls._eval_error(value, expression, ValueError("Arguments must be quoted strings."))

        try:
            # Remove quotes from the arguments
            old_val = args[0][1:-1] if len(args[0]) >= 2 else args[0]
            new_val = args[1][1:-1] if len(args[1]) >= 2 else args[1]
            return value.replace(old_val, new_val)
        except Exception as ex:
            raise cls._eval_error(value, expression, ex)

    @classmethod
    def _match(cls, value: str, expression: str, args: list[str]) -> str:
        """
        RegEx match M(regex).

        Args:
            value: The value to process.
            expression: The expression being applied.
            args: The arguments for the match operation.

        Returns:
            The concatenated matching parts.
        """
        if len(args) != 1:
            raise cls._eval_error(value, expression)

        try:
            pattern = re.compile(args[0])
            matches = pattern.findall(value)
            return "".join(matches)
        except re.error as ex:
            raise cls._eval_error(value, expression, ex)

    @classmethod
    def _date(cls, value: str, expression: str) -> str:
        """
        Date expression D.

        Supported date formats, and will be changed to "yyyy-MM-dd".
        If the date is not in the supported formats, an exception will be thrown.

        Args:
            value: The value to process.
            expression: The expression being applied.

        Returns:
            The formatted date string.
        """
        # Supported date formats
        possible_formats = ["%Y-%m-%d"]

        for fmt in possible_formats:
            try:
                date = datetime.strptime(value, fmt)
                return date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If no format worked, raise an error
        raise cls._eval_error(value, expression)
