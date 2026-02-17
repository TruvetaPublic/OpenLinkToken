#!/usr/bin/env python3
"""
Multi-Language Sync Tool
Detects changes in any language (Java, Python, Node.js) and creates corresponding sync tasks
for the other languages.
"""

import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


class MultiLanguageSyncer:
    """Syncer that handles Java, Python, and Node.js implementations"""
    
    # Language configuration
    LANGUAGES = {
        'java': {
            'path': 'lib/java/opentoken/src/main/java/com/truveta/opentoken/',
            'extension': '.java',
            'naming': 'PascalCase'
        },
        'python': {
            'path': 'lib/python/opentoken/src/main/opentoken/',
            'extension': '.py',
            'naming': 'snake_case'
        },
        'nodejs': {
            'path': 'lib/nodejs/opentoken/src/',
            'extension': '.ts',
            'naming': 'PascalCase'
        }
    }
    
    FALLBACK_MAPPINGS = {
        "critical_files": {},
        "directory_mappings": {},
        "ignore_patterns": [],
        "auto_generate_unmapped": True
    }

    def __init__(self, mapping_file="tools/multi-language-mapping.json"):
        self.root_dir = Path(__file__).parent.parent
        self.mapping_file = self.root_dir / mapping_file
        
        # Try to load multi-language mapping, fallback to java-python if not found
        if not self.mapping_file.exists():
            print(f"Note: Multi-language mapping not found, using java-python-mapping.json")
            self.mapping_file = self.root_dir / "tools" / "java-python-mapping.json"
        
        self.load_mappings()

    def load_mappings(self):
        """Load the multi-language file mappings"""
        try:
            with open(self.mapping_file, 'r') as f:
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
        lang_path = lang_config['path']
        
        try:
            result = subprocess.run([
                'git', 'diff', '--name-only', f'{since_commit}', 'HEAD', '--', lang_path
            ], capture_output=True, text=True, cwd=self.root_dir)

            if result.returncode == 0:
                all_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                return self._filter_ignored_files(all_files)
            return []
        except subprocess.CalledProcessError:
            return []

    def _filter_ignored_files(self, files):
        """Filter out files that match ignore patterns"""
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

    def get_file_last_modified_commit(self, file_path, since_commit="HEAD~1"):
        """Get the most recent commit that modified a specific file"""
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

    def is_file_up_to_date(self, source_file, target_file, since_commit="HEAD~1"):
        """Check if target file is up-to-date relative to source file changes"""
        source_last_modified = self.get_file_last_modified_commit(source_file, since_commit)
        target_last_modified = self.get_file_last_modified_commit(target_file, since_commit)
        
        # If source file wasn't modified at all in this PR, no sync needed
        if not source_last_modified:
            return True
            
        # If target file wasn't modified at all in this PR, it's out of date
        if not target_last_modified:
            return False
            
        # Target is up-to-date if it was modified after the source file
        return target_last_modified['timestamp'] >= source_last_modified['timestamp']

    def check_file_exists(self, file_path):
        """Check if a file exists"""
        return (self.root_dir / file_path).exists()

    def convert_filename(self, filename, from_naming, to_naming):
        """Convert filename between naming conventions"""
        # Remove extension
        base_name = filename
        for lang_config in self.LANGUAGES.values():
            if filename.endswith(lang_config['extension']):
                base_name = filename[:-len(lang_config['extension'])]
                break
        
        # Convert naming convention
        if from_naming == 'PascalCase' and to_naming == 'snake_case':
            # Convert PascalCase to snake_case
            import re
            base_name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', base_name)
            base_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', base_name).lower()
        elif from_naming == 'snake_case' and to_naming == 'PascalCase':
            # Convert snake_case to PascalCase
            base_name = ''.join(word.capitalize() for word in base_name.split('_'))
        
        return base_name

    def get_corresponding_files(self, source_file, source_lang):
        """Get corresponding files in other languages"""
        corresponding = {}
        
        # Extract relative path within language directory
        lang_config = self.LANGUAGES[source_lang]
        source_path = source_file.replace(lang_config['path'], '')
        
        # Try to map to other languages
        for target_lang, target_config in self.LANGUAGES.items():
            if target_lang == source_lang:
                continue
            
            # Convert directory structure (usually similar)
            target_path = source_path
            
            # Convert filename based on naming convention
            path_parts = target_path.split('/')
            if path_parts:
                filename = path_parts[-1]
                converted = self.convert_filename(
                    filename,
                    lang_config['naming'],
                    target_config['naming']
                )
                path_parts[-1] = converted + target_config['extension']
                target_path = '/'.join(path_parts)
            
            target_file = target_config['path'] + target_path
            corresponding[target_lang] = target_file
        
        return corresponding

    def generate_sync_report(self, output_format="console", since_commit="HEAD~1"):
        """Generate a report of files that need syncing across all languages"""
        
        # Get changes for each language
        all_changes = {}
        for lang in self.LANGUAGES:
            all_changes[lang] = self.get_changes_for_language(lang, since_commit)
        
        # Check if any changes were made
        total_changes = sum(len(changes) for changes in all_changes.values())
        if total_changes == 0:
            if output_format == "github-checklist":
                return "✅ All changes appear to be in sync across Java, Python, and Node.js!"
            else:
                print("No changes detected in any language.")
                return
        
        # Build sync requirements
        sync_requirements = []
        
        for source_lang, changed_files in all_changes.items():
            for source_file in changed_files:
                corresponding = self.get_corresponding_files(source_file, source_lang)
                sync_requirements.append({
                    'source_lang': source_lang,
                    'source_file': source_file,
                    'corresponding': corresponding
                })
        
        return self.format_output(sync_requirements, all_changes, output_format, since_commit)

    def format_output(self, sync_requirements, all_changes, output_format="console", since_commit="HEAD~1"):
        """Format the output based on the specified format"""
        if output_format == "github-checklist":
            return self.format_github_checklist(sync_requirements, all_changes, since_commit)
        elif output_format == "json":
            return json.dumps({
                "sync_requirements": sync_requirements,
                "all_changes": all_changes
            }, indent=2)
        else:
            return self.format_console(sync_requirements, all_changes, since_commit)

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
            lang = req['source_lang']
            if lang not in by_lang:
                by_lang[lang] = []
            by_lang[lang].append(req)
        
        for source_lang in sorted(by_lang.keys()):
            output += f"### 🔹 From {source_lang.upper()}\n\n"
            
            for req in by_lang[source_lang]:
                source_file = req['source_file']
                output += f"#### 📁 `{source_file}`\n"
                
                for target_lang, target_file in sorted(req['corresponding'].items()):
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
            f"## Multi-Language Sync Required ({completed_items}/{total_items} completed)\n\n"
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
            for target_lang, target_file in req['corresponding'].items():
                exists = "✓" if self.check_file_exists(target_file) else "✗"
                output += f"  → {target_lang}: {exists} {target_file}\n"
            output += "\n"
        
        return output


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Multi-language sync checker')
    parser.add_argument('--format', choices=['console', 'json', 'github-checklist'],
                       default='console', help='Output format')
    parser.add_argument('--since', default='HEAD~1',
                       help='Compare since this commit')
    parser.add_argument('--health-check', action='store_true',
                       help='Run health check')
    
    args = parser.parse_args()
    
    syncer = MultiLanguageSyncer()
    
    if args.health_check:
        print("Health check not yet implemented for multi-language syncer")
        return
    
    report = syncer.generate_sync_report(args.format, args.since)
    
    if report:
        print(report)


if __name__ == "__main__":
    main()
