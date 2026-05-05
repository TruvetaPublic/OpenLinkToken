#!/usr/bin/env bash

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI_SOURCE_ROOT="$REPO_ROOT/lib/python/openlinktoken-cli/src/main"
CORE_SOURCE_ROOT="$REPO_ROOT/lib/python/openlinktoken/src/main"

DEFAULT_HASHING_SECRET="LocalHarnessHashingSecret"
HASHING_SECRET_ENV_VAR="OLT_MATRIX_HASHING_SECRET"
RECIPIENT_PUBLIC_KEY_ENV_VAR="OLT_MATRIX_RECIPIENT_PUBLIC_KEY_PEM"
SENDER_PRIVATE_KEY_ENV_VAR="OLT_MATRIX_SENDER_PRIVATE_KEY_PEM"

PAUSE_SECONDS="0.25"
INCLUDE_LIVE_UPDATE="false"
INCLUDE_EXTENSION_INSTALL="false"
AUTO_CONTINUE="false"
DRY_RUN="false"
KEEP_WORKSPACE="false"
WORKSPACE_ROOT=""
STOP_REQUESTED="false"

declare -a STEP_NAMES=()
declare -a STEP_CODES=()
declare -a STEP_DURATIONS=()
declare -a STEP_STDOUT_FILES=()
declare -a STEP_STDERR_FILES=()

show_usage() {
    cat <<'EOF'
Usage: tools/cli/run_cli_matrix.sh [OPTIONS]

Run a local Open Link Token CLI command matrix against the current worktree.
The script prints each exact command before it runs, pauses between commands,
and summarizes pass/fail counts plus the slowest command at the end.

Options:
  --pause-seconds N           Pause after each non-final command (default: 0.25)
  --include-live-update       Also run `update --dry-run --yes` after `update --help`
  --include-extension-install Also run the full extension install/uninstall round-trip.
                              Requires `python -m build` and modifies the active venv.
                              The editable install is restored automatically on exit.
  --auto-continue             Skip confirmation prompts and run the full matrix
  --dry-run                   Print the planned commands without executing them
  --keep-workspace            Preserve the temporary workspace after completion
  --workspace PATH            Use a specific workspace directory instead of mktemp
  --help                      Show this help text
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pause-seconds)
                PAUSE_SECONDS="${2:-}"
                shift 2
                ;;
            --include-live-update)
                INCLUDE_LIVE_UPDATE="true"
                shift
                ;;
            --include-extension-install)
                INCLUDE_EXTENSION_INSTALL="true"
                shift
                ;;
            --auto-continue)
                AUTO_CONTINUE="true"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --keep-workspace)
                KEEP_WORKSPACE="true"
                shift
                ;;
            --workspace)
                WORKSPACE_ROOT="${2:-}"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                show_usage >&2
                exit 1
                ;;
        esac
    done

    if ! python - "$PAUSE_SECONDS" <<'PY'
import sys
value = float(sys.argv[1])
if value < 0:
    raise ValueError("pause must be non-negative")
PY
    then
        echo "--pause-seconds must be a non-negative number" >&2
        exit 1
    fi
}

setup_workspace() {
    if [[ -n "$WORKSPACE_ROOT" ]]; then
        mkdir -p "$WORKSPACE_ROOT"
    else
        WORKSPACE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/openlinktoken-cli-matrix.XXXXXX")"
    fi

    INPUT_DIR="$WORKSPACE_ROOT/inputs"
    OUTPUT_DIR="$WORKSPACE_ROOT/outputs"
    LOG_DIR="$WORKSPACE_ROOT/logs"
    HOME_DIR="$WORKSPACE_ROOT/home"
    WHEEL_DIR="$WORKSPACE_ROOT/wheels"
    mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$LOG_DIR" "$HOME_DIR" "$WHEEL_DIR"

    PERSON_CSV="$INPUT_DIR/people.csv"
    TOKENIZED_DEMO_CSV="$OUTPUT_DIR/tokenized-demo.csv"
    TOKENIZED_HASH_CSV="$OUTPUT_DIR/tokenized-hash.csv"
    ENCRYPTED_CSV="$OUTPUT_DIR/encrypted.csv"
    DECRYPTED_CSV="$OUTPUT_DIR/decrypted.csv"
    PACKAGED_CSV="$OUTPUT_DIR/packaged.csv"
    EXCHANGE_JSON="$OUTPUT_DIR/local.exchange.json"
    RECIPIENT_PUBLIC_KEY="$HOME_DIR/.openlinktoken/recipient.public.pem"
    SENDER_PRIVATE_KEY="$HOME_DIR/.openlinktoken/sender-local.private.pem"

    EXT_HELLO_WORLD_DIR="$REPO_ROOT/lib/python/openlinktoken_ext_hello_world"
    EXT_HELLO_WORLD_WHEEL=""
    EXT_HELLO_WORLD_WAS_INSTALLED="false"
    if python -c "import importlib.metadata; importlib.metadata.distribution('openlinktoken-ext-hello-world')" 2>/dev/null; then
        EXT_HELLO_WORLD_WAS_INSTALLED="true"
    fi

    cat > "$PERSON_CSV" <<'EOF'
RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber
demo-001,John,Doe,98004,Male,2000-01-01,123-45-6789
demo-002,Jane,Smith,12345,Female,1990-05-15,234-56-7890
EOF

    export HOME="$HOME_DIR"
    export PYTHONPATH="$CLI_SOURCE_ROOT:$CORE_SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
    export NO_COLOR="1"
}

