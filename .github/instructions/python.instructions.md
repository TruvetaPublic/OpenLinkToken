---
description: "Python coding conventions and guidelines"
applyTo: "**/*.py"
---

# Python Coding Conventions

## Repo-Specific Runtime Rules

- Use the shared Python virtual environment at `/home/vscode/.local/share/opentoken/.venv`.
- The workspace-root `.venv` is a symlink to this shared environment in the devcontainer.
- Never create or activate a nested `.venv` under `lib/python/...`.
- Activate the shared environment with:

```bash
source /home/vscode/.local/share/opentoken/.venv/bin/activate
```

## Python Instructions

- Prefer clear, descriptive docstrings for functions; use inline comments sparingly to explain non-obvious intent or constraints, not obvious behavior.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following PEP 257 conventions.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Ensure lines do not exceed 120 characters (extended from PEP 8's 79 for PySpark chains).
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- **Remove unused imports and variables**: Always clean up unused imports and variables from your code. Running `ruff check --fix` can help automatically identify and remove these.
- Organize imports in standard order: standard library imports, third-party imports, then local application imports, with a blank line between each group.

### PySpark Import Rules (Critical)

- **Always use direct imports**: `from pyspark.sql.functions import col, lit, when, sum, count`
- **Never** use `import pyspark.sql.functions as F` pattern
- **Always place imports at the top of the file**, never inside methods or functions

### PySpark Method Chaining Indentation

When chaining PySpark DataFrame methods, place each `.method()` call on a new line with **additional indentation** (4 spaces beyond the opening parenthesis):

```python
# CORRECT - additional indentation for chained methods
result_df = (
    source_df
        .select(USER_ID, ORDER_ID, PRODUCT_ID)
        .withColumn(STATUS_CODE, lit(DEFAULT_STATUS).cast(IntegerType()))
        .withColumn(CREATED_AT, current_timestamp())
        .filter(col(IS_ACTIVE) == True)
)

# INCORRECT - no additional indentation
result_df = (
    source_df
    .select(USER_ID, ORDER_ID, PRODUCT_ID)
    .withColumn(STATUS_CODE, lit(DEFAULT_STATUS).cast(IntegerType()))
)
```

## Testing

### Running Tests

```bash
source /home/vscode/.local/share/opentoken/.venv/bin/activate

cd lib/python/opentoken && pytest
cd lib/python/opentoken-cli && pytest
```

### Installing Dependencies

```bash
source /home/vscode/.local/share/opentoken/.venv/bin/activate
cd lib/python/opentoken && uv pip install -r requirements.txt -r dev-requirements.txt
cd lib/python/opentoken-cli && uv pip install -r requirements.txt -r dev-requirements.txt
```

### Test Guidelines

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

## Example of Proper Documentation

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class DataProcessor(ABC):
    """
    Base class for all data processors.

    All processors must implement the process() method which contains the
    processor-specific logic.

    Attributes:
        config: Configuration dictionary with processor-specific settings.
        output_path: Path where processed results will be written.
    """

    def __init__(self, config: Dict[str, Any], output_path: str):
        self.config = config
        self.output_path = output_path

    @abstractmethod
    def process(self, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Process the input data according to processor-specific logic.

        Args:
            data: List of records to process, where each record is a dictionary.

        Returns:
            Optional dictionary containing processing results and metadata,
            or None if no results to return.
        """
        pass
```
