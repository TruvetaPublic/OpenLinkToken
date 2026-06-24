#!/bin/bash

# run-openlinktoken.sh
# Convenience script to run Open Link Token via Docker.
# Automatically builds the Docker image when needed, mounts all required file
# paths into the container, and forwards every option to the olt CLI.

set -e

DOCKER_IMAGE="openlinktoken:latest"
SKIP_BUILD=false
VERBOSE=false

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1" >&2; }

show_usage() {
    cat << EOF
Usage: $0 SUBCOMMAND [OPTIONS]

Docker convenience wrapper for Open Link Token. Builds the Docker image when
needed, mounts file paths into the container, and forwards all options to olt.

SUBCOMMANDS:
    package             Tokenize and encrypt in one step
    tokenize            Generate hashed tokens (--mode hash-only for SHA-256 only)
    encrypt             Encrypt previously tokenized output
    decrypt             Decrypt encrypted tokens
    initiate-exchange   Create an exchange config from a partner's public key
    generate-key-pair   Generate an ECDH key pair (written to ~/.openlinktoken/)

OPTIONS (forwarded to the container — see olt help <subcommand> for full details):
    -i, --input PATH                Input file (package, tokenize, encrypt, decrypt)
    -o, --output PATH               Output file
    --exchange-config PATH          Exchange config JSON (package, tokenize, encrypt, decrypt)
    --private-key PATH              Private key PEM file
    --private-key-env VAR           Read private key from this environment variable
    --public-key PATH               Partner public key PEM (initiate-exchange)
    --public-key-env VAR            Read partner public key from this environment variable
    --public-key-stdin              Read partner public key from stdin
    --sender-private-key PATH       Sender private key PEM (initiate-exchange)
    --sender-private-key-env VAR    Read sender private key from this environment variable
    --hashingsecret SECRET          Hashing secret (initiate-exchange)
    --hashingsecret-env VAR         Read hashing secret from this environment variable
    --hashingsecret-stdin           Read hashing secret from stdin
    --mode MODE                     Tokenize mode: olt|hash-only|demo
    --ring-id ID                    Ring identifier (package, encrypt)
    --hash-record-ids               Hash record IDs before writing output
    -n, --name NAME                 Key/config base name (generate-key-pair, initiate-exchange)
    -c, --curve CURVE               EC curve: P-256, P-384, P-521 (default: P-256)
    --force                         Overwrite existing key or config files
    -q, --no-progress               Suppress progress indicator

SCRIPT OPTIONS:
    --image NAME        Docker image name (default: openlinktoken:latest)
    --skip-build        Skip Docker image build (use existing image)
    -v, --verbose       Verbose output
    --help              Show this message

NOTES:
    - Run from the Open Link Token repository root directory
    - ~/.openlinktoken/ is always mounted so key files persist across runs
    - File paths are automatically resolved and mounted into the container
    - Environment variables named by --*-env flags are forwarded to the container

EXAMPLES:
    # Generate a key pair
    $0 generate-key-pair --name recipient

    # Create an exchange config from the recipient's public key
    $0 initiate-exchange --public-key "\$HOME/.openlinktoken/recipient.public.pem"

    # Tokenize and encrypt
    $0 package -i ./data/input.csv -o ./data/output.zip \\
        --exchange-config ./openlinktoken.exchange.json \\
        --private-key "\$HOME/.openlinktoken/mykey.private.pem"

    # Hash-only tokenize (no exchange config needed)
    $0 tokenize --mode hash-only -i ./data/input.csv -o ./data/hashed.csv

    # Decrypt
    $0 decrypt -i ./data/output.zip -o ./data/decrypted.csv \\
        --exchange-config ./openlinktoken.exchange.json \\
        --private-key "\$HOME/.openlinktoken/mykey.private.pem"

    # Use an existing image (skip rebuild)
    $0 package --skip-build -i ./input.csv -o ./output.zip \\
        --exchange-config ./openlinktoken.exchange.json

EOF
}

# ─── Subcommand ───────────────────────────────────────────────────────────────

VALID_SUBCOMMANDS=(package tokenize encrypt decrypt initiate-exchange generate-key-pair)
SUBCOMMAND=""

if [[ $# -gt 0 ]]; then
    for sc in "${VALID_SUBCOMMANDS[@]}"; do
        if [[ "$1" == "$sc" ]]; then
            SUBCOMMAND="$1"
            shift
            break
        fi
    done
fi

if [[ -z "$SUBCOMMAND" ]]; then
    if [[ "${1:-}" == "--help" ]]; then show_usage; exit 0; fi
    log_error "A subcommand is required."
    echo ""
    show_usage
    exit 1
fi

# ─── Separate script options from passthrough args ────────────────────────────

PASSTHROUGH_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)   SKIP_BUILD=true; shift ;;
        --image)        DOCKER_IMAGE="$2"; shift 2 ;;
        -v|--verbose)   VERBOSE=true; shift ;;
        --help)         show_usage; exit 0 ;;
        *)              PASSTHROUGH_ARGS+=("$1"); shift ;;
    esac
done

# ─── Check Docker ─────────────────────────────────────────────────────────────

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH."
    log_error "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# ─── Volume mount planning ────────────────────────────────────────────────────
# Flags whose next argument is a host file path that must be mounted.
FILE_FLAGS=(-i --input -o --output --exchange-config --private-key --public-key --sender-private-key)

# Flags whose next argument is an environment variable name — forward the var.
ENV_VAR_FLAGS=(--private-key-env --hashingsecret-env --public-key-env --sender-private-key-env)

# Flags that indicate stdin will be used — pass -i to docker run.
STDIN_FLAGS=(--hashingsecret-stdin --public-key-stdin)