cleanup() {
    # Restore the hello-world editable install if the install round-trip removed it.
    if [[ "$INCLUDE_EXTENSION_INSTALL" == "true" && "$EXT_HELLO_WORLD_WAS_INSTALLED" == "true" ]]; then
        if ! python -c "import importlib.metadata; importlib.metadata.distribution('openlinktoken-ext-hello-world')" 2>/dev/null; then
            echo "Restoring openlinktoken-ext-hello-world editable install..."
            python -m pip install -e "$EXT_HELLO_WORLD_DIR" --quiet
        fi
    fi

    local had_failures="false"
    local index
    for index in "${!STEP_CODES[@]}"; do
        if [[ "${STEP_CODES[$index]}" != "0" ]]; then
            had_failures="true"
            break
        fi
    done

    if [[ "$KEEP_WORKSPACE" == "true" || "$had_failures" == "true" ]]; then
        echo "Workspace preserved at: $WORKSPACE_ROOT"
        return
    fi

    if [[ -n "$WORKSPACE_ROOT" && -d "$WORKSPACE_ROOT" ]]; then
        rm -rf "$WORKSPACE_ROOT"
    fi
}

quote_command() {
    local quoted=""
    local part
    for part in "$@"; do
        quoted+=" $(printf '%q' "$part")"
    done
    printf '%s' "${quoted# }"
}

duration_seconds() {
    python - "$1" "$2" <<'PY'
import sys
start_ns = int(sys.argv[1])
end_ns = int(sys.argv[2])
print(f"{(end_ns - start_ns) / 1_000_000_000:.2f}")
PY
}

set_matrix_env_value() {
    local name="$1"
    local value="$2"
    printf -v "$name" '%s' "$value"
    export "$name"
}

set_matrix_env_from_file() {
    local name="$1"
    local path="$2"
    local placeholder="$3"
    local value="$placeholder"

    if [[ -f "$path" ]]; then
        value="$(<"$path")"
    fi

    set_matrix_env_value "$name" "$value"
}

run_step() {
    local name="$1"
    local pause_after="$2"
    shift 2
    local stdout_file="$LOG_DIR/${name}.stdout.log"
    local stderr_file="$LOG_DIR/${name}.stderr.log"
    local command_text
    command_text="$(quote_command "$@")"

    echo
    echo "=== $name ==="
    echo "command: $command_text"

    if [[ "$DRY_RUN" == "true" ]]; then
        STEP_NAMES+=("$name")
        STEP_CODES+=("0")
        STEP_DURATIONS+=("0.00")
        STEP_STDOUT_FILES+=("")
        STEP_STDERR_FILES+=("")
        return
    fi

    local start_ns
    start_ns="$(date +%s%N)"

    "$@" >"$stdout_file" 2>"$stderr_file"
    local rc=$?

    local end_ns
    end_ns="$(date +%s%N)"
    local duration
    duration="$(duration_seconds "$start_ns" "$end_ns")"

    STEP_NAMES+=("$name")
    STEP_CODES+=("$rc")
    STEP_DURATIONS+=("$duration")
    STEP_STDOUT_FILES+=("$stdout_file")
    STEP_STDERR_FILES+=("$stderr_file")

    echo "result: rc=$rc duration=${duration}s"
    if [[ -s "$stdout_file" ]]; then
        sed 's/^/  stdout | /' "$stdout_file"
    fi
    if [[ -s "$stderr_file" ]]; then
        sed 's/^/  stderr | /' "$stderr_file"
    fi

}

