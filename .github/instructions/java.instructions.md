---
description: "Guidelines for building Java applications"
applyTo: "**/*.java"
---

# Java Development

## General Instructions

- Use IDE / Code editor reported warnings and suggestions to catch common patterns early in development.
- Address code smells proactively during development rather than accumulating technical debt.
- Focus on readability, maintainability, and performance when refactoring identified issues.

## Best practices

- **Imports**: Never use fully qualified class names in Java code. Add imports and use short class names.
- **Lombok**: This codebase uses Lombok extensively. Use:
  - `@Builder` for immutable object construction (preferred over Java Records for complex objects)
  - `@NonNull` for required fields with null-checking
  - `@Data` or `@Value` for data classes
  - `@Slf4j` for logging instead of manual Logger creation
- **Records**: For simple data transfer objects without Lombok, Java Records can be used.
- **Pattern Matching**: Utilize pattern matching for `instanceof` and `switch` expression to simplify conditional logic and type casting.
- **Type Inference**: Use `var` for local variable declarations to improve readability, but only when the type is explicitly clear from the right-hand side of the expression.
- **Immutability**: Favor immutable objects. Make classes and fields `final` where possible. Use collections from `List.of()`/`Map.of()` for fixed data. Use `Stream.toList()` to create immutable lists.
- **Streams and Lambdas**: Use the Streams API and lambda expressions for collection processing. Employ method references (e.g., `stream.map(Foo::toBar)`).
- **Null Handling**: Avoid returning or accepting `null`. Use `Optional<T>` for possibly-absent values and `Objects` utility methods like `equals()` and `requireNonNull()`.

### Naming Conventions

- Follow Google's Java style guide:
  - `UpperCamelCase` for class and interface names.
  - `lowerCamelCase` for method and variable names.
  - `UPPER_SNAKE_CASE` for constants.
  - `lowercase` for package names.
- Use nouns for classes (`UserService`) and verbs for methods (`getUserById`).
- Avoid abbreviations and Hungarian notation.

## Build and Verification

- After adding or modifying code, verify the project continues to build successfully.
- Run the full build with tests:
  ```bash
  cd lib/java && mvn clean install
  ```
- For a faster verification pass while iterating:
  ```bash
  cd lib/java && mvn test
  ```
- Run Checkstyle explicitly when needed:
  ```bash
  cd lib/java/openlinktoken && mvn checkstyle:check
  ```
- Ensure all tests pass as part of the build.
- **Code Review Checklist**: Before finalizing any Java code changes, verify:
  - All classes use direct imports at the top of the file instead of fully qualified class names in the code
  - Remove any unused imports
  - Organize imports in logical groups (Java standard library, third-party libraries, project classes)

### Common Bug Patterns

Below are concise, human-readable rules you can apply regardless of which static analysis tool you use. If you run Sonar/SonarLint, the IDE will show the matching rule and location — direct Sonar connections are preferred and should override this ruleset.

- Resource management — Always close resources (files, sockets, streams). Use try-with-resources where possible so resources are closed automatically.
- Equality checks — Compare object equality with `.equals()` or `Objects.equals(...)` rather than `==` for non-primitives; this avoids reference-equality bugs.
- Redundant casts — Remove unnecessary casts; prefer correct generic typing and let the compiler infer types where possible.
- Reachable conditions — Avoid conditional expressions that are always true or false; they indicate bugs or dead code and should be corrected.

For contributors who _do_ use Sonar or SonarLint: the IDE/scan will show the specific rule key (for example, S2095 for resource leaks) and the affected file/line. Use that information to navigate to the exact location, then apply the recommended remediation.

### Common Code Smells

These patterns are phrased for humans; they map cleanly to checks in Sonar, SpotBugs, PMD, or Checkstyle but do not require those tools to be useful.

- Parameter count — Keep method parameter lists short. If a method needs many params, consider grouping into a value object or using the builder pattern.
- Method size — Keep methods focused and small. Extract helper methods to improve readability and testability.
- Cognitive complexity — Reduce nested conditionals and heavy branching by extracting methods, using polymorphism, or applying the Strategy pattern.
- Duplicated literals — Extract repeated strings and numbers into named constants or enums to reduce errors and ease changes.
- Dead code — Remove unused variables and assignments. They confuse readers and can hide bugs.
- Magic numbers — Replace numeric literals with named constants that explain intent (e.g., MAX_RETRIES).

If you run a static analyzer like Sonar or SonarLint — direct Sonar connections are preferred and should override this ruleset. Sonar rule keys are useful for automation and suppression, but they are not required in day-to-day developer guidance.
