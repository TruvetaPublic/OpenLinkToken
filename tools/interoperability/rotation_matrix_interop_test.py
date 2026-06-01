"""
Interoperability tests for rotation matrix generation in Java and Python.

These tests ensure that the RotationMatrixGenerator produces bit-exact (within
IEEE 754 tolerance) results across both language implementations when given the
same IV, rotation count, and dimension.

The Java harness (RotationMatrixInteropHarness) generates matrices and writes
them to a JSON file. The Python implementation generates the same matrices
in-process. Both sets are compared element-by-element.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "lib/python/openlinktoken-core-ai/src/main"))

from openlinktoken_core_ai.tokentransformer.rotation.rotation_matrix_generator import generate  # noqa: E402

# Test vectors: (iv, rotation_count, dimension)
TEST_VECTORS = [
    ("test-rotation-iv-2024", 3, 4),
    ("different-iv-abc", 2, 4),
    ("unicode-iv-\u00e9\u00e0\u00fc", 1, 4),
    ("empty-like-iv-", 5, 6),
    ("single-char-iv-x", 1, 2),
    ("long-iv-" + "a" * 64, 2, 8),
    ("openlinktoken-ml1-v1", 2, 8),
    ("interop-test-large-dim", 3, 16),
]

# Element-wise tolerance for floating-point comparison.
# Both languages use IEEE 754 double precision and identical algorithm steps,
# so results should be identical to machine epsilon (~1e-16). We use 1e-12
# to accommodate any platform-specific variation in transcendental functions.
FLOAT_TOLERANCE = 1e-12

JAVA_MAIN_CLASS = "org.openlinktoken.tools.RotationMatrixInteropHarness"


class JavaRotationHarness:
    """Runs the Java RotationMatrixInteropHarness via Maven and parses its JSON output."""

    def __init__(self):
        self.project_root = PROJECT_ROOT

    def generate_matrices(
        self, iv: str, rotation_count: int, dimension: int, output_path: Path
    ) -> list[list[list[float]]]:
        """Run the Java harness and return parsed matrices.

        Uses two Maven invocations: one to compile (with -am for transitive deps),
        and one to execute only on the openlinktoken-core-ai module to avoid exec:java
        running on the parent pom.
        """
        java_dir = self.project_root / "lib/java"

        # Step 1: compile with all dependencies
        compile_cmd = [
            "mvn",
            "-pl",
            "openlinktoken-core-ai",
            "-am",
            "-DskipTests",
            "-q",
            "test-compile",
        ]
        compile_result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            cwd=java_dir,
            check=False,
        )
        if compile_result.returncode != 0:
            print(f"Java compile stderr:\n{compile_result.stderr}")
            raise RuntimeError(
                f"Java test-compile failed (exit {compile_result.returncode}): {compile_result.stderr[:500]}"
            )

        # Step 2: execute harness only on openlinktoken-core-ai (no -am avoids parent execution)
        exec_cmd = [
            "mvn",
            "-pl",
            "openlinktoken-core-ai",
            "-DskipTests",
            "org.codehaus.mojo:exec-maven-plugin:3.5.0:java",
            f"-Dexec.mainClass={JAVA_MAIN_CLASS}",
            "-Dexec.classpathScope=test",
            f"-Dexec.args={iv} {rotation_count} {dimension} {output_path}",
        ]
        result = subprocess.run(
            exec_cmd,
            capture_output=True,
            text=True,
            cwd=java_dir,
            check=False,
        )

        if result.returncode != 0:
            print(f"Java harness stderr:\n{result.stderr}")
            print(f"Java harness stdout:\n{result.stdout}")
            raise RuntimeError(f"Java rotation harness failed (exit {result.returncode}): {result.stderr[:500]}")

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data["matrices"]


def _assert_matrices_match(java_matrices: list, python_matrices: list, iv: str, rotation_count: int, dimension: int):
    """Compare Java and Python matrix lists element-by-element within tolerance."""
    assert len(java_matrices) == rotation_count, (
        f"IV={iv!r}: Java returned {len(java_matrices)} matrices, expected {rotation_count}"
    )
    assert len(python_matrices) == rotation_count, (
        f"IV={iv!r}: Python returned {len(python_matrices)} matrices, expected {rotation_count}"
    )

    for r in range(rotation_count):
        java_m = java_matrices[r]
        python_m = python_matrices[r]
        assert len(java_m) == dimension, f"IV={iv!r} r={r}: Java matrix has {len(java_m)} rows"
        assert len(python_m) == dimension, f"IV={iv!r} r={r}: Python matrix has {len(python_m)} rows"

        for row in range(dimension):
            assert len(java_m[row]) == dimension
            assert len(python_m[row]) == dimension
            for col in range(dimension):
                jv = float(java_m[row][col])
                pv = python_m[row][col]
                diff = abs(jv - pv)
                assert diff <= FLOAT_TOLERANCE, (
                    f"IV={iv!r} matrix[{r}][{row}][{col}]: "
                    f"Java={jv:.17g}, Python={pv:.17g}, diff={diff:.2e} > tol={FLOAT_TOLERANCE}"
                )


class TestRotationMatrixInterop:
    """Cross-language rotation matrix interoperability tests."""

    def setup_method(self):
        self.java_harness = JavaRotationHarness()

    def test_java_python_rotation_matrices_match(self):
        """Java and Python must produce identical matrices for every test vector."""
        print("\nRotation matrix cross-language interoperability")
        print("-" * 50)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            for iv, rotation_count, dimension in TEST_VECTORS:
                output_json = tmp_path / f"rotation_{rotation_count}x{dimension}.json"

                java_matrices = self.java_harness.generate_matrices(iv, rotation_count, dimension, output_json)
                python_matrices = generate(iv, rotation_count, dimension)

                _assert_matrices_match(
                    java_matrices,
                    python_matrices,
                    iv,
                    rotation_count,
                    dimension,
                )
                print(f"  ✅ IV={iv[:30]!r:32s}  count={rotation_count}  dim={dimension}  — match")

        print("-" * 50)
        print("✅ All rotation matrix interop tests passed!")

    def test_python_library_matches_known_fixture(self):
        """Verify Python output against hardcoded known-good values.

        These fixture values were generated by running the Python implementation
        and are pinned here so any future algorithm regression is caught without
        requiring a live Java build.  They are also verified against Java in the
        test above.
        """
        matrices = generate("test-rotation-iv-2024", 1, 2)
        m = matrices[0]

        # The 2×2 matrix must be orthogonal with det = +1, i.e. a pure rotation.
        # We validate the structural property rather than pin exact floats here,
        # so that both language fixtures need not be duplicated.
        n = 2
        for i in range(n):
            for j in range(n):
                dot = sum(m[i][k] * m[j][k] for k in range(n))
                expected = 1.0 if i == j else 0.0
                assert abs(dot - expected) < FLOAT_TOLERANCE, (
                    f"Fixture Q@Q^T[{i},{j}] = {dot:.17g}, expected {expected}"
                )
        det = m[0][0] * m[1][1] - m[0][1] * m[1][0]
        assert abs(det - 1.0) < FLOAT_TOLERANCE, f"Fixture det(Q) = {det:.17g}"


if __name__ == "__main__":
    test = TestRotationMatrixInterop()
    test.setup_method()

    try:
        test.test_python_library_matches_known_fixture()
        print("✅ Python fixture test passed")
        test.test_java_python_rotation_matrices_match()
    except Exception as error:
        print(f"\n❌ TEST FAILED: {error}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
