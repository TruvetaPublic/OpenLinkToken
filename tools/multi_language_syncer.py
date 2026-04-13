#!/usr/bin/env python3
"""
Multi-Language Sync Tool
Detects changes in any language (Java, Python, Node.js) and creates corresponding sync tasks
for the other languages.
"""

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path


class MultiLanguageSyncer:
    """Syncer that handles Java, Python, and Node.js implementations"""

    # Language configuration
    LANGUAGES = {
        "java": {
            "path": "lib/java/openlinktoken/src/main/java/org/openlinktoken/",
            "extension": ".java",
            "naming": "PascalCase",
            "group": "core",
        },
        "python": {
            "path": "lib/python/openlinktoken/src/main/openlinktoken/",
            "extension": ".py",
            "naming": "snake_case",
            "group": "core",
        },
        "python-cli": {
            "path": "lib/python/openlinktoken-cli/src/main/openlinktoken_cli/",
            "extension": ".py",
            "naming": "snake_case",
            "group": "cli",
        },
    }

    FALLBACK_MAPPINGS = {
        "critical_files": {},
        "directory_mappings": {},
        "ignore_patterns": [],
        "auto_generate_unmapped": True,
    }

    def __init__(self, mapping_file="tools/multi-language-mapping.json"):
        self.root_dir = Path(__file__).parent.parent
        self.mapping_file = self.root_dir / mapping_file

        self.load_mappings()
        self._discover_active_languages()

    def _discover_active_languages(self):
        """Discover which languages have existing paths in the repository.

        Filters LANGUAGES to only include entries whose configured path exists
        on disk. This prevents spurious missing-sync tasks for languages that
        have not yet been implemented in this repository.
        """
        discovered = {
            lang: config for lang, config in self.LANGUAGES.items() if (self.root_dir / config["path"]).is_dir()
        }
        if discovered:
            self.LANGUAGES = discovered
        else:
            # Fall back to all languages if none are discovered (e.g. fresh clone
            # without any lib directories) to avoid silently doing nothing.
            pass

    def load_mappings(self):
        """Load the multi-language file mappings"""
        try:
            with open(self.mapping_file, "r") as f:
                self.mappings = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Mapping file not found: {self.mapping_file}")
            self.mappings = self.FALLBACK_MAPPINGS.copy()
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in mapping file: {e}")
            self.mappings = self.FALLBACK_MAPPINGS.copy()

    def get_changes_for_language(self, language, since_commit="HEAD~1"):
        """Get list of changed files for a specific language

        Args:
            language: The language to check ('java', 'python', or 'nodejs')
            since_commit: The commit to compare against

        Returns:
            A list of changed files for that language
        """
        if language not in self.LANGUAGES:
            return []

        lang_config = self.LANGUAGES[language]
        lang_path = lang_config["path"]

        try:
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-only",
                    f"{since_commit}",
                    "HEAD",
                    "--",
                    lang_path,
                ],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )

            if result.returncode == 0:
                all_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                return self._filter_ignored_files(all_files)
            return []
        except subprocess.CalledProcessError:
            return []

    def _filter_ignored_files(self, files):
        """Filter out files that match ignore patterns"""
        ignore_patterns = self.mappings.get("ignore_patterns", [])
        filtered_files = []

        for file in files:
            should_ignore = False
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(file, pattern):
                    should_ignore = True
                    break

            if not should_ignore:
                filtered_files.append(file)

        return filtered_files

    def get_file_last_modified_commit(self, file_path, since_commit="HEAD~1"):
        """Get the most recent commit that modified a specific file"""
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "-1",
                    "--format=%H %ct",
                    f"{since_commit}..HEAD",
                    "--",
                    file_path,
                ],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )

            if result.returncode == 0 and result.stdout.strip():
                commit_hash, timestamp = result.stdout.strip().split()
                return {"commit": commit_hash, "timestamp": int(timestamp)}
            return None
        except subprocess.CalledProcessError:
            return None

    def is_file_up_to_date(self, source_file, target_file, since_commit="HEAD~1"):
        """Check if target file was touched anywhere in the PR when the source was also touched.

        A sync pair is considered complete as long as both files were modified
        at least once in the PR, regardless of commit order.
        """
        source_last_modified = self.get_file_last_modified_commit(source_file, since_commit)
        target_last_modified = self.get_file_last_modified_commit(target_file, since_commit)

        # If source file wasn't modified at all in this PR, no sync needed
        if not source_last_modified:
            return True

        # Target is up-to-date if it was touched anywhere in the PR
        return target_last_modified is not None

    def check_file_exists(self, file_path):
        """Check if a file exists"""
        return (self.root_dir / file_path).exists()

    def convert_filename(self, filename, from_naming, to_naming):
        """Convert filename between naming conventions"""
        # Remove extension
        base_name = filename
        for lang_config in self.LANGUAGES.values():
            if filename.endswith(lang_config["extension"]):
                base_name = filename[: -len(lang_config["extension"])]
                break

        # Convert naming convention
        if from_naming == "PascalCase" and to_naming == "snake_case":
            # Convert PascalCase to snake_case
            base_name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", base_name)
            base_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", base_name).lower()
        elif from_naming == "snake_case" and to_naming == "PascalCase":
            # Convert snake_case to PascalCase
            base_name = "".join(word.capitalize() for word in base_name.split("_"))

        return base_name

    def get_corresponding_files(self, source_file, source_lang, active_languages=None):
        """Get corresponding files in other languages

        Args:
            source_file: Path to the source file
            source_lang: Language of the source file
            active_languages: Optional dict of language configs to restrict results to.
                              Defaults to all LANGUAGES when None.
        """
        corresponding = {}

        # Extract relative path within language directory
        lang_config = self.LANGUAGES[source_lang]
        source_path = source_file.replace(lang_config["path"], "")

        # Try to map to other languages in the same group only (e.g. cli→cli, core→core).
        # This prevents CLI command/processor files from being projected onto core library
        # paths where they don't belong, which would generate false-positive sync tasks.
        source_group = lang_config.get("group")
        target_pool = active_languages if active_languages is not None else self.LANGUAGES
        for target_lang, target_config in target_pool.items():
            if target_lang == source_lang:
                continue
            if source_group and target_config.get("group") != source_group:
                continue

            # Convert directory structure (usually similar)
            target_path = source_path
            path_parts = target_path.split("/")
            if path_parts:
                filename = path_parts[-1]
                converted = self.convert_filename(filename, lang_config["naming"], target_config["naming"])
                path_parts[-1] = converted + target_config["extension"]
                target_path = "/".join(path_parts)

            target_file = target_config["path"] + target_path
            corresponding[target_lang] = target_file

        return corresponding

    def run_health_check(self):
        """Run a health check to validate tool configuration and environment

        Returns:
            A tuple of (passed: bool, report: str)
        """
        issues = []
        checks = []

        # Check 1: Git is available
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                checks.append(("✓", "Git", f"available ({result.stdout.strip()})"))
            else:
                issues.append("Git is not properly configured")
                checks.append(("✗", "Git", "not available"))
        except FileNotFoundError:
            issues.append("Git command not found on PATH")
            checks.append(("✗", "Git", "not found"))

        # Check 2: Root directory is a git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )
            if result.returncode == 0:
                checks.append(("✓", "Git Repository", f"found at {self.root_dir}"))
            else:
                issues.append(f"Root directory {self.root_dir} is not a git repository")
                checks.append(("✗", "Git Repository", "not found"))
        except subprocess.CalledProcessError:
            issues.append(f"Cannot verify git repository at {self.root_dir}")
            checks.append(("✗", "Git Repository", "verification failed"))

        # Check 3: Language paths exist
        for lang, config in self.LANGUAGES.items():
            lang_path = self.root_dir / config["path"]
            if lang_path.exists() and lang_path.is_dir():
                checks.append(("✓", f"{lang.upper()} Path", str(config["path"])))
            else:
                issues.append(f"{lang.upper()} path does not exist: {config['path']}")
                checks.append(("✗", f"{lang.upper()} Path", str(config["path"])))

        # Check 4: Mapping file
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, "r") as f:
                    json.load(f)
                checks.append(("✓", "Mapping File", f"{self.mapping_file.name} (valid JSON)"))
            except json.JSONDecodeError as e:
                issues.append(f"Mapping file contains invalid JSON: {e}")
                checks.append(("✗", "Mapping File", f"{self.mapping_file.name} (invalid JSON)"))
        else:
            checks.append(
                (
                    "⚠",
                    "Mapping File",
                    f"not found at {self.mapping_file} (using defaults)",
                )
            )

        # Check 5: Ignore patterns in mapping
        ignore_patterns = self.mappings.get("ignore_patterns", [])
        if ignore_patterns:
            checks.append(
                (
                    "✓",
                    "Ignore Patterns",
                    f"{len(ignore_patterns)} pattern(s) configured",
                )
            )
        else:
            checks.append(("ℹ", "Ignore Patterns", "none configured"))

        # Check 6: Can execute git commands
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )
            if result.returncode == 0:
                checks.append(("✓", "Git Commands", "working"))
            else:
                issues.append("Cannot execute git commands")
                checks.append(("✗", "Git Commands", "failed"))
        except subprocess.CalledProcessError:
            issues.append("Failed to execute git commands")
            checks.append(("✗", "Git Commands", "failed"))

        # Format report
        output = "Multi-Language Sync Tool - Health Check Report\n"
        output += "=" * 60 + "\n\n"

        for symbol, name, status in checks:
            output += f"{symbol} {name:.<20} {status}\n"

        output += "\n" + "=" * 60 + "\n"

        if issues:
            output += f"⚠️  {len(issues)} issue(s) found:\n\n"
            for i, issue in enumerate(issues, 1):
                output += f"  {i}. {issue}\n"
            output += "\nStatus: ❌ FAILED\n"
            return (False, output)
        else:
            output += "Status: ✅ PASSED\n"
            return (True, output)

    def generate_sync_report(self, output_format="console", since_commit="HEAD~1", languages=None):
        """Generate a report of files that need syncing across all languages

        Returns:
            A tuple of (report: str, is_complete: bool) where is_complete indicates
            whether all syncs are up-to-date. Returns (report, True) when no changes
            are detected (nothing to do).

        Args:
            output_format: One of 'console', 'json', or 'github-checklist'
            since_commit: The commit to compare against
            languages: Optional list of language names to restrict the check to.
                       Both source detection and target mapping are filtered to
                       only the specified languages. Defaults to all languages.
        """
        active_languages = {k: v for k, v in self.LANGUAGES.items() if languages is None or k in languages}

        # Get changes for each active language
        all_changes = {}
        for lang in active_languages:
            all_changes[lang] = self.get_changes_for_language(lang, since_commit)

        # Check if any changes were made
        total_changes = sum(len(changes) for changes in all_changes.values())
        if total_changes == 0:
            if output_format == "github-checklist":
                return (
                    "✅ All changes appear to be in sync across Java, Python, and Node.js!",
                    True,
                )
            else:
                return ("No changes detected in any language.", True)

        # Build sync requirements
        sync_requirements = []

        for source_lang, changed_files in all_changes.items():
            for source_file in changed_files:
                corresponding = self.get_corresponding_files(source_file, source_lang, active_languages)
                sync_requirements.append(
                    {
                        "source_lang": source_lang,
                        "source_file": source_file,
                        "corresponding": corresponding,
                    }
                )

        report = self.format_output(sync_requirements, all_changes, output_format, since_commit)
        is_complete = self._check_sync_complete(sync_requirements, since_commit)

        return (report, is_complete)

    def format_output(
        self,
        sync_requirements,
        all_changes,
        output_format="console",
        since_commit="HEAD~1",
    ):
        """Format the output based on the specified format"""
        if output_format == "github-checklist":
            return self.format_github_checklist(sync_requirements, all_changes, since_commit)
        elif output_format == "json":
            return json.dumps(
                {"sync_requirements": sync_requirements, "all_changes": all_changes},
                indent=2,
            )
        else:
            return self.format_console(sync_requirements, all_changes, since_commit)

    def _check_sync_complete(self, sync_requirements, since_commit="HEAD~1"):
        """Check if all sync requirements are complete (up-to-date)

        Returns:
            True if all corresponding files are up-to-date, False otherwise
        """
        for req in sync_requirements:
            for target_lang, target_file in req["corresponding"].items():
                if not self.is_file_up_to_date(req["source_file"], target_file, since_commit):
                    return False
        return True

    def format_github_checklist(self, sync_requirements, all_changes, since_commit):
        """Format output as GitHub markdown checklist"""
        if not sync_requirements:
            return "✅ All changes appear to be in sync across Java, Python, and Node.js!"

        total_items = 0
        completed_items = 0

        output = "## Multi-Language Sync Required\n\n"

        # Group by source language
        by_lang = {}
        for req in sync_requirements:
            lang = req["source_lang"]
            if lang not in by_lang:
                by_lang[lang] = []
            by_lang[lang].append(req)

        for source_lang in sorted(by_lang.keys()):
            output += f"### 🔹 From {source_lang.upper()}\n\n"

            for req in by_lang[source_lang]:
                source_file = req["source_file"]
                output += f"#### 📁 `{source_file}`\n"

                for target_lang, target_file in sorted(req["corresponding"].items()):
                    total_items += 1
                    exists = self.check_file_exists(target_file)
                    is_up_to_date = self.is_file_up_to_date(source_file, target_file, since_commit)

                    if is_up_to_date:
                        checkbox = "- [x]"
                        status = "✓🔄"
                        completed_items += 1
                    elif exists:
                        checkbox = "- [ ]"
                        status = "✓⏳"
                    else:
                        checkbox = "- [ ]"
                        status = "✗⏳"

                    output += f"{checkbox} **{status} {target_lang.upper()}**: `{target_file}`\n"

                output += "\n"

        # Update the header with completion count
        output = output.replace(
            "## Multi-Language Sync Required\n\n",
            f"## Multi-Language Sync Required ({completed_items}/{total_items} completed)\n\n",
        )

        if completed_items > 0:
            output += f"✅ **Progress**: {completed_items} of {total_items} items completed\n"

        return output

    def format_console(self, sync_requirements, all_changes, since_commit):
        """Format output for console"""
        output = "Multi-Language Sync Report\n"
        output += "=" * 60 + "\n\n"

        for lang, changes in all_changes.items():
            if changes:
                output += f"{lang.upper()}: {len(changes)} files changed\n"

        output += "\n" + "=" * 60 + "\n"
        output += "Sync Requirements:\n\n"

        for req in sync_requirements:
            output += f"Source: {req['source_file']}\n"
            for target_lang, target_file in req["corresponding"].items():
                exists = "✓" if self.check_file_exists(target_file) else "✗"
                output += f"  → {target_lang}: {exists} {target_file}\n"
            output += "\n"

        return output


def main():
    """Main entry point

    Returns:
        0 if successful (health check passed or sync is complete)
        1 if sync is incomplete (corresponding files not updated)
    """
    parser = argparse.ArgumentParser(description="Multi-language sync checker")
    parser.add_argument(
        "--format",
        choices=["console", "json", "github-checklist"],
        default="console",
        help="Output format",
    )
    parser.add_argument("--since", default="HEAD~1", help="Compare since this commit")
    parser.add_argument(
        "--languages",
        help="Comma-separated list of languages to check (e.g., java,python)",
    )
    parser.add_argument("--health-check", action="store_true", help="Run health check")

    args = parser.parse_args()

    languages = [lang.strip() for lang in args.languages.split(",")] if args.languages else None

    syncer = MultiLanguageSyncer()

    if args.health_check:
        passed, report = syncer.run_health_check()
        print(report)
        sys.exit(0 if passed else 1)

    report, is_complete = syncer.generate_sync_report(args.format, args.since, languages)

    if report:
        print(report)

    sys.exit(0 if is_complete else 1)


if __name__ == "__main__":
    main()
