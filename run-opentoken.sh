#!/bin/bash

# run-opentoken.sh
# Convenience script to build and run OpenToken via Docker
# Automatically handles Docker image building and container execution

set -e  # Exit on error

# Default values
INPUT_FILE=""
OUTPUT_FILE=""
FILE_TYPE="csv"
HASHING_SECRET=""
ENCRYPTION_KEY=""
DOCKER_IMAGE="opentoken:latest"
SKIP_BUILD=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1" >&2; }

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Convenience wrapper for building and running OpenToken via Docker.
Automatically builds the Docker image if needed and runs OpenToken with specified parameters.

REQUIRED OPTIONS:
    -i, --input FILE        Input file path (absolute or relative)
    -h, --hash SECRET       Hashing secret key
    -e, --encrypt KEY       Encryption key

OPTIONAL:
    -o, --output FILE       Output file path (defaults to <input>_tokenized.<type>)
    -t, --type TYPE         File type: csv or parquet (default: csv)
    -s, --skip-build        Skip Docker image build (use existing image)
    --image NAME            Docker image name (default: opentoken:latest)
    -v, --verbose           Enable verbose output
    --help                  Show this help message

EXAMPLES:
    # Basic usage with CSV files
    $0 -i /path/to/input.csv -h "MyHashKey" -e "MyEncryptionKey"

    # With parquet files
    $0 -i ./data/input.parquet -t parquet -h "secret" -e "key123"

    # Skip Docker build if image already exists
    $0 -i ./input.csv -h "secret" -e "key" --skip-build

    # Verbose mode for troubleshooting
    $0 -i ./input.csv -h "secret" -e "key" -v

NOTES:
    - This script must be run from the OpenToken repository root directory
    - Input and output files are automatically mounted into the Docker container
    - The script will build the Docker image on first run (may take a few minutes)
    - Use --skip-build to skip rebuilding the image on subsequent runs

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -t|--type)
            FILE_TYPE="$2"
            if [[ ! "$FILE_TYPE" =~ ^(csv|parquet)$ ]]; then
                log_error "Invalid file type: $FILE_TYPE. Must be: csv, parquet"
                exit 1
            fi
            shift 2
            ;;
        -h|--hash)
            HASHING_SECRET="$2"
            shift 2
            ;;
        -e|--encrypt)
            ENCRYPTION_KEY="$2"
            shift 2
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --image)
            DOCKER_IMAGE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --help)
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

# Validate required parameters
if [[ -z "$INPUT_FILE" ]]; then
    log_error "Input file is required (use -i or --input)"
    echo ""
    show_usage
    exit 1
fi

if [[ -z "$HASHING_SECRET" ]]; then
    log_error "Hashing secret is required (use -h or --hash)"
    echo ""
    show_usage
    exit 1
fi

if [[ -z "$ENCRYPTION_KEY" ]]; then
    log_error "Encryption key is required (use -e or --encrypt)"
    echo ""
    show_usage
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    log_error "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Convert to absolute paths
INPUT_FILE=$(realpath "$INPUT_FILE" 2>/dev/null || echo "$INPUT_FILE")
OUTPUT_FILE=$(realpath -m "$OUTPUT_FILE" 2>/dev/null || echo "$OUTPUT_FILE")

# Verify input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    log_error "Input file does not exist: $INPUT_FILE"
    exit 1
fi

if [[ -z "$OUTPUT_FILE" ]]; then
    INPUT_BASENAME=$(basename "$INPUT_FILE")
    INPUT_STEM="${INPUT_BASENAME%.*}"
    OUTPUT_FILE="$(dirname "$INPUT_FILE")/${INPUT_STEM}_tokenized.${FILE_TYPE}"
    log_info "No output file provided; using derived path: $OUTPUT_FILE"
fi

# Get directory paths for volume mounting
INPUT_DIR=$(dirname "$INPUT_FILE")
INPUT_FILENAME=$(basename "$INPUT_FILE")
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
OUTPUT_FILENAME=$(basename "$OUTPUT_FILE")

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

if [[ $VERBOSE == true ]]; then
    log_info "Input file: $INPUT_FILE"
    log_info "Output file: $OUTPUT_FILE"
    log_info "File type: $FILE_TYPE"
    log_info "Docker image: $DOCKER_IMAGE"
fi

# Build Docker image if needed
if [[ $SKIP_BUILD == false ]]; then
    # Check if image already exists
    if docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
        log_success "Docker image '$DOCKER_IMAGE' already exists locally"
        if [[ $VERBOSE == true ]]; then
            log_info "Use --skip-build to suppress this check"
        fi
    else
        log_info "Building Docker image: $DOCKER_IMAGE"
        log_info "This may take a few minutes on first run..."
        
        if [[ $VERBOSE == true ]]; then
            docker build -t "$DOCKER_IMAGE" .
            BUILD_STATUS=$?
        else
            docker build -t "$DOCKER_IMAGE" . > /dev/null 2>&1
            BUILD_STATUS=$?
        fi
        
        if [[ $BUILD_STATUS -eq 0 ]]; then
            log_success "Docker image built successfully"
        else
            log_error "Failed to build Docker image"
            exit 1
        fi
    fi
else
    log_info "Skipping Docker build (using existing image)"
    
    # Check if image exists
    if ! docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
        log_error "Docker image '$DOCKER_IMAGE' not found"
        log_error "Run without --skip-build to build the image first"
        exit 1
    fi
fi

# Run OpenToken via Docker
log_info "Running OpenToken..."

# If input and output are in the same directory, mount once
if [[ "$INPUT_DIR" == "$OUTPUT_DIR" ]]; then
    if [[ $VERBOSE == true ]]; then
        log_info "Mounting directory: $INPUT_DIR"
    fi
    
    docker run --rm \
        -v "$INPUT_DIR:/data" \
        "$DOCKER_IMAGE" \
        -i "/data/$INPUT_FILENAME" \
        -t "$FILE_TYPE" \
        -o "/data/$OUTPUT_FILENAME" \
        -h "$HASHING_SECRET" \
        -e "$ENCRYPTION_KEY"
else
    # Mount input and output directories separately
    if [[ $VERBOSE == true ]]; then
        log_info "Mounting input directory: $INPUT_DIR"
        log_info "Mounting output directory: $OUTPUT_DIR"
    fi
    
    docker run --rm \
        -v "$INPUT_DIR:/data/input" \
        -v "$OUTPUT_DIR:/data/output" \
        "$DOCKER_IMAGE" \
        -i "/data/input/$INPUT_FILENAME" \
        -t "$FILE_TYPE" \
        -o "/data/output/$OUTPUT_FILENAME" \
        -h "$HASHING_SECRET" \
        -e "$ENCRYPTION_KEY"
fi

if [[ $? -eq 0 ]]; then
    log_success "OpenToken completed successfully!"
    log_success "Output file: $OUTPUT_FILE"
else
    log_error "OpenToken execution failed"
    exit 1
fi
