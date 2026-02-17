#!/usr/bin/env python3
"""
Java Multi-Language Sync Tool
Detects changes in Java codebase and creates corresponding sync tasks for target languages
Supports Python (enabled by default) with extensible architecture for future languages
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
import re
from abc import ABC, abstractmethod

# Constants
DEFAULT_SINCE_COMMIT = "HEAD~1"
NO_CHANGES_MESSAGE = "No Java changes detected."


class LanguageHandler(ABC):
    """Base class for language-specific sync logic"""
    
    def __init__(self, language_name, config):
        self.language_name = language_name
        self.config = config
        self.naming_convention = config.get('naming_convention', 'snake_case')
        self.file_extension = config.get('file_extension', '.py')
        self.base_path = config.get('base_path', '')
    
    @abstractmethod
    def convert_java_to_target_path(self, java_path):
        """Convert Java file path to target language path"""
        pass
    
    @abstractmethod
    def convert_java_to_target_naming(self, java_name):
        """Convert Java class name to target language naming"""
        pass
    
    def check_file_exists(self, root_dir, target_path):
        """Check if target file exists"""
        target_file = root_dir / target_path
        return target_file.exists()


class PythonHandler(LanguageHandler):
    """Python-specific logic (snake_case, .py extension)"""
    
    def convert_java_to_target_naming(self, java_name):
        """Convert Java CamelCase to Python snake_case"""
        # Handle test files: JavaTest -> java_test.py
        if java_name.endswith('Test.java'):
            class_name = java_name[:-9]  # Remove 'Test.java'
            snake_case = self._to_snake_case(class_name)
            return snake_case + '_test.py'
        elif java_name.endswith('.java'):
            class_name = java_name[:-5]  # Remove '.java'
            snake_case = self._to_snake_case(class_name)
            return snake_case + '.py'
        return java_name
    
    def convert_java_to_target_path(self, java_path):
        """Convert Java file path to Python path"""
        # Handle CLI main source files
        if "lib/java/opentoken-cli/src/main/java/com/truveta/opentoken/cli/" in java_path:
            python_path = java_path.replace(
                "lib/java/opentoken-cli/src/main/java/com/truveta/opentoken/cli/",
                "lib/python/opentoken-cli/src/main/opentoken_cli/"
            )
        # Handle CLI test files
        elif "lib/java/opentoken-cli/src/test/java/com/truveta/opentoken/cli/" in java_path:
            python_path = java_path.replace(
                "lib/java/opentoken-cli/src/test/java/com/truveta/opentoken/cli/",
                "lib/python/opentoken-cli/src/test/opentoken_cli/"
            )
        # Handle core main source files
        elif "lib/java/opentoken/src/main/java/com/truveta/opentoken/" in java_path:
            python_path = java_path.replace(
                "lib/java/opentoken/src/main/java/com/truveta/opentoken/",
                "lib/python/opentoken/src/main/opentoken/"
            )
        # Handle core test files
        elif "lib/java/opentoken/src/test/java/com/truveta/opentoken/" in java_path:
            python_path = java_path.replace(
                "lib/java/opentoken/src/test/java/com/truveta/opentoken/",
                "lib/python/opentoken/src/test/opentoken/"
            )
        else:
            python_path = java_path
        
        # Convert filename if it's a .java file
        if python_path.endswith('.java'):
            path_parts = python_path.rsplit('/', 1)
            if len(path_parts) == 2:
                directory, filename = path_parts
                converted_filename = self.convert_java_to_target_naming(filename)
                return directory + '/' + converted_filename
            else:
                return self.convert_java_to_target_naming(python_path)
        
        return python_path
    
    def _to_snake_case(self, camel_str):
        """Convert CamelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class CSharpHandler(LanguageHandler):
    """C#-specific logic (PascalCase, .cs extension)"""

    def convert_java_to_target_naming(self, java_name):
        # Test classes: SomeThingTest.java -> SomeThingTests.cs (convention)
        if java_name.endswith('Test.java'):
            base = java_name[:-9]  # remove Test.java
            return base + 'Tests.cs'
        elif java_name.endswith('.java'):
            base = java_name[:-5]
            return base + '.cs'
        return java_name

    def convert_java_to_target_path(self, java_path):
        # Replace Java source roots with hypothetical C# project structure
        if "lib/java/opentoken/src/main/java/com/truveta/opentoken/" in java_path:
            cs_path = java_path.replace(
                "lib/java/opentoken/src/main/java/com/truveta/opentoken/",
                "lib/csharp/OpenToken/src/"
            )
        elif "lib/java/opentoken/src/test/java/com/truveta/opentoken/" in java_path:
            cs_path = java_path.replace(
                "lib/java/opentoken/src/test/java/com/truveta/opentoken/",
                "lib/csharp/OpenToken/tests/"
            )
        else:
            cs_path = java_path

        if cs_path.endswith('.java'):
            directory, filename = cs_path.rsplit('/', 1)
            return directory + '/' + self.convert_java_to_target_naming(filename)
        return cs_path


