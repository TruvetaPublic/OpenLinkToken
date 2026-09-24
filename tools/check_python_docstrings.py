"""Check Python classes, functions, and methods for useful docstrings."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_SECTION_HEADINGS = {
    "Args:",
    "Arguments:",
    "Attributes:",
    "Class Attributes:",
    "Deprecated:",
    "Example:",
    "Examples:",
    "Keyword Args:",
    "Keyword Arguments:",
    "Methods:",
    "Module Attributes:",
    "Note:",
    "Notes:",
    "Other Parameters:",
    "Parameters:",
    "Properties:",
    "Raises:",
    "References:",
    "Returns:",
    "See Also:",
    "Todo:",
    "Warnings:",
    "Yields:",
}
_PARAMETER_LINE = re.compile(r"^\s*(?P<name>\*{0,2}[A-Za-z_]\w*)(?:\s+\([^)]*\))?:\s*(?P<description>\S.*)$")


class _FunctionOutputVisitor(ast.NodeVisitor):
    """Find return and yield statements belonging to one function."""

    def __init__(self) -> None:
        """Initialize the visitor's output flags."""
        self._root: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        self.has_return_value = False
        self.has_yield = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit only the root function, skipping nested function bodies.

        Args:
            node: Function declaration to inspect.
        """
        if self._root is None:
            self._root = node
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit only the root async function, skipping nested function bodies.

        Args:
            node: Async function declaration to inspect.
        """
        if self._root is None:
            self._root = node
            self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Skip nested class bodies when inspecting a function.

        Args:
            node: Nested class declaration to skip.
        """

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Skip lambda bodies when inspecting a function.

        Args:
            node: Lambda expression to skip.
        """

    def visit_Return(self, node: ast.Return) -> None:
        """Record whether a return statement produces a value.

        Args:
            node: Return statement to inspect.
        """
        self.has_return_value |= node.value is not None and not _is_none_expression(node.value)

    def visit_Yield(self, node: ast.Yield) -> None:
        """Record a yielded output.

        Args:
            node: Yield expression to inspect.
        """
        self.has_yield = True

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """Record an output yielded from another iterable.

        Args:
            node: Yield-from expression to inspect.
        """
        self.has_yield = True


class _DocstringVisitor(ast.NodeVisitor):
    """Collect missing Python declaration and parameter documentation."""

    def __init__(self, file_path: str) -> None:
        """Create a checker for one Python source file.

        Args:
            file_path: Display path used in diagnostics.
        """
        self.file_path = file_path
        self.issues: list[str] = []
        self._scope: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check a class docstring and inspect its declarations.

        Args:
            node: Class declaration to inspect.
        """
        if not _has_docstring(node):
            self.issues.append(f"{self.file_path}:{node.lineno}: class {node.name!r} is missing a docstring")
        self._scope.append("class")
        try:
            self.generic_visit(node)
        finally:
            self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check a function or method docstring and inspect nested declarations.

        Args:
            node: Function declaration to inspect.
        """
        self._check_function(node, is_method=bool(self._scope and self._scope[-1] == "class"))
        self._scope.append("function")
        try:
            self.generic_visit(node)
        finally:
            self._scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check an async function or method docstring and inspect nested declarations.

        Args:
            node: Async function declaration to inspect.
        """
        self._check_function(node, is_method=bool(self._scope and self._scope[-1] == "class"))
        self._scope.append("function")
        try:
            self.generic_visit(node)
        finally:
            self._scope.pop()

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> None:
        """Check a function's docstring, inputs, and outputs.

        Args:
            node: Function declaration to inspect.
            is_method: Whether the declaration is directly inside a class.
        """
        docstring = ast.get_docstring(node)
        declaration = "method" if is_method else "function"
        if not docstring or not docstring.strip():
            self.issues.append(f"{self.file_path}:{node.lineno}: {declaration} {node.name!r} is missing a docstring")
            return

        parameters = _function_parameters(node, is_method and not _is_static_method(node))
        documented = _documented_parameters(docstring)
        missing = [parameter for parameter in parameters if parameter not in documented]
        if missing:
            self.issues.append(
                f"{self.file_path}:{node.lineno}: {declaration} {node.name!r} does not document "
                f"input parameter(s): {', '.join(missing)} in an Args section"
            )

        output_section = _output_section(node)
        if output_section and not _section_has_content(docstring, output_section):
            self.issues.append(
                f"{self.file_path}:{node.lineno}: {declaration} {node.name!r} is missing a non-empty "
                f"{output_section} section"
            )


def _has_docstring(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a declaration has a non-empty docstring.

    Args:
        node: Declaration to inspect.

    Returns:
        True if its docstring contains non-whitespace text.
    """
    docstring = ast.get_docstring(node)
    return bool(docstring and docstring.strip())


