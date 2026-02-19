# Development Tools

- [Development Tools](#development-tools)
  - [Multi-Language Sync Tool](#multi-language-sync-tool)
    - [Overview](#overview)
    - [Usage](#usage)
      - [Command Line Interface](#command-line-interface)
      - [Shell Wrapper](#shell-wrapper)
      - [GitHub Actions Integration](#github-actions-integration)
    - [Configuration](#configuration)
    - [Output Formats](#output-formats)
      - [Console Format (Default)](#console-format-default)
      - [GitHub Checklist Format](#github-checklist-format)
      - [JSON Format](#json-format)
    - [Workflow Integration](#workflow-integration)
    - [Related Files](#related-files)

## Multi-Language Sync Tool

### Overview

The multi-language sync tool detects changes in any supported language (Java, Python, or Node.js) and identifies corresponding files in the other languages that need updating. It tracks sync progress across commits in a PR and posts checklists to GitHub PRs via GitHub Actions.

Use this tool to ensure parity between Java, Python, and future language implementations as they evolve.

### Usage

#### Command Line Interface

```bash
# Basic sync check (compares against HEAD~1)
python3 tools/multi_language_syncer.py

# Check against specific branch/commit
python3 tools/multi_language_syncer.py --since origin/main

# Generate GitHub-style checklist
python3 tools/multi_language_syncer.py --format github-checklist

# Output as JSON for automation
python3 tools/multi_language_syncer.py --format json

# Run health check
python3 tools/multi_language_syncer.py --health-check
```

#### Shell Wrapper

`sync-check.sh` wraps the Python tool with convenience options and optional GitHub issue creation:

```bash
# Basic usage
./tools/sync-check.sh

# Check PR against main branch with checklist output
./tools/sync-check.sh --since origin/main --format github-checklist

# Check only Java/Python sync
./tools/sync-check.sh --languages java,python --since origin/main

# Generate JSON report
./tools/sync-check.sh --format json --since origin/main

# Create GitHub issue with sync tasks (requires gh CLI)
./tools/sync-check.sh --issue --format github-checklist --since origin/main

# Quiet mode for scripting
./tools/sync-check.sh --quiet --format json
```

#### GitHub Actions Integration

The tool runs automatically on pull requests via `.github/workflows/multi-language-sync.yml`:

- **Triggers**: On PR open, synchronize, or reopen
- **Scope**: Changes to Java files in `lib/java/` or Python files in `lib/python/`
- **Output**: Automated PR comments with progress tracking and checklists
- **Permissions**: Requires `issues: write` and `pull-requests: write` permissions

### Configuration

Language paths are defined directly in `multi_language_syncer.py`:

```python
LANGUAGES = {
    'java':   {'path': 'lib/java/opentoken/src/main/java/com/truveta/opentoken/', ...},
    'python': {'path': 'lib/python/opentoken/src/main/opentoken/', ...},
}
```

An optional `tools/multi-language-mapping.json` file can supply `ignore_patterns`:

```json
{
  "ignore_patterns": ["**/generated/**", "**/target/**", "**/__pycache__/**"]
}
```

### Output Formats

#### Console Format (Default)

```text
Multi-Language Sync Report
============================================================

JAVA: 1 files changed
PYTHON: 0 files changed

============================================================
Sync Requirements:

Source: lib/java/opentoken/src/main/java/com/truveta/opentoken/TokenGenerator.java
  → python: ✓ lib/python/opentoken/src/main/opentoken/token_generator.py
  → nodejs: ✗ lib/nodejs/opentoken/src/TokenGenerator.ts
```

#### GitHub Checklist Format

```markdown
## Multi-Language Sync Required (1/2 completed)

### 🔹 From JAVA

#### 📁 `lib/java/opentoken/src/.../TokenGenerator.java`
- [x] **✓🔄 PYTHON**: `lib/python/opentoken/src/main/opentoken/token_generator.py`
- [ ] **✗⏳ NODEJS**: `lib/nodejs/opentoken/src/TokenGenerator.ts`

✅ **Progress**: 1 of 2 items completed
```

#### JSON Format

```json
{
  "sync_requirements": [...],
  "all_changes": {
    "java": ["lib/java/opentoken/.../TokenGenerator.java"],
    "python": [],
    "nodejs": []
  }
}
```

### Workflow Integration

The `.github/workflows/multi-language-sync.yml` workflow provides:

1. **Change Detection**: Compares against PR base branch for accurate change detection
2. **Progress Tracking**: Tracks completion across multiple commits in the same PR
3. **Comment Management**: Replaces previous sync comments to keep PR history clean
4. **Non-blocking**: Posts informational comments without hard-failing the workflow

### Related Files

- `tools/multi_language_syncer.py` - Main tool implementation
- `tools/multi-language-mapping.json` - Optional configuration (ignore patterns)
- `tools/sync-check.sh` - Shell wrapper script for CI and local use
- `.github/workflows/multi-language-sync.yml` - GitHub Actions workflow