class JavaLanguageSyncer:
    """Multi-language sync checker with Java as source of truth"""
    
    FALLBACK_MAPPINGS = {
        "source_language": "java",
        "target_languages": {},
        "auto_generate_unmapped": True
    }

    def __init__(self, mapping_file="tools/java-language-mappings.json"):
        self.root_dir = Path(__file__).parent.parent
        self.mapping_file = self.root_dir / mapping_file
        self.load_mappings()
        self.language_handlers = self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Initialize handlers for all enabled languages"""
        handlers = {}
        target_languages = self.mappings.get('target_languages', {})
        
        for lang, config in target_languages.items():
            if config.get('enabled', False):
                if lang == 'python':
                    handlers[lang] = PythonHandler(lang, config)
                elif lang == 'csharp':
                    handlers[lang] = CSharpHandler(lang, config)
        
        return handlers

    def load_mappings(self):
        """Load the Java to multi-language file mappings"""
        try:
            with open(self.mapping_file, 'r') as f:
                self.mappings = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Mapping file not found: {self.mapping_file}")
            self.mappings = self.FALLBACK_MAPPINGS.copy()
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in mapping file: {e}")
            self.mappings = self.FALLBACK_MAPPINGS.copy()

    def validate_configuration(self):
        """Validate the mapping configuration and repository state
        
        Args:
            None
            
        Returns:
            list: A list of validation issues found.
        """
        issues = []
        
        # Check if mapping file exists
        if not self.mapping_file.exists():
            issues.append(f"Mapping file not found: {self.mapping_file}")
            return issues
        
        # Validate top-level mapping structure
        required_keys = ['source_language', 'target_languages']
        for key in required_keys:
            if key not in self.mappings:
                issues.append(f"Missing required mapping key: {key}")
        
        # Validate each enabled language configuration
        target_languages = self.mappings.get('target_languages', {})
        for lang, config in target_languages.items():
            if not config.get('enabled', False):
                continue
            
            # Check critical files for each language
            if 'critical_files' in config:
                for java_path, mapping in config['critical_files'].items():
                    java_file = self.root_dir / java_path
                    if not java_file.exists():
                        issues.append(f"[{lang}] Mapped Java file not found: {java_path}")
                    
                    target_file = self.root_dir / mapping['target_file']
                    if not target_file.exists():
                        issues.append(f"[{lang}] Mapped {lang} file not found: {mapping['target_file']}")
        
        # Check Git repository status
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.root_dir)
            # Check if there are any uncommitted changes
            if result.stdout.strip():
                issues.append("Working directory has uncommitted changes")
        except subprocess.CalledProcessError:
            issues.append("Not in a Git repository or Git not available")
        
        return issues
    
    def health_check(self):
        """Perform a comprehensive health check of the sync system.
            Prints the health check results.
        """
        print("🔍 Performing Java multi-language sync health check...")
        print("=" * 50)
        
        issues = self.validate_configuration()
        
        if not issues:
            print("✅ Configuration validation passed")
        else:
            print("❌ Configuration issues found:")
            for issue in issues:
                print(f"   - {issue}")
        
        # Statistics
        print("\nMapping Statistics:")
        target_languages = self.mappings.get('target_languages', {})
        for lang, config in target_languages.items():
            if config.get('enabled', False):
                critical_count = len(config.get('critical_files', {}))
                directory_count = len(config.get('directory_mappings', {}))
                ignore_count = len(config.get('ignore_patterns', []))
                
                print(f"\n  {lang.upper()}:")
                print(f"   - Critical file mappings: {critical_count}")
                print(f"   - Directory mappings: {directory_count}")  
                print(f"   - Ignore patterns: {ignore_count}")
        
        return len(issues) == 0
    
    def get_java_changes(self, since_commit=DEFAULT_SINCE_COMMIT):
        """Get list of changed Java files since specified commit with timestamps

        Args:
            since_commit: The commit to compare against (default: HEAD~1)

        Returns:
            A list of changed Java files with their last modified timestamps
        """
        try:
            # For PR workflows, compare against the base branch
            if since_commit == "HEAD~1":
                # Try to get the merge base with main/origin/main
                try:
                    merge_base_result = subprocess.run([
                        'git', 'merge-base', 'HEAD', 'origin/main'
                    ], capture_output=True, text=True, cwd=self.root_dir)
                    
                    if merge_base_result.returncode == 0:
                        since_commit = merge_base_result.stdout.strip()
                        print(f"Comparing against PR base: {since_commit[:8]}")
                except subprocess.CalledProcessError:
                    # Fallback to HEAD~1 if merge-base fails
                    pass
            
            # Get changes from core library (exclude deleted files)
            result = subprocess.run([
                'git', 'diff', '--name-status', f'{since_commit}', 'HEAD', '--', 'lib/java/opentoken/src/'
            ], capture_output=True, text=True, cwd=self.root_dir)

            all_files = []
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2 and parts[0] != 'D':  # Exclude deleted files
                            all_files.append(parts[1])
            
            # Also get changes from CLI package (exclude deleted files)
            result_cli = subprocess.run([
                'git', 'diff', '--name-status', f'{since_commit}', 'HEAD', '--', 'lib/java/opentoken-cli/src/'
            ], capture_output=True, text=True, cwd=self.root_dir)

            if result_cli.returncode == 0:
                for line in result_cli.stdout.splitlines():
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2 and parts[0] != 'D':  # Exclude deleted files
                            all_files.append(parts[1])
            
            # Filter out ignored files
            return self._filter_ignored_files(all_files)
        except subprocess.CalledProcessError:
            return []

    def get_file_last_modified_commit(self, file_path, since_commit=DEFAULT_SINCE_COMMIT):
        """Get the most recent commit that modified a specific file
        
        Args:
            file_path: The path to the file to check.
            since_commit: The commit after which we would like to check file_path's status (default: HEAD~1)

        Returns:
            A dictionary containing the commit hash and timestamp of the last modification,
            or None if the file was not modified.
        """
        try:
            result = subprocess.run([
                'git', 'log', '-1', '--format=%H %ct', f'{since_commit}..HEAD', '--', file_path
            ], capture_output=True, text=True, cwd=self.root_dir)
            
            if result.returncode == 0 and result.stdout.strip():
                commit_hash, timestamp = result.stdout.strip().split()
                return {
                    'commit': commit_hash,
                    'timestamp': int(timestamp)
                }
            return None
        except subprocess.CalledProcessError:
            return None

    def is_target_file_up_to_date(self, java_file, target_file, since_commit=DEFAULT_SINCE_COMMIT, check_both_modified=False):
        """Check if target language file is up-to-date relative to Java file changes
        
        Args:
            java_file: The path to the Java file.
            target_file: The path to the target language file.
            since_commit: The commit after which we would like to check file modifications 
                (default: HEAD~1 will check against base of the branch).
            check_both_modified: If True, simply checks that both files were modified in the PR.
                If False (default), checks that target was modified after Java (timestamp-based).

        Returns:
            bool: True if the target file is up-to-date, False otherwise.
        """
        java_last_modified = self.get_file_last_modified_commit(java_file, since_commit)
        target_last_modified = self.get_file_last_modified_commit(target_file, since_commit)
        
        # If Java file wasn't modified at all in this PR, no sync needed
        if not java_last_modified:
            return True
            
        # If target file wasn't modified at all in this PR, it's out of date
        if not target_last_modified:
            return False
        
        # If check_both_modified is True, simply verify both were touched
        if check_both_modified:
            # Both files were modified in this PR, so sync is considered complete
            return True
            
        # Otherwise, use timestamp-based check: target is up-to-date if modified after Java
        return target_last_modified['timestamp'] >= java_last_modified['timestamp']

    def _filter_ignored_files(self, files):
        """Filter out files that match ignore patterns

        Args:
            files: A list of file paths to filter.

        Returns:
            A list of file paths that do not match any ignore patterns.
        """
        import fnmatch
        
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

    def get_target_language_changes(self, language, since_commit=DEFAULT_SINCE_COMMIT):
        """Get list of changed files for a target language since specified commit
        
        Args:
            language: The target language to check (e.g., 'python').
            since_commit: The commit to compare since.

        Returns:
            A list of changed file paths for the target language.
        """
        if language not in self.mappings['target_languages']:
            return []
        
        lang_config = self.mappings['target_languages'][language]
        base_path = lang_config.get('base_path', '')
        
        try:
            # Use same logic as Java changes for PR base comparison
            if since_commit == "HEAD~1":
                # subprocess.run without check=True will not raise CalledProcessError;
                # we simply inspect the return code and fallback silently if it fails.
                merge_base_result = subprocess.run([
                    'git', 'merge-base', 'HEAD', 'origin/main'
                ], capture_output=True, text=True, cwd=self.root_dir)
                if merge_base_result.returncode == 0 and merge_base_result.stdout.strip():
                    since_commit = merge_base_result.stdout.strip()
            
            all_changes = []
            result = subprocess.run([
                'git', 'diff', '--name-only', f'{since_commit}', 'HEAD', '--', f'{base_path}/'
            ], capture_output=True, text=True, cwd=self.root_dir)

            if result.returncode == 0:
                all_changes.extend([line.strip() for line in result.stdout.splitlines() if line.strip()])
            
            # Also check CLI base path if it exists
            cli_base_path = lang_config.get('cli_base_path', '')
            if cli_base_path:
                result_cli = subprocess.run([
                    'git', 'diff', '--name-only', f'{since_commit}', 'HEAD', '--', f'{cli_base_path}/'
                ], capture_output=True, text=True, cwd=self.root_dir)
                if result_cli.returncode == 0:
                    all_changes.extend([line.strip() for line in result_cli.stdout.splitlines() if line.strip()])
            
            return all_changes
            return []
        except subprocess.CalledProcessError:
            return []

    def check_target_file_exists(self, target_file):
        """Check if the corresponding target language file exists
        
        Args:
            target_file: The path to the target language file.
            
        Returns:
            True if the file exists, False otherwise.
        """
        target_path = self.root_dir / target_file
        return target_path.exists()

    def generate_sync_report(self, output_format="console", since_commit=DEFAULT_SINCE_COMMIT, check_both_modified=False, target_languages=None, compact=False):
        """Generate a report of files that need syncing
        
        Args:
            output_format: The format for the output report.
            since_commit: The commit to compare since.
            check_both_modified: If True, simply checks that both files were modified in the PR.
                If False, checks that target was modified after Java (timestamp-based).
            target_languages: List of specific languages to check, or None for all enabled languages.
            compact: If True, only show failures and summary (for cleaner PR comments).
        
        Returns:
            str: A formatted report string (even for console output).
        """
        changed_files = self.get_java_changes(since_commit)

        if not changed_files:
            if output_format == "github-checklist":
                return "✅ All Java changes appear to be in sync!"
            else:
                print(NO_CHANGES_MESSAGE)
                return NO_CHANGES_MESSAGE

        # Determine which languages to check
        languages_to_check = target_languages if target_languages else list(self.language_handlers.keys())
        
        # Build mapping list for all languages
        all_language_mappings = {}
        for lang in languages_to_check:
            if lang not in self.language_handlers:
                print(f"Warning: Language '{lang}' not enabled or not found")
                continue
            
            handler = self.language_handlers[lang]
            lang_config = self.mappings['target_languages'][lang]
            lang_changes = self.get_target_language_changes(lang, since_commit)
            
            mappings = []
            for java_file in changed_files:
                mapping = self.get_mapping_for_file(java_file, lang, handler, lang_config)
                if mapping:
                    target_files = mapping.get('target_files', [])
                    if isinstance(target_files, str):
                        target_files = [target_files]
                    
                    mappings.append({
                        'java_file': java_file,
                        'target_files': target_files
                    })
            
            all_language_mappings[lang] = {
                'mappings': mappings,
                'changes': lang_changes
            }

        return self.format_output(all_language_mappings, output_format, since_commit, check_both_modified, compact)

    def format_output(self, all_language_mappings, output_format="console", since_commit=DEFAULT_SINCE_COMMIT, check_both_modified=False, compact=False):
        """Format the output based on the specified format
        
        Args:
            all_language_mappings: Dictionary with language as key and mappings/changes as values.
            output_format: The format for the output report.
            since_commit: The commit to compare since.
            check_both_modified: If True, simply checks that both files were modified in the PR.
                If False, checks that target was modified after Java (timestamp-based).
            compact: If True, only show failures and summary (for cleaner PR comments).
            
        Returns:
            str: The formatted output string (console/json/github-checklist).
        """
        if output_format == "github-checklist":
            return self.format_github_checklist(all_language_mappings, since_commit, check_both_modified, compact)
        elif output_format == "json":
            # Update JSON format to also use timestamp-based logic
            result = {}
            for lang, data in all_language_mappings.items():
                mappings = data['mappings']
                total_items = 0
                completed_items = 0
                for mapping in mappings:
                    java_file = mapping['java_file']
                    for target_file in mapping['target_files']:
                        total_items += 1
                        if self.is_target_file_up_to_date(java_file, target_file, since_commit, check_both_modified):
                            completed_items += 1
                
                result[lang] = {
                    "mappings": mappings,
                    "changes": data['changes'],
                    "total_items": total_items,
                    "completed_items": completed_items
                }
            
            return json.dumps(result, indent=2)
        else:
            # Enhanced console format with multi-language support
            output = ""
            grand_total = 0
            grand_completed = 0
            
            for lang, data in all_language_mappings.items():
                mappings = data['mappings']
                
                output += f"\n{'='*60}\n"
                output += f"  {lang.upper()} Sync Status\n"
                output += f"{'='*60}\n"
                
                total_items = 0
                completed_items = 0
                
                for mapping in mappings:
                    java_file = mapping['java_file']
                    target_files = mapping['target_files']
                    
                    output += f"\n📁 {java_file}:\n"
                    for target_file in target_files:
                        total_items += 1
                        exists = "✅" if self.check_target_file_exists(target_file) else "❌"
                        is_up_to_date = self.is_target_file_up_to_date(java_file, target_file, since_commit, check_both_modified)
                        
                        if is_up_to_date:
                            status_icon = "🔄"
                            completed_items += 1
                        else:
                            status_icon = "⏳"
                        
                        output += f"   {exists} {status_icon} {target_file}\n"
                    output += "-" * 40 + "\n"
                
                # Language summary
                output += f"\n{lang.upper()} SUMMARY:\n"
                output += f"Total sync items: {total_items}\n"
                output += f"Recently updated: {completed_items}\n"
                output += f"Still pending: {total_items - completed_items}\n"
                
                grand_total += total_items
                grand_completed += completed_items
            
            # Overall summary
            if len(all_language_mappings) > 1:
                output += f"\n{'='*60}\n"
                output += "OVERALL PROGRESS:\n"
                output += f"Total across all languages: {grand_total}\n"
                output += f"Completed: {grand_completed}\n"
                output += f"Pending: {grand_total - grand_completed}\n"
            
            # Legend
            check_mode = "both files modified" if check_both_modified else "target modified after Java"
            output += "\nLEGEND:\n"
            output += "  ✅ = File exists, ❌ = File missing\n"
            output += f"  🔄 = Synced ({check_mode}), ⏳ = Out-of-date (needs update)\n"
            
            print(output)
            
            # Save enhanced report
            for lang, data in all_language_mappings.items():
                self.save_enhanced_report(lang, data['mappings'], data['changes'])
            return output

    def format_github_checklist(self, all_language_mappings, since_commit=DEFAULT_SINCE_COMMIT, check_both_modified=False, compact=False):
        """Format as GitHub checklist with completion status for multiple languages
        
        Args:
            all_language_mappings: Dictionary with language as key and mappings/changes as values.
            since_commit: The commit to compare since.
            check_both_modified: If True, simply checks that both files were modified in the PR.
                If False, checks that target was modified after Java (timestamp-based).
            compact: If True, only show failures and summary (for cleaner PR comments).
            
        Returns:
            A formatted GitHub checklist.
        """
        if not all_language_mappings:
            return "✅ All Java changes appear to be in sync!"
        
        grand_total = 0
        grand_completed = 0
        output = "## Java Multi-Language Sync Status\n\n"
        failed_items = []  # Collect failed items for compact mode
        
        for lang, data in all_language_mappings.items():
            mappings = data['mappings']
            
            if not mappings:
                continue
            
            total_items = 0
            completed_items = 0
            lang_failed_items = []
            
            for mapping in mappings:
                java_file = mapping['java_file']
                target_files = mapping['target_files']
                
                for target_file in target_files:
                    total_items += 1
                    exists = self.check_target_file_exists(target_file)
                    is_up_to_date = self.is_target_file_up_to_date(java_file, target_file, since_commit, check_both_modified)
                    
                    if is_up_to_date:
                        completed_items += 1
                    else:
                        status = "⏳ NEEDS SYNC" if exists else "❌ MISSING"
                        lang_failed_items.append({
                            'java_file': java_file,
                            'target_file': target_file,
                            'status': status
                        })
            
            grand_total += total_items
            grand_completed += completed_items
            
            if compact:
                # In compact mode, only add failed items section if there are failures
                if lang_failed_items:
                    failed_items.extend(lang_failed_items)
            else:
                # Full output mode - show all files
                output += f"### 🔄 {lang.upper()} ({len(mappings)} Java files)\n\n"
                
                for mapping in mappings:
                    java_file = mapping['java_file']
                    target_files = mapping['target_files']
                    
                    output += f"#### 📁 `{java_file}`\n"
                    for target_file in target_files:
                        exists = self.check_target_file_exists(target_file)
                        is_up_to_date = self.is_target_file_up_to_date(java_file, target_file, since_commit, check_both_modified)
                        
                        if is_up_to_date:
                            checkbox = "- [x]"
                            status = "✅ SYNCED"
                        elif exists:
                            checkbox = "- [ ]"
                            status = "⏳ NEEDS SYNC"
                        else:
                            checkbox = "- [ ]"
                            status = "❌ MISSING"
                        
                        output += f"{checkbox} **{status}**: `{target_file}`\n"
                    output += "\n"
                
                # Language-specific progress
                output += f"**{lang.upper()} Progress**: {completed_items}/{total_items} completed\n\n"
                output += "---\n\n"
        
        # Build compact output
        if compact:
            if failed_items:
                output += f"**{len(failed_items)} items need attention:**\n\n"
                for item in failed_items:
                    output += f"- [ ] **{item['status']}**: `{item['target_file']}`\n"
                    output += f"  - Source: `{item['java_file']}`\n"
                output += "\n"
            else:
                output += "All files are in sync! ✅\n\n"
        
        # Overall summary (always shown)
        output = output.replace(
            "## Java Multi-Language Sync Status\n\n",
            f"## Java Multi-Language Sync Status ({grand_completed}/{grand_total} completed)\n\n"
        )
        
        if grand_total > 0:
            percentage = round((grand_completed / grand_total) * 100, 1)
            output += f"\n### 📊 Overall Progress: {grand_completed}/{grand_total} ({percentage}%)\n"
        
        return output

    def save_enhanced_report(self, language, mappings, target_changes):
        """Save enhanced report with completion tracking for a specific language
        
        Args:
            language: The target language name.
            mappings: The mapping information between Java and target language files.
            target_changes: The list of changed target language files.
            
        Returns:
            None
        """
        total_items = 0
        completed_items = 0
        details = []
        
        for mapping in mappings:
            java_file = mapping['java_file']
            for target_file in mapping['target_files']:
                total_items += 1
                exists = self.check_target_file_exists(target_file)
                recently_modified = target_file in target_changes
                
                if recently_modified:
                    completed_items += 1
                
                details.append({
                    "java_file": java_file,
                    "target_file": target_file,
                    "exists": exists,
                    "recently_modified": recently_modified,
                    "status": "completed" if recently_modified else "pending"
                })
        
        report_data = {
            "language": language,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_java_files": len(mappings),
                "total_sync_items": total_items,
                "completed_items": completed_items,
                "completion_percentage": (
                    round((completed_items / total_items) * 100, 1)
                    if total_items > 0 else 100
                )
            },
            "mappings": mappings,
            "target_changes": target_changes,
            "details": details
        }
        
        report_file = self.root_dir / "tools" / f"sync-report-{language}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n[{language}] Detailed report saved to: {report_file}")

    def get_mapping_for_file(self, java_file, language, handler, lang_config):
        """Get the mapping configuration for a specific Java file for a target language
        
        Args:
            java_file: The Java file path to get the mapping for.
            language: The target language name (e.g., 'python').
            handler: The LanguageHandler instance for the target language.
            lang_config: The language configuration from mappings.
            
        Returns:
            A mapping configuration for the Java file, or None if not found.
        """
        source_base = self.mappings.get("source_base_path", "")
        cli_source_base = self.mappings.get("cli_source_base_path", "")
        
        # Determine if this is a CLI file
        is_cli_file = cli_source_base and java_file.startswith("lib/java/opentoken-cli/")
        
        if is_cli_file:
            rel_path = java_file[len(cli_source_base):] if java_file.startswith(cli_source_base) else java_file
        else:
            rel_path = java_file[len(source_base):] if java_file.startswith(source_base) else java_file

        # 1. Source-centric critical files (check both core and CLI)
        critical_list = self.mappings.get("critical_cli_files" if is_cli_file else "critical_java_files", [])
        if critical_list:
            overrides = lang_config.get("overrides", {}).get("critical_files", {})
            for cf in critical_list:
                cf_path = cf.get("path")
                if cf_path == rel_path or cf_path == java_file:
                    # Determine target file (override or handler-derived)
                    if cf_path in overrides:
                        target_file = overrides[cf_path]
                    else:
                        target_file = handler.convert_java_to_target_path(java_file)
                    return {
                        "target_files": [target_file],
                        "sync_priority": cf.get("priority", "medium"),
                        "description": cf.get("description", f"Critical file {rel_path}"),
                        "auto_sync": False,
                        "manual_review": cf.get("manual_review", False)
                    }

        # 2. Source-centric directory roots (check both core and CLI)
        dir_roots = self.mappings.get("cli_directory_roots" if is_cli_file else "directory_roots", [])
        if dir_roots:
            for root in dir_roots:
                root_path = root.get("path")
                # Support relative root (under source_base) or absolute java path
                if root_path.startswith("lib/java/"):
                    full_root = root_path
                else:
                    full_root = (cli_source_base if is_cli_file else source_base) + root_path
                if java_file.startswith(full_root):
                    target_file = handler.convert_java_to_target_path(java_file)
                    return {
                        "target_files": [target_file],
                        "sync_priority": root.get("priority", "medium"),
                        "description": f"Directory root mapping for {rel_path}",
                        "auto_sync": root.get("auto_sync", True)
                    }

        # 3. Legacy per-language critical files (check both core and CLI)
        critical_files_key = "critical_cli_files" if is_cli_file else "critical_files"
        if critical_files_key in lang_config:
            for exact_file, mapping in lang_config[critical_files_key].items():
                if java_file == exact_file:
                    return {
                        "target_files": [mapping["target_file"]],
                        "sync_priority": mapping.get("sync_priority", "medium"),
                        "description": mapping.get("description", ""),
                        "auto_sync": mapping.get("auto_sync", False)
                    }

        # 4. Legacy per-language directory mappings (check both core and CLI)
        dir_mappings_key = "cli_directory_mappings" if is_cli_file else "directory_mappings"
        if dir_mappings_key in lang_config:
            for dir_pattern, mapping in lang_config[dir_mappings_key].items():
                if java_file.startswith(dir_pattern):
                    target_file = handler.convert_java_to_target_path(java_file)
                    return {
                        "target_files": [target_file],
                        "sync_priority": mapping.get("sync_priority", "medium"),
                        "description": f"Directory mapping for {java_file}",
                        "auto_sync": mapping.get("auto_sync", True)
                    }

        # 5. Fallback auto-generate
        if self.mappings.get("auto_generate_unmapped", True):
            target_file = handler.convert_java_to_target_path(java_file)
            return {
                "target_files": [target_file],
                "sync_priority": "low",
                "description": f"Auto-generated mapping for {java_file}",
                "auto_sync": True
            }
        return None



def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Java multi-language synchronization checker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --format console --since origin/main
  %(prog)s --format github-checklist --check-both-modified --since origin/main
  %(prog)s --health-check
  %(prog)s --validate-only
  %(prog)s --languages python  # Check specific language only
        """
    )
    
    parser.add_argument('--format', choices=['console', 'github-checklist', 'json'],
                        default='console', help='Output format')
    parser.add_argument('--since', default='HEAD~1',
                        help='Compare changes since this commit/branch')
    parser.add_argument('--check-both-modified', action='store_true',
                        help='Check that both Java and target files were modified in the PR (simpler check)')
    parser.add_argument('--compact', action='store_true',
                        help='Show only failures and summary (for cleaner PR comments)')
    parser.add_argument('--languages', 
                        help='Comma-separated list of target languages to check (default: all enabled)')
    parser.add_argument('--health-check', action='store_true',
                        help='Perform comprehensive health check')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate configuration, don\'t check changes')
    
    args = parser.parse_args()
    
    syncer = JavaLanguageSyncer()
    
    if args.health_check:
        success = syncer.health_check()
        return 0 if success else 1
    
    if args.validate_only:
        issues = syncer.validate_configuration()
        if issues:
            print("❌ Configuration validation failed:")
            for issue in issues:
                print(f"   - {issue}")
            return 1
        else:
            print("✅ Configuration validation passed")
            return 0
    
    # Parse target languages if specified
    target_languages = None
    if args.languages:
        target_languages = [lang.strip() for lang in args.languages.split(',')]
    
    # Default: generate sync report
    result = syncer.generate_sync_report(
        output_format=args.format, 
        since_commit=args.since,
        check_both_modified=args.check_both_modified,
        target_languages=target_languages,
        compact=args.compact
    )
    
    if args.format == "github-checklist":
        print(result)
        # Check if sync is complete - fail if not
        if "0 completed)" not in result and "completed)" in result:
            # Extract completion status using already imported 're'
            match = re.search(r'\((\d+)/(\d+) completed\)', result)
            if match:
                completed = int(match.group(1))
                total = int(match.group(2))
                if completed < total:
                    print(f"\n❌ Sync incomplete: {completed}/{total} items completed")
                    return 1
    
    return 0


if __name__ == "__main__":
    main()
