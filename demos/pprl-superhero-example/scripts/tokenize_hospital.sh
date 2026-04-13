#!/usr/bin/env bash
#
# Tokenize the hospital dataset using OpenLinkToken (Python CLI).
#
# Output:
#   outputs/hospital_tokens.csv
#   outputs/hospital_tokens.metadata.json
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/.."
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Demo secrets (CHANGE THESE IN PRODUCTION!)
# Keep in sync with:
# - scripts/tokenize_pharmacy.sh
# - scripts/analyze_overlap.py
HASHING_SECRET="SuperHeroHashingKey2024"
ENCRYPTION_KEY="SuperHero-Encryption-Key-32chars" # Must be exactly 32 characters

echo "============================================================"
echo "Tokenizing Hospital Dataset (Superhero PPRL Demo)"
echo "============================================================"
echo ""

# Ensure Python CLI is available
if ! command -v openlinktoken &>/dev/null; then
  echo "openlinktoken CLI not found. Installing Python CLI..."
  (cd "${PROJECT_ROOT}" && uv pip install -e lib/python/openlinktoken -e lib/python/openlinktoken-cli)
fi

mkdir -p "${DEMO_DIR}/outputs"

echo "Running OpenLinkToken CLI (hospital)..."
openlinktoken package \
  -t csv \
  -i "${DEMO_DIR}/datasets/hospital_superhero_data.csv" \
  -o "${DEMO_DIR}/outputs/hospital_tokens.csv" \
  -h "${HASHING_SECRET}" \
  -e "${ENCRYPTION_KEY}"

echo ""
echo "Done."
echo "  - ${DEMO_DIR}/outputs/hospital_tokens.csv"
echo "  - ${DEMO_DIR}/outputs/hospital_tokens.metadata.json"
