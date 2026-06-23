#!/usr/bin/env bash
#
# Tokenize the pharmacy dataset using Open Link Token (Python CLI).
#
# Output:
#   outputs/pharmacy_tokens.csv
#   outputs/pharmacy_tokens.metadata.json
#
# Exchange config and private key are read from environment variables when set
# by run_end_to_end.sh, or created automatically if running standalone.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/.."
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Demo hashing secret (keep in sync with tokenize_hospital.sh and run_end_to_end.sh)
HASHING_SECRET="SuperHeroHashingKey2024"
DEMO_KEY_NAME="superhero-demo"

echo "============================================================"
echo "Tokenizing Pharmacy Dataset (Superhero PPRL Demo)"
echo "============================================================"
echo ""

# Ensure Python CLI is available
if ! command -v olt &>/dev/null; then
  echo "olt CLI not found. Installing Python CLI..."
  (cd "${PROJECT_ROOT}" && uv pip install -e lib/python/openlinktoken -e lib/python/openlinktoken-cli)
fi

# Resolve exchange config and private key (use env vars set by run_end_to_end.sh,
# or fall back to default paths when running standalone)
EXCHANGE_CONFIG="${OLT_DEMO_EXCHANGE_CONFIG:-${DEMO_DIR}/superhero-demo.exchange.json}"
PRIVATE_KEY="${OLT_DEMO_PRIVATE_KEY:-${HOME}/.openlinktoken/${DEMO_KEY_NAME}.private.pem}"

# Set up exchange config when running standalone (not called from run_end_to_end.sh)
if [[ ! -f "${EXCHANGE_CONFIG}" ]] || [[ ! -f "${PRIVATE_KEY}" ]]; then
  echo "Setting up demo exchange config..."
  olt generate-key-pair -n "${DEMO_KEY_NAME}" --force
  DEMO_HASHING_SECRET="${HASHING_SECRET}" olt initiate-exchange \
    --public-key "${HOME}/.openlinktoken/${DEMO_KEY_NAME}.public.pem" \
    --sender-private-key "${HOME}/.openlinktoken/${DEMO_KEY_NAME}.private.pem" \
    --hashingsecret-env DEMO_HASHING_SECRET \
    -n "${DEMO_KEY_NAME}" \
    -o "${EXCHANGE_CONFIG}" \
    --force
  echo ""
fi

mkdir -p "${DEMO_DIR}/outputs"

echo "Running Open Link Token CLI (pharmacy)..."
olt package \
  -i "${DEMO_DIR}/datasets/pharmacy_superhero_data.csv" \
  -o "${DEMO_DIR}/outputs/pharmacy_tokens.csv" \
  --exchange-config "${EXCHANGE_CONFIG}" \
  --private-key "${PRIVATE_KEY}"

echo ""
echo "Done."
echo "  - ${DEMO_DIR}/outputs/pharmacy_tokens.csv"
echo "  - ${DEMO_DIR}/outputs/pharmacy_tokens.metadata.json"