maybe_pause() {
    local pause_after="$1"

    if [[ "$pause_after" != "0" && "$pause_after" != "0.0" && "$pause_after" != "0.00" ]]; then
        echo "pause: ${pause_after}s"
        sleep "$pause_after"
    fi
}

confirm_before_next_step() {
    local next_step="$1"
    local pause_after="$2"
    local response=""

    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi

    if [[ "$AUTO_CONTINUE" == "true" ]]; then
        maybe_pause "$pause_after"
        return 0
    fi

    printf "Press Enter to continue to %s, or type 'q' to stop: " "$next_step"
    if ! IFS= read -r response; then
        echo
        echo "Stopping because no confirmation was received."
        STOP_REQUESTED="true"
        return 1
    fi

    if [[ "$response" == "q" || "$response" == "quit" || "$response" == "n" || "$response" == "no" ]]; then
        echo "Stopping at user request."
        STOP_REQUESTED="true"
        return 1
    fi

    maybe_pause "$pause_after"
    return 0
}

print_summary() {
    local total="${#STEP_NAMES[@]}"
    local passed=0
    local failed=0
    local slowest_name="n/a"
    local slowest_duration="-1"
    local index

    for index in "${!STEP_NAMES[@]}"; do
        if [[ "${STEP_CODES[$index]}" == "0" ]]; then
            ((passed+=1))
        else
            ((failed+=1))
        fi

        if python - "${STEP_DURATIONS[$index]}" "$slowest_duration" <<'PY'
import sys
current = float(sys.argv[1])
slowest = float(sys.argv[2])
sys.exit(0 if current > slowest else 1)
PY
        then
            slowest_duration="${STEP_DURATIONS[$index]}"
            slowest_name="${STEP_NAMES[$index]}"
        fi
    done

    echo
    echo "Open Link Token CLI matrix summary"
    echo "Commands run: $total"
    echo "Passed: $passed"
    echo "Failed: $failed"
    echo "Slowest command: $slowest_name (${slowest_duration}s)"
    echo
    echo "Per-command results:"

    for index in "${!STEP_NAMES[@]}"; do
        local status="PASS"
        if [[ "${STEP_CODES[$index]}" != "0" ]]; then
            status="FAIL"
        fi
        printf '  %-4s %-28s %6ss  rc=%s\n' \
            "$status" \
            "${STEP_NAMES[$index]}" \
            "${STEP_DURATIONS[$index]}" \
            "${STEP_CODES[$index]}"
    done
}