declare -A DIR_MAP   # host_dir -> container mount point
MOUNT_ARGS=()
ENV_PASS_ARGS=()
MOUNT_COUNTER=0
NEEDS_STDIN=false

_is_file_flag() {
    local arg="$1"
    for f in "${FILE_FLAGS[@]}"; do [[ "$arg" == "$f" ]] && return 0; done
    return 1
}

_is_env_flag() {
    local arg="$1"
    for f in "${ENV_VAR_FLAGS[@]}"; do [[ "$arg" == "$f" ]] && return 0; done
    return 1
}

_is_stdin_flag() {
    local arg="$1"
    for f in "${STDIN_FLAGS[@]}"; do [[ "$arg" == "$f" ]] && return 0; done
    return 1
}

# Always mount ~/.openlinktoken so key files are accessible and persist.
OLT_HOME_ABS="$(realpath "$HOME/.openlinktoken" 2>/dev/null || echo "$HOME/.openlinktoken")"
mkdir -p "$OLT_HOME_ABS"
DIR_MAP["$OLT_HOME_ABS"]="/root/.openlinktoken"
MOUNT_ARGS+=(-v "$OLT_HOME_ABS:/root/.openlinktoken")

_register_dir() {
    local host_dir="$1"
    if [[ -z "${DIR_MAP[$host_dir]+_}" ]]; then
        local container_dir="/data/$MOUNT_COUNTER"
        DIR_MAP["$host_dir"]="$container_dir"
        MOUNT_ARGS+=(-v "${host_dir}:${container_dir}")
        MOUNT_COUNTER=$((MOUNT_COUNTER + 1))
    fi
}

_remap_path() {
    local path="$1"
    local abs
    abs="$(realpath -m "$path" 2>/dev/null || echo "$(pwd)/$path")"
    local dir file
    dir="$(dirname "$abs")"
    file="$(basename "$abs")"
    mkdir -p "$dir"
    _register_dir "$dir"
    echo "${DIR_MAP[$dir]}/$file"
}

# First pass: register all directories and collect env vars.
idx=0
while [[ $idx -lt ${#PASSTHROUGH_ARGS[@]} ]]; do
    arg="${PASSTHROUGH_ARGS[$idx]}"
    if _is_file_flag "$arg"; then
        path="${PASSTHROUGH_ARGS[$((idx+1))]}"
        abs="$(realpath -m "$path" 2>/dev/null || echo "$(pwd)/$path")"
        mkdir -p "$(dirname "$abs")"
        _register_dir "$(dirname "$abs")"
        idx=$((idx+2))
    elif _is_env_flag "$arg"; then
        varname="${PASSTHROUGH_ARGS[$((idx+1))]}"
        if [[ -n "${!varname+_}" ]]; then
            ENV_PASS_ARGS+=(-e "$varname=${!varname}")
        fi
        idx=$((idx+2))
    elif _is_stdin_flag "$arg"; then
        NEEDS_STDIN=true
        idx=$((idx+1))
    else
        idx=$((idx+1))
    fi
done

# Second pass: rewrite file path values to container-internal paths.
REMAPPED_ARGS=()
idx=0
while [[ $idx -lt ${#PASSTHROUGH_ARGS[@]} ]]; do
    arg="${PASSTHROUGH_ARGS[$idx]}"
    if _is_file_flag "$arg"; then
        path="${PASSTHROUGH_ARGS[$((idx+1))]}"
        REMAPPED_ARGS+=("$arg" "$(_remap_path "$path")")
        idx=$((idx+2))
    else
        REMAPPED_ARGS+=("$arg")
        idx=$((idx+1))
    fi
done

# ─── Docker build ─────────────────────────────────────────────────────────────

if [[ $SKIP_BUILD == false ]]; then
    if docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
        [[ $VERBOSE == true ]] && log_info "Using existing image '$DOCKER_IMAGE'"
    else
        log_info "Building Docker image '$DOCKER_IMAGE' (first run may take a few minutes)..."
        if [[ $VERBOSE == true ]]; then
            docker build -t "$DOCKER_IMAGE" . || { log_error "Docker build failed"; exit 1; }
        else
            docker build -t "$DOCKER_IMAGE" . > /dev/null 2>&1 || { log_error "Docker build failed"; exit 1; }
        fi
        log_success "Docker image built"
    fi
else
    log_info "Skipping Docker build"
    docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1 || {
        log_error "Image '$DOCKER_IMAGE' not found. Run without --skip-build first."
        exit 1
    }
fi

# ─── Run ──────────────────────────────────────────────────────────────────────

if [[ $VERBOSE == true ]]; then
    log_info "Subcommand: $SUBCOMMAND"
    log_info "Mounts:     ${MOUNT_ARGS[*]}"
    log_info "Env:        ${ENV_PASS_ARGS[*]}"
    log_info "Args:       ${REMAPPED_ARGS[*]}"
fi

log_info "Running Open Link Token ($SUBCOMMAND)..."

DOCKER_RUN_OPTS=(--rm)
[[ $NEEDS_STDIN == true ]] && DOCKER_RUN_OPTS+=(-i)
DOCKER_RUN_OPTS+=("${MOUNT_ARGS[@]}" "${ENV_PASS_ARGS[@]}")

docker run "${DOCKER_RUN_OPTS[@]}" "$DOCKER_IMAGE" "$SUBCOMMAND" "${REMAPPED_ARGS[@]}"
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    log_success "Completed successfully"
else
    log_error "Open Link Token exited with code $EXIT_CODE"
    exit $EXIT_CODE
fi
