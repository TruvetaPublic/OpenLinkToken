"""Tests for the Python docstring checker."""

import unittest

from tools.check_python_docstrings import check_source


class CheckPythonDocstringsTests(unittest.TestCase):
    """Verify the checker enforces declaration, input, and output docs."""

    def test_missing_declaration_docstrings_are_reported(self) -> None:
        """Report classes and methods without docstrings."""
        source = "class Example:\n    def run(self):\n        return 1\n"

        issues = check_source("example.py", source)

        self.assertEqual(len(issues), 2)
        self.assertIn("class 'Example' is missing a docstring", issues[0])
        self.assertIn("method 'run' is missing a docstring", issues[1])

    def test_missing_input_and_output_documentation_are_reported(self) -> None:
        """Require every parameter and non-void output to be documented."""
        source = 'def transform(source, strict=False):\n    """Transform source text."""\n    return source\n'

        issues = check_source("example.py", source)

        self.assertEqual(len(issues), 2)
        self.assertIn("source, strict", issues[0])
        self.assertIn("missing a non-empty Returns section", issues[1])

    def test_documented_method_passes(self) -> None:
        """Accept Google-style parameter and return descriptions."""
        source = (
            "class Parser:\n"
            '    """Parse source text."""\n'
            "    def parse(self, source: str, *, strict: bool = False) -> str:\n"
            '        """Parse source text.\n\n'
            "        Args:\n"
            "            source: The text to parse.\n"
            "            strict: Whether to reject malformed input.\n\n"
            "        Returns:\n"
            "            The parsed text.\n"
            '        """\n'
            "        return source\n"
        )

        self.assertEqual(check_source("example.py", source), [])

    def test_void_function_does_not_need_return_documentation(self) -> None:
        """Do not require Returns for functions that return None."""
        source = (
            "def notify(message: str) -> None:\n"
            '    """Send a notification.\n\n'
            "    Args:\n"
            "        message: The message to send.\n"
            '    """\n'
            "    return None\n"
        )

        self.assertEqual(check_source("example.py", source), [])

    def test_none_annotated_function_does_not_document_helper_return(self) -> None:
        """Treat calls returned from None-annotated functions as no output."""
        source = 'def update() -> None:\n    """Update stored state."""\n    return write_state()\n'

        self.assertEqual(check_source("example.py", source), [])

    def test_return_description_ending_in_colon_is_not_a_section_header(self) -> None:
        """Keep a description ending in a colon inside the Returns section."""
        source = (
            "def results() -> dict:\n"
            '    """Build results.\n\n'
            "    Returns:\n"
            "        Dictionary containing analysis results:\n"
            "        - `count`: Number of matches.\n"
            '    """\n'
            "    return {}\n"
        )

        self.assertEqual(check_source("example.py", source), [])

    def test_generator_documents_yielded_values(self) -> None:
        """Require Yields documentation for generator output."""
        source = (
            "def names():\n"
            '    """Yield names.\n\n'
            "    Yields:\n"
            "        A name from the source.\n"
            '    """\n'
            '    yield "name"\n'
        )

        self.assertEqual(check_source("example.py", source), [])

    def test_static_method_documents_parameter_named_self(self) -> None:
        """Treat a static method's self-named argument as an input."""
        source = (
            "class Encoder:\n"
            '    """Encode values."""\n'
            "    @staticmethod\n"
            "    def encode(self: str) -> str:\n"
            '        """Encode a value.\n\n'
            "        Args:\n"
            "            self: The value to encode.\n\n"
            "        Returns:\n"
            "            The encoded value.\n"
            '        """\n'
            "        return self\n"
        )

        self.assertEqual(check_source("example.py", source), [])

    def test_nested_function_outputs_do_not_belong_to_outer_function(self) -> None:
        """Keep nested function returns scoped to their declaration."""
        source = (
            "def outer():\n"
            '    """Run a local helper."""\n'
            "    def inner() -> int:\n"
            '        """Return a value.\n\n'
            "        Returns:\n"
            "            The helper result.\n"
            '        """\n'
            "        return 1\n"
        )

        self.assertEqual(check_source("example.py", source), [])


if __name__ == "__main__":
    unittest.main()
