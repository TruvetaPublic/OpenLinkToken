#!/bin/bash

# Java Multi-Language Synchronization Checker
# Wrapper script for java_language_syncer.py with completion tracking

# Default values
OUTPUT_FORMAT="console"
SINCE_COMMIT="HEAD~1"
CREATE_ISSUE=false
VERBOSE=false
QUIET=false
TARGET_LANGUAGES=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() { [[ $QUIET != true ]] && echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { [[ $QUIET != true ]] && echo -e "${GREEN}✓${NC} $1"; }
log_warning() { [[ $QUIET != true ]] && echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1" >&2; }

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Java Multi-Language Synchronization Checker with Completion Tracking
Detects Java file changes and identifies corresponding target language files that need updates.
Tracks completion status across multiple commits in PRs.

OPTIONS:
    -f, --format FORMAT     Output format: console, github-checklist, json (default: console)
    -s, --since COMMIT      Compare changes since this commit/branch (default: HEAD~1)
                           Use 'origin/main' for full PR comparison
    -l, --languages LANGS   Comma-separated list of languages to check (e.g., python)
                           Default: all enabled languages
    -i, --issue            Create GitHub issue for sync tasks (requires gh CLI)
    -v, --verbose          Enable verbose output
    -q, --quiet            Suppress info messages
    -h, --help             Show this help message

EXAMPLES:
    # Basic usage - check for changes since last commit
    $0

    # Check all changes in current PR against main branch
    $0 --since origin/main --format github-checklist

    # Check only Python sync status
    $0 --languages python --since origin/main

    # Generate JSON report for automation
    $0 --format json --since origin/main

    # Create GitHub issue with completion tracking
    $0 --issue --format github-checklist --since origin/main

    # Quiet mode for scripting
    $0 --quiet --format json

COMPLETION TRACKING FEATURES:
    The enhanced tool now tracks which target language files have been recently modified,
    helping you see progress on sync items across multiple commits in a PR.
    
    Status indicators:
    ✓ = File exists, ✗ = File missing
    🔄 = Recently modified, ⏳ = Needs update
    
    Progress tracking:
    - Shows completion percentage (e.g., "3/5 completed")
    - Identifies which items are done vs pending
    - Works across multiple commits in same PR

WORKFLOW FOR MULTI-COMMIT PRs:
    1. Make Java changes → tool shows sync checklist
    2. Make some target language updates → tool shows progress
    3. Continue until all items are 🔄 (completed)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--format)
            OUTPUT_FORMAT="$2"
            if [[ ! "$OUTPUT_FORMAT" =~ ^(console|github-checklist|json)$ ]]; then
                log_error "Invalid format: $OUTPUT_FORMAT. Must be: console, github-checklist, json"
                exit 1
            fi
            shift 2
            ;;
        -s|--since)
            SINCE_COMMIT="$2"
            shift 2
            ;;
        -l|--languages)
            TARGET_LANGUAGES="$2"
            shift 2
            ;;
        -i|--issue)
            CREATE_ISSUE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            log_error "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Determine script directory and root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to root directory
cd "$ROOT_DIR"

# Environment validation
if [[ $VERBOSE == true ]]; then
    log_info "Script directory: $SCRIPT_DIR"
    log_info "Root directory: $ROOT_DIR"
    log_info "Output format: $OUTPUT_FORMAT"
    log_info "Since commit: $SINCE_COMMIT"
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not found"
    exit 1
fi

# Check if the syncer script exists
if [[ ! -f "tools/java_language_syncer.py" ]]; then
    log_error "Syncer script not found: tools/java_language_syncer.py"
    exit 1
fi

# Check if the mapping file exists
if [[ ! -f "tools/java-language-mappings.json" ]]; then
    log_error "Mapping file not found: tools/java-language-mappings.json"
    exit 1
fi

# Show progress indicator unless quiet
if [[ $QUIET != true ]]; then
    if [[ $SINCE_COMMIT == "HEAD~1" ]]; then
        echo "Checking for sync requirements since last commit..."
    elif [[ $SINCE_COMMIT == *"main"* ]]; then
        echo "Checking for sync requirements in current PR..."
    else
        echo "Checking for sync requirements since: $SINCE_COMMIT"
    fi
    echo ""
fi

# Run the enhanced sync checker
SYNC_RESULT=""
LANG_ARGS=""
if [[ -n "$TARGET_LANGUAGES" ]]; then
    LANG_ARGS="--languages $TARGET_LANGUAGES"
fi

if [[ $OUTPUT_FORMAT == "github-checklist" ]]; then
    # Capture output for potential issue creation
    SYNC_RESULT=$(python3 tools/java_language_syncer.py --format "$OUTPUT_FORMAT" --since "$SINCE_COMMIT" $LANG_ARGS 2>&1)
    SYNC_EXIT_CODE=$?
    
    # Always show the result for checklist format
    echo "$SYNC_RESULT"
else
    # Run normally
    if [[ $VERBOSE == true ]]; then
        python3 tools/java_language_syncer.py --format "$OUTPUT_FORMAT" --since "$SINCE_COMMIT" $LANG_ARGS
    else
        python3 tools/java_language_syncer.py --format "$OUTPUT_FORMAT" --since "$SINCE_COMMIT" $LANG_ARGS 2>/dev/null
    fi
    SYNC_EXIT_CODE=$?
fi

# Handle GitHub issue creation
if [[ $CREATE_ISSUE == true ]]; then
    if ! command -v gh &> /dev/null; then
        log_warning "GitHub CLI (gh) not found - cannot create issue automatically"
        log_info "Install gh CLI: https://cli.github.com/"
    else
        # Check if there are recent sync reports indicating work needed
        RECENT_REPORTS=$(find tools/ -name "sync-report-*.json" -mtime -1 2>/dev/null | head -1)
        if [[ -n "$RECENT_REPORTS" ]]; then
            log_info "Creating GitHub issue for sync tracking..."
            
            # Create issue with the checklist format
            if [[ -n "$SYNC_RESULT" ]]; then
                # Use the already captured result
                gh issue create \
                    --title "Java Multi-Language Sync Required (Auto-generated)" \
                    --body "$SYNC_RESULT" \
                    --label "language-sync-needed,auto-generated" 2>/dev/null && \
                log_success "GitHub issue created successfully!" || \
                log_warning "Failed to create GitHub issue"
            else
                # Generate checklist format for issue
                ISSUE_CONTENT=$(python3 tools/java_language_syncer.py --format github-checklist --since "$SINCE_COMMIT" $LANG_ARGS 2>/dev/null)
                gh issue create \
                    --title "Java Multi-Language Sync Required (Auto-generated)" \
                    --body "$ISSUE_CONTENT" \
                    --label "language-sync-needed,auto-generated" 2>/dev/null && \
                log_success "GitHub issue created successfully!" || \
                log_warning "Failed to create GitHub issue"
            fi
        else
            log_success "No sync requirements found - no issue needed"
        fi
    fi
fi

# Final status
if [[ $SYNC_EXIT_CODE -eq 0 ]]; then
    [[ $QUIET != true ]] && log_success "Sync check complete!"
else
    log_error "Sync check failed with exit code: $SYNC_EXIT_CODE"
    exit $SYNC_EXIT_CODE
fi
