#!/usr/bin/env bash
#
# Run the Superhero PPRL example end-to-end:
#  1) Generate datasets
#  2) Tokenize with the Python Open Link Token CLI
#  3) Decrypt-and-compare tokens to measure overlap
#
set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DATASETS_DIR="${DEMO_DIR}/datasets"
OUTPUTS_DIR="${DEMO_DIR}/outputs"
VENV_ACTIVATE="${PROJECT_ROOT}/.venv/bin/activate"

# Keys (keep in sync with tokenization scripts and analyze_overlap.py)
HASHING_SECRET="SuperHeroHashingKey2024"
ENCRYPTION_KEY="SuperHero-Encryption-Key-32chars" # Must be exactly 32 characters

echo "============================================================"
echo "Superhero PPRL - End-to-End Demo Runner"
echo "============================================================"
echo "Project root: ${PROJECT_ROOT}"
echo "Demo dir    : ${DEMO_DIR}"
echo ""

# Step 0: Python environment (best-effort)
if [[ -f "${VENV_ACTIVATE}" ]]; then
  echo -e "${BLUE}Activating repo Python venv...${NC}"
  # shellcheck disable=SC1090
  source "${VENV_ACTIVATE}"
else
  echo -e "${YELLOW}Repo venv not found at ${VENV_ACTIVATE}.${NC}"
  echo -e "${YELLOW}Continuing with system Python. Ensure 'cryptography' is installed.${NC}"
fi

# Ensure required Python deps for analysis
ANALYZE_OVERLAP_COMMAND=(python "${DEMO_DIR}/scripts/analyze_overlap.py")
if ! python -c "import cryptography" >/dev/null 2>&1; then
  if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}Python package 'cryptography' not found and uv is unavailable.${NC}"
    echo -e "${RED}Install uv or activate a virtual environment with cryptography before rerunning.${NC}"
    exit 1
  fi

  echo -e "${YELLOW}Python package 'cryptography' not found. Using uv-managed dependency for overlap analysis...${NC}"
  ANALYZE_OVERLAP_COMMAND=(uv run --isolated --with cryptography python "${DEMO_DIR}/scripts/analyze_overlap.py")
fi

# Step 1: Generate datasets
echo -e "${BLUE}Step 1/3: Generating datasets...${NC}"
mkdir -p "${DATASETS_DIR}"
python "${DEMO_DIR}/scripts/generate_superhero_datasets.py"
echo ""

# Step 2: Tokenize datasets with the Python CLI
echo -e "${BLUE}Step 2/3: Tokenizing datasets with Open Link Token...${NC}"
chmod +x "${DEMO_DIR}/scripts/tokenize_hospital.sh" || true
chmod +x "${DEMO_DIR}/scripts/tokenize_pharmacy.sh" || true
"${DEMO_DIR}/scripts/tokenize_hospital.sh"
"${DEMO_DIR}/scripts/tokenize_pharmacy.sh"
echo ""

# Step 3: Analyze overlap (decrypt + compare)
echo -e "${BLUE}Step 3/3: Analyzing overlap (decrypting and comparing tokens)...${NC}"
"${ANALYZE_OVERLAP_COMMAND[@]}"
echo ""

echo "============================================================"
echo -e "${GREEN}End-to-end run complete!${NC}"
echo "Outputs:"
echo "  - ${OUTPUTS_DIR}/hospital_tokens.csv"
echo "  - ${OUTPUTS_DIR}/pharmacy_tokens.csv"
echo "  - ${OUTPUTS_DIR}/matching_records.csv"
echo "  - ${OUTPUTS_DIR}/hospital_tokens.metadata.json"
echo "  - ${OUTPUTS_DIR}/pharmacy_tokens.metadata.json"
echo "============================================================"
