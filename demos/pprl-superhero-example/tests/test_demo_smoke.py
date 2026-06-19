from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).resolve().parent.parent
NOTEBOOK_PATH = DEMO_DIR / "PPRL_Superhero_Demo.ipynb"
ANALYZE_SCRIPT = DEMO_DIR / "scripts" / "analyze_overlap.py"


def _run_command(*args: str, cwd: Path = DEMO_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def prepared_demo_artifacts() -> None:
    result = _run_command("bash", "run_end_to_end.sh")
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_analyze_overlap_supports_relaxed_rules_and_custom_output(prepared_demo_artifacts: None) -> None:
    output_name = "matching_records_alt.csv"
    output_path = DEMO_DIR / "outputs" / output_name
    if output_path.exists():
        output_path.unlink()

    result = _run_command(
        sys.executable,
        str(ANALYZE_SCRIPT),
        "--matching-rules",
        "T1",
        "T2",
        "T3",
        "T5",
        "--output",
        output_name,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert output_path.exists()

    with output_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert set(rows[0]) == {"HospitalRecordId", "PharmacyRecordId", "MatchingTokens", "TokenCount"}


def test_notebook_uses_pyspark_bridge_apis() -> None:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    assert "OpenLinkTokenProcessor.from_exchange_config" in source
    assert "OpenLinkTokenOverlapAnalyzer.from_exchange_config" in source


def test_notebook_executes_end_to_end(tmp_path: Path) -> None:
    if shutil.which("jupyter") is None:
        pytest.skip("jupyter is not installed in this environment")
    if importlib.util.find_spec("pyspark") is None:
        pytest.skip("pyspark is not installed in this environment")

    notebook_copy = DEMO_DIR / f"tmp-{NOTEBOOK_PATH.name}"
    shutil.copy2(NOTEBOOK_PATH, notebook_copy)
    try:
        result = _run_command(
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--output",
            "tmp-executed.ipynb",
            str(notebook_copy),
            cwd=DEMO_DIR,
        )
    finally:
        notebook_copy.unlink(missing_ok=True)
        (DEMO_DIR / "tmp-executed.ipynb").unlink(missing_ok=True)

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