run_matrix() {
    local -a python_cmd=(python -m openlinktoken_cli.main --no-update-check)

    run_step "root-help" "$PAUSE_SECONDS" "${python_cmd[@]}" --help
    confirm_before_next_step "help-overview" "$PAUSE_SECONDS" || return 0
    run_step "help-overview" "$PAUSE_SECONDS" "${python_cmd[@]}" help
    confirm_before_next_step "help-package" "$PAUSE_SECONDS" || return 0
    run_step "help-package" "$PAUSE_SECONDS" "${python_cmd[@]}" help package
    confirm_before_next_step "tokenize-help" "$PAUSE_SECONDS" || return 0
    run_step "tokenize-help" "$PAUSE_SECONDS" "${python_cmd[@]}" tokenize --help
    confirm_before_next_step "tokenize-demo" "$PAUSE_SECONDS" || return 0
    run_step "tokenize-demo" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" tokenize -i "$PERSON_CSV" -o "$TOKENIZED_DEMO_CSV" --demo-mode
    confirm_before_next_step "generate-key-pair-help" "$PAUSE_SECONDS" || return 0
    run_step "generate-key-pair-help" "$PAUSE_SECONDS" "${python_cmd[@]}" generate-key-pair --help
    confirm_before_next_step "generate-key-pair-recipient" "$PAUSE_SECONDS" || return 0
    run_step "generate-key-pair-recipient" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" generate-key-pair --name recipient --force
    confirm_before_next_step "generate-key-pair-p384" "$PAUSE_SECONDS" || return 0
    run_step "generate-key-pair-p384" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" generate-key-pair --name recipient-p384 --curve P-384 --force
    confirm_before_next_step "generate-key-pair-p521" "$PAUSE_SECONDS" || return 0
    run_step "generate-key-pair-p521" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" generate-key-pair --name recipient-p521 --curve P-521 --force
    confirm_before_next_step "initiate-exchange-help" "$PAUSE_SECONDS" || return 0
    run_step "initiate-exchange-help" "$PAUSE_SECONDS" "${python_cmd[@]}" initiate-exchange --help
    set_matrix_env_value "$HASHING_SECRET_ENV_VAR" "$DEFAULT_HASHING_SECRET"
    set_matrix_env_from_file "$RECIPIENT_PUBLIC_KEY_ENV_VAR" "$RECIPIENT_PUBLIC_KEY" "invalid-recipient-public-key"
    confirm_before_next_step "initiate-exchange-local" "$PAUSE_SECONDS" || return 0
    run_step "initiate-exchange-local" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" initiate-exchange --name sender-local \
        --public-key-env "$RECIPIENT_PUBLIC_KEY_ENV_VAR" \
        --output "$EXCHANGE_JSON" \
        --hashingsecret-env "$HASHING_SECRET_ENV_VAR" \
        --force
    set_matrix_env_from_file "$SENDER_PRIVATE_KEY_ENV_VAR" "$SENDER_PRIVATE_KEY" "invalid-sender-private-key"
    confirm_before_next_step "tokenize-hash" "$PAUSE_SECONDS" || return 0
    run_step "tokenize-hash" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" tokenize -i "$PERSON_CSV" -o "$TOKENIZED_HASH_CSV" \
        --exchange-config "$EXCHANGE_JSON" \
        --private-key-env "$SENDER_PRIVATE_KEY_ENV_VAR"
    confirm_before_next_step "encrypt-help" "$PAUSE_SECONDS" || return 0
    run_step "encrypt-help" "$PAUSE_SECONDS" "${python_cmd[@]}" encrypt --help
    confirm_before_next_step "encrypt-tokenized-output" "$PAUSE_SECONDS" || return 0
    run_step "encrypt-tokenized-output" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" encrypt -i "$TOKENIZED_HASH_CSV" -o "$ENCRYPTED_CSV" \
        --exchange-config "$EXCHANGE_JSON" \
        --private-key-env "$SENDER_PRIVATE_KEY_ENV_VAR"
    confirm_before_next_step "decrypt-help" "$PAUSE_SECONDS" || return 0
    run_step "decrypt-help" "$PAUSE_SECONDS" "${python_cmd[@]}" decrypt --help
    confirm_before_next_step "decrypt-encrypted-output" "$PAUSE_SECONDS" || return 0
    run_step "decrypt-encrypted-output" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" decrypt -i "$ENCRYPTED_CSV" -o "$DECRYPTED_CSV" \
        --exchange-config "$EXCHANGE_JSON" \
        --private-key-env "$SENDER_PRIVATE_KEY_ENV_VAR"
    confirm_before_next_step "package-help" "$PAUSE_SECONDS" || return 0
    run_step "package-help" "$PAUSE_SECONDS" "${python_cmd[@]}" package --help
    confirm_before_next_step "package-csv" "$PAUSE_SECONDS" || return 0
    run_step "package-csv" "$PAUSE_SECONDS" \
        "${python_cmd[@]}" package -i "$PERSON_CSV" -o "$PACKAGED_CSV" \
        --exchange-config "$EXCHANGE_JSON" \
        --private-key-env "$SENDER_PRIVATE_KEY_ENV_VAR"
    confirm_before_next_step "update-help" "$PAUSE_SECONDS" || return 0
    run_step "update-help" "0" "${python_cmd[@]}" update --help

    if [[ "$INCLUDE_LIVE_UPDATE" == "true" ]]; then
        confirm_before_next_step "update-dry-run" "$PAUSE_SECONDS" || return 0
        run_step "update-dry-run" "0" "${python_cmd[@]}" update --dry-run --yes
    fi

    # ---- Extension tests ----

    confirm_before_next_step "extension-help" "$PAUSE_SECONDS" || return 0
    run_step "extension-help" "$PAUSE_SECONDS" "${python_cmd[@]}" extension --help
    confirm_before_next_step "extension-list" "$PAUSE_SECONDS" || return 0
    run_step "extension-list" "$PAUSE_SECONDS" "${python_cmd[@]}" extension list

    # hello-world steps only run when the reference extension is already installed
    # in the active Python environment (entry-point discovery must resolve it).
    if [[ "$EXT_HELLO_WORLD_WAS_INSTALLED" == "true" ]]; then
        confirm_before_next_step "extension-hello-world-help" "$PAUSE_SECONDS" || return 0
        run_step "extension-hello-world-help" "$PAUSE_SECONDS" "${python_cmd[@]}" hello-world --help
        confirm_before_next_step "extension-hello-world-hello" "$PAUSE_SECONDS" || return 0
        run_step "extension-hello-world-hello" "$PAUSE_SECONDS" "${python_cmd[@]}" hello-world hello --name Alice
        confirm_before_next_step "extension-hello-world-bye" "$PAUSE_SECONDS" || return 0
        run_step "extension-hello-world-bye" "0" "${python_cmd[@]}" hello-world bye --name Bob
    else
        echo "Skipping hello-world steps (openlinktoken-ext-hello-world not installed; use --include-extension-install to test the full install/run/uninstall round-trip)"
    fi

    if [[ "$INCLUDE_EXTENSION_INSTALL" == "true" ]]; then
        # Build the hello-world wheel into the isolated workspace.
        echo
        if [[ "$DRY_RUN" != "true" ]]; then
            confirm_before_next_step "extension-build-wheel" "$PAUSE_SECONDS" || return 0
            run_step "extension-build-wheel" "$PAUSE_SECONDS" \
                python -m build --wheel --outdir "$WHEEL_DIR" "$EXT_HELLO_WORLD_DIR" -q

            local last_step_index=$(( ${#STEP_CODES[@]} - 1 ))
            if (( last_step_index < 0 )) || [[ "${STEP_CODES[$last_step_index]}" != "0" ]]; then
                echo "ERROR: wheel build failed; skipping install/uninstall steps." >&2
                return 0
            fi

            EXT_HELLO_WORLD_WHEEL="$(ls "$WHEEL_DIR"/openlinktoken_ext_hello_world-*.whl 2>/dev/null | head -1)"
            echo "Built: $EXT_HELLO_WORLD_WHEEL"

            confirm_before_next_step "extension-install" "$PAUSE_SECONDS" || return 0
            run_step "extension-install" "$PAUSE_SECONDS" \
                "${python_cmd[@]}" extension install "file://$EXT_HELLO_WORLD_WHEEL" --yes
            confirm_before_next_step "extension-list-installed" "$PAUSE_SECONDS" || return 0
            run_step "extension-list-installed" "$PAUSE_SECONDS" "${python_cmd[@]}" extension list
            confirm_before_next_step "extension-hello-world-hello-installed" "$PAUSE_SECONDS" || return 0
            run_step "extension-hello-world-hello-installed" "$PAUSE_SECONDS" \
                "${python_cmd[@]}" hello-world hello --name Charlie
            confirm_before_next_step "extension-uninstall" "$PAUSE_SECONDS" || return 0
            run_step "extension-uninstall" "$PAUSE_SECONDS" \
                "${python_cmd[@]}" extension uninstall hello-world
            confirm_before_next_step "extension-list-after-uninstall" "$PAUSE_SECONDS" || return 0
            run_step "extension-list-after-uninstall" "0" "${python_cmd[@]}" extension list
        else
            echo "command: (build wheel from $EXT_HELLO_WORLD_DIR)"
            STEP_NAMES+=("extension-build-wheel")
            STEP_CODES+=("0")
            STEP_DURATIONS+=("0.00")
            STEP_STDOUT_FILES+=("")
            STEP_STDERR_FILES+=("")
            for step in extension-install extension-list-installed extension-hello-world-hello-installed extension-uninstall extension-list-after-uninstall; do
                confirm_before_next_step "$step" "$PAUSE_SECONDS" || return 0
                run_step "$step" "$PAUSE_SECONDS" "${python_cmd[@]}" extension --help
            done
        fi
    fi
}

main() {
    parse_args "$@"
    setup_workspace
    trap cleanup EXIT

    echo "Using workspace: $WORKSPACE_ROOT"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Dry run: printing planned commands only."
    fi

    run_matrix
    print_summary

    if [[ "$STOP_REQUESTED" == "true" ]]; then
        return 0
    fi

    local index
    for index in "${!STEP_CODES[@]}"; do
        if [[ "${STEP_CODES[$index]}" != "0" ]]; then
            return 1
        fi
    done
    return 0
}

main "$@"