def _function_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> list[str]:
    """Return the function's documented input parameter names.

    Args:
        node: Function declaration whose signature is inspected.
        is_method: Whether to exclude the conventional receiver parameter.

    Returns:
        Parameter names in signature order.
    """
    arguments = node.args
    parameters = [*arguments.posonlyargs, *arguments.args]
    if arguments.vararg:
        parameters.append(arguments.vararg)
    parameters.extend(arguments.kwonlyargs)
    if arguments.kwarg:
        parameters.append(arguments.kwarg)

    names = [parameter.arg for parameter in parameters]
    if is_method and names and names[0] in {"self", "cls"}:
        names.pop(0)
    return names


def _is_static_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a class function is decorated as a static method.

    Args:
        node: Function declaration whose decorators are inspected.

    Returns:
        True if one of its decorators is staticmethod.
    """
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            decorator = decorator.func
        if isinstance(decorator, ast.Name) and decorator.id == "staticmethod":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "staticmethod":
            return True
    return False


def _documented_parameters(docstring: str) -> set[str]:
    """Extract parameter names with descriptions from a Google-style section.

    Args:
        docstring: Function docstring to inspect.

    Returns:
        Parameter names listed in its Args, Arguments, or Parameters section.
    """
    for heading in ("Args", "Arguments", "Parameters"):
        section = _section_lines(docstring, heading)
        if section is not None:
            documented = set()
            for line in section:
                match = _PARAMETER_LINE.match(line)
                if match:
                    documented.add(match.group("name").lstrip("*"))
            return documented
    return set()


def _output_section(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Return the documentation section required by a function's outputs.

    Args:
        node: Function declaration whose outputs are inspected.

    Returns:
        Returns, Yields, or None when the function has no output.
    """
    visitor = _FunctionOutputVisitor()
    visitor.visit(node)
    if visitor.has_yield:
        return "Yields"

    annotation = node.returns
    if annotation is not None and (_is_none_annotation(annotation) or _is_no_return_annotation(annotation)):
        return None
    if annotation is not None or visitor.has_return_value:
        return "Returns"
    return None


def _is_none_expression(expression: ast.expr) -> bool:
    """Return whether an expression is the literal None.

    Args:
        expression: Expression to inspect.

    Returns:
        True only for the None literal.
    """
    return isinstance(expression, ast.Constant) and expression.value is None


def _is_none_annotation(annotation: ast.expr) -> bool:
    """Return whether a return annotation explicitly declares None.

    Args:
        annotation: Return annotation to inspect.

    Returns:
        True when the annotation is None or the string "None".
    """
    if isinstance(annotation, ast.Name):
        return annotation.id == "None"
    return isinstance(annotation, ast.Constant) and annotation.value in (None, "None")


def _is_no_return_annotation(annotation: ast.expr) -> bool:
    """Return whether an annotation indicates that a function never returns.

    Args:
        annotation: Return annotation to inspect.

    Returns:
        True when the annotation names NoReturn or Never.
    """
    if isinstance(annotation, ast.Name):
        return annotation.id in {"NoReturn", "Never"}
    return isinstance(annotation, ast.Attribute) and annotation.attr in {"NoReturn", "Never"}


def _section_lines(docstring: str, heading: str) -> list[str] | None:
    """Return lines under a Google-style section heading.

    Args:
        docstring: Docstring containing the section.
        heading: Section heading to find without its trailing colon.

    Returns:
        Section body lines, or None when the heading is absent.
    """
    lines = docstring.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == f"{heading}:"), None)
    if start is None:
        return None

    section = []
    for line in lines[start + 1 :]:
        if line.strip() in _SECTION_HEADINGS:
            break
        if line.strip():
            section.append(line)
    return section


def _section_has_content(docstring: str, heading: str) -> bool:
    """Return whether a documentation section contains non-empty text.

    Args:
        docstring: Docstring containing the section.
        heading: Section heading to inspect.

    Returns:
        True if the section has at least one non-blank line.
    """
    section = _section_lines(docstring, heading)
    return bool(section)


def check_source(file_path: str, source: str) -> list[str]:
    """Check one Python source string for documentation violations.

    Args:
        file_path: Display path used in diagnostics.
        source: Python source text to parse and inspect.

    Returns:
        Documentation or syntax issues found in the source.
    """
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as error:
        return [f"{file_path}:{error.lineno or 1}: invalid Python syntax: {error.msg}"]

    visitor = _DocstringVisitor(file_path)
    visitor.visit(tree)
    return visitor.issues


def main(argv: list[str] | None = None) -> int:
    """Check Python files selected by the caller.

    Args:
        argv: File paths supplied by pre-commit or the command line.

    Returns:
        Zero when all files pass, one for violations, or two for usage errors.
    """
    paths = [Path(path) for path in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print("Provide at least one Python file path.", file=sys.stderr)
        return 2

    issues = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as error:
            issues.append(f"{path}: unable to read Python source: {error}")
            continue
        issues.extend(check_source(str(path), source))

    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
