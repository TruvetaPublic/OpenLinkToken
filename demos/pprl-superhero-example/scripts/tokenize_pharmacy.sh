#!/usr/bin/env bash
#
# Tokenize the pharmacy dataset using Open Link Token (Python CLI).
#
# Output:
#   outputs/pharmacy_tokens.csv
#   outputs/pharmacy_tokens.metadata.json
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/.."
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Demo secrets (CHANGE THESE IN PRODUCTION!)
# Keep in sync with:
# - scripts/tokenize_hospital.sh
# - scripts/analyze_overlap.py
HASHING_SECRET="SuperHeroHashingKey2024"
ENCRYPTION_KEY="SuperHero-Encryption-Key-32chars" # Must be exactly 32 characters

echo "============================================================"
echo "Tokenizing Pharmacy Dataset (Superhero PPRL Demo)"
echo "============================================================"
echo ""

# Ensure Python CLI is available
if ! command -v olt &>/dev/null; then
  echo "olt CLI not found. Installing Python CLI..."
  (cd "${PROJECT_ROOT}" && uv pip install -e lib/python/openlinktoken -e lib/python/openlinktoken-cli)
fi

mkdir -p "${DEMO_DIR}/outputs"

echo "Running Open Link Token CLI (pharmacy)..."
olt package \
  -i "${DEMO_DIR}/datasets/pharmacy_superhero_data.csv" \
  -o "${DEMO_DIR}/outputs/pharmacy_tokens.csv" \
  -h "${HASHING_SECRET}" \
  -e "${ENCRYPTION_KEY}"

echo ""
echo "Done."
echo "  - ${DEMO_DIR}/outputs/pharmacy_tokens.csv"
echo "  - ${DEMO_DIR}/outputs/pharmacy_tokens.metadata.json"
