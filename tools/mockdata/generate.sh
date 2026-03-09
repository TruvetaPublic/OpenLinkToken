#!/usr/bin/env bash
set -euo pipefail

uv run --isolated --with faker python data_generator.py 100 0.05 test_data.csv
