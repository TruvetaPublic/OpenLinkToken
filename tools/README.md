# Development Tools

- [Development Tools](#development-tools)
  - [Java Multi-Language Sync Tool](#java-multi-language-sync-tool)
    - [Overview](#overview)
    - [Usage](#usage)
      - [Command Line Interface](#command-line-interface)
      - [GitHub Actions Integration](#github-actions-integration)
    - [Configuration](#configuration)
      - [Mapping File: `tools/java-language-mappings.json`](#mapping-file-toolsjava-language-mappingsjson)
      - [Configuration Options](#configuration-options)
    - [File Naming \& Handler Conventions](#file-naming--handler-conventions)
    - [Output Formats](#output-formats)
      - [Console Format (Default)](#console-format-default)
      - [GitHub Checklist Format](#github-checklist-format)
      - [JSON Format](#json-format)
    - [Workflow Integration](#workflow-integration)
      - [GitHub Actions Workflow](#github-actions-workflow)
    - [Related Files](#related-files)

## Java Multi-Language Sync Tool

### Overview
The multi-language sync tool detects changes in Java source files (source of truth) and evaluates synchronization status for enabled target languages (currently Python; C# scaffolds exist but are disabled). It supports source-centric configuration, automatic path/naming conversion via language handlers, progress tracking, and GitHub PR workflow enforcement.

Use this tool to ensure parity between Java and other implementations as they evolve.

### Usage

#### Command Line Interface
```bash
# Basic sync check (compares against PR base or HEAD~1)
python3 tools/java_language_syncer.py

# Check against specific branch/commit
python3 tools/java_language_syncer.py --since origin/main

# Generate GitHub-style checklist
python3 tools/java_language_syncer.py --format github-checklist

# Output as JSON for automation
python3 tools/java_language_syncer.py --format json

# Comprehensive health check
python3 tools/java_language_syncer.py --health-check

# Validate configuration only
python3 tools/java_language_syncer.py --validate-only
```

#### GitHub Actions Integration
The tool automatically runs on pull requests via the `.github/workflows/java-python-sync-enhanced.yml` workflow:

- **Triggers**: On PR open, synchronize, or reopen
- **Scope**: Changes to Java files in `lib/java/opentoken/src/main/java/com/truveta/opentoken/` or Python files in `lib/python/opentoken/src/`
- **Output**: Automated PR comments with progress tracking and checklists
- **Permissions**: Requires `issues: write` and `pull-requests: write` permissions

### Configuration

 
#### Mapping File: `tools/java-language-mappings.json`

The tool uses a source-centric JSON mapping file. High-level structure:

```json
{
  "source_language": "java",
  "source_base_path": "lib/java/opentoken/src/",
  "critical_java_files": [
    {
      "path": "main/java/com/truveta/opentoken/tokentransformer/HashTokenTransformer.java",
      "priority": "high",
      "description": "Core hash transformer",
      "manual_review": true
    }
  ],
  "directory_roots": [
    { "path": "main/java/com/truveta/opentoken/attributes/", "priority": "medium" },
    { "path": "test/java/com/truveta/opentoken/", "priority": "low" }
  ],
  "target_languages": {
    "python": {
      "enabled": true,
      "base_path": "lib/python/opentoken/src",
      "naming_convention": "snake_case",
      "file_extension": ".py",
      "overrides": {
        "critical_files": {
          "main/java/com/truveta/opentoken/tokentransformer/HashTokenTransformer.java": "lib/python/opentoken/src/main/opentoken/tokentransformer/hash_token_transformer.py"
        }
      }
    },
    "csharp": { "enabled": false }
  },
  "ignore_patterns": ["**/generated/**", "**/target/**"],
  "auto_generate_unmapped": true
}
```

#### Configuration Options

Key configuration concepts:

- **`source_base_path`**: Root prefix for all Java paths used in source-centric lists.
- **`critical_java_files`**: Array of Java file descriptors (path relative to source base, optional priority & manual_review). Overrides per language live under `target_languages.<lang>.overrides.critical_files`.
- **`directory_roots`**: Source directories to auto-map; handler converts file names.
- **`target_languages`**: Language-specific enablement and naming/file extension settings; optional overrides.
- **Legacy keys (`critical_files`, `directory_mappings`)**: Still supported for backward compatibility but superseded by source-centric lists.
- **`ignore_patterns`**: Glob patterns excluded from sync evaluation.
- **`auto_generate_unmapped`**: If true, unmapped Java files falling outside explicit lists are auto-mapped.

 
### File Naming & Handler Conventions

Handlers implement language-specific path and naming conversion:

- **PythonHandler**: CamelCase → snake_case, `Test.java` → `_test.py`
- **CSharpHandler (scaffold)**: Preserves PascalCase, `Test.java` → `Tests.cs`

Examples (Python enabled):

```text
Java: lib/java/opentoken/src/main/java/com/truveta/opentoken/attributes/BirthDateAttribute.java
Python: lib/python/opentoken/src/main/opentoken/attributes/birth_date_attribute.py

Java: lib/java/opentoken/src/test/java/com/truveta/opentoken/TokenGeneratorTest.java
Python: lib/python/opentoken/src/test/opentoken/token_generator_test.py
```

### Output Formats

 
#### Console Format (Default)

```text
Java changes detected (1 Java files):
============================================================

📁 lib/java/opentoken/src/main/java/com/truveta/opentoken/TokenGenerator.java:
   ✅ 🔄 lib/python/opentoken/src/main/opentoken/token_generator.py
----------------------------------------

PROGRESS SUMMARY:
Total sync items: 1
Recently updated: 1
Still pending: 0

LEGEND:
  ✅ = File exists, ❌ = File missing
  🔄 = Up-to-date (Python modified after Java), ⏳ = Out-of-date (needs update)
```

 
#### GitHub Checklist Format

```markdown
## Java to Python Sync Required (1/2 completed)

### 📁 `lib/java/opentoken/src/main/java/com/truveta/opentoken/TokenGenerator.java`
- [x] **🔄 UPDATED**: `lib/python/opentoken/src/main/opentoken/token_generator.py`
- [ ] **⏳ NEEDS UPDATE**: `lib/python/opentoken/src/test/opentoken/token_generator_test.py`

✅ **Progress**: 1 of 2 items completed
```

 
#### JSON Format

```json
{
  "mappings": [...],
  "python_changes": [...],
  "total_items": 2,
  "completed_items": 1
}
```

### Workflow Integration

 
#### GitHub Actions Workflow

The enhanced workflow (`.github/workflows/java-python-sync-enhanced.yml`) provides:

1. **Change Detection**: Compares against PR base branch for accurate change detection
2. **Progress Tracking**: Tracks completion across multiple commits
3. **Comment Management**: Maintains clean PR history by replacing previous comments
4. **Status Reporting**: Provides both workflow logs and PR comments

 
### Related Files

- `tools/java_language_syncer.py` - Main tool implementation
- `tools/java-language-mappings.json` - Source-centric configuration file
- `tools/sync-check.sh` - Shell wrapper script for CI enforcement
- `.github/workflows/java-language-sync.yml` - GitHub Actions workflow
