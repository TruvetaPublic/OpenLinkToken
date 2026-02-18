#!/usr/bin/env bash
#
# Tokenize the pharmacy dataset using OpenToken (Java CLI).
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

# Check if OpenToken JAR exists (in opentoken-cli module)
JAR_FILE=$(ls "${PROJECT_ROOT}/lib/java/opentoken-cli/target/opentoken-cli-"*.jar 2>/dev/null | head -1)
if [ -z "${JAR_FILE}" ]; then
  echo "OpenToken JAR not found. Building..."
  (cd "${PROJECT_ROOT}/lib/java" && mvn clean install -DskipTests)
  JAR_FILE=$(ls "${PROJECT_ROOT}/lib/java/opentoken-cli/target/opentoken-cli-"*.jar | head -1)
fi

echo "Using JAR: ${JAR_FILE}"
echo ""

mkdir -p "${DEMO_DIR}/outputs"

echo "Running OpenToken CLI (pharmacy)..."
java -jar "${JAR_FILE}" \
  -t csv \
  -i "${DEMO_DIR}/datasets/pharmacy_superhero_data.csv" \
  -o "${DEMO_DIR}/outputs/pharmacy_tokens.csv" \
  -h "${HASHING_SECRET}" \
  -e "${ENCRYPTION_KEY}"

echo ""
echo "Done."
echo "  - ${DEMO_DIR}/outputs/pharmacy_tokens.csv"
echo "  - ${DEMO_DIR}/outputs/pharmacy_tokens.metadata.json"
