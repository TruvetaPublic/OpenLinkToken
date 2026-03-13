#!/usr/bin/env python3
"""Regression tests for the devcontainer unified setup script."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / ".devcontainer" / "scripts" / "unified-setup.sh"
CompletedProcess = subprocess.CompletedProcess[str]


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _create_fake_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repo"
    script_dir = repo_root / ".devcontainer" / "scripts"
    script_dir.mkdir(parents=True)
    shutil.copy2(SOURCE_SCRIPT, script_dir / "unified-setup.sh")

    (repo_root / ".git").mkdir()
    (repo_root / ".gitignore").write_text("", encoding="utf-8")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    (home_dir / ".bashrc").write_text("", encoding="utf-8")
    (home_dir / ".zshrc").write_text("", encoding="utf-8")

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log_path = tmp_path / "command.log"

    _write_executable(
        fake_bin / "uv",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "uv:$*" >> "{log_path}"
if [ "${{1:-}}" = "venv" ]; then
  target="${{@: -1}}"
  mkdir -p "$target/bin"
  cat > "$target/bin/activate" <<'EOF'
#!/usr/bin/env bash
export VIRTUAL_ENV="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)"
EOF
  cat > "$target/bin/pip" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "pip:$*" >> "{log_path}"
EOF
  chmod +x "$target/bin/pip"
  cat > "$target/bin/prek" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "prek:$*" >> "{log_path}"
EOF
  chmod +x "$target/bin/prek"
fi
""",
    )
    _write_executable(
        fake_bin / "apm",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "apm:$*" >> "{log_path}"
""",
    )
    _write_executable(
        fake_bin / "sudo",
        """#!/usr/bin/env bash
set -euo pipefail
"$@"
""",
    )
    _write_executable(
        fake_bin / "ssh-keygen",
        """#!/usr/bin/env bash
set -euo pipefail
exit 1
""",
    )
    _write_executable(
        fake_bin / "ssh-keyscan",
        """#!/usr/bin/env bash
set -euo pipefail
printf 'github.com ssh-rsa fake-key\\n'
""",
    )
    _write_executable(
        fake_bin / "git",
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "-C" ]; then
  shift 2
fi
if [ "${1:-}" = "ls-files" ]; then
  exit 0
fi
echo "unexpected git invocation: $*" >&2
exit 1
""",
    )

    return repo_root, home_dir, log_path


def _run_setup(tmp_path: Path, phase: str, *, env_overrides: dict[str, str] | None = None) -> CompletedProcess:
    repo_root, home_dir, _ = _create_fake_repo(tmp_path)
    venv_dir = tmp_path / "custom-venv"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home_dir),
            "PATH": f"{tmp_path / 'fake-bin'}:{env['PATH']}",
            "UV_PROJECT_ENVIRONMENT": str(venv_dir),
        }
    )
    if env_overrides:
        env.update(env_overrides)

    script_path = repo_root / ".devcontainer" / "scripts" / "unified-setup.sh"
    return subprocess.run(
        [str(script_path), phase],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_post_start_skips_workspace_package_installation(tmp_path: Path) -> None:
    """post-start should only do core environment checks, not reinstall packages."""
    completed = _run_setup(tmp_path, "post-start")

    assert completed.returncode == 0, completed.stderr
    assert "Installing all workspace packages and dependencies" not in completed.stdout
    assert "Refreshing workspace packages" not in completed.stdout
    assert "Installing prek" not in completed.stdout


def test_post_attach_refreshes_workspace_without_running_full_setup(tmp_path: Path) -> None:
    """post-attach should refresh workspace packages instead of re-running first-create work."""
    completed = _run_setup(tmp_path, "post-attach")

    assert completed.returncode == 0, completed.stderr
    assert "Refreshing workspace packages" in completed.stdout
    assert "Installing prek" not in completed.stdout
    assert "Installing all workspace packages and dependencies" not in completed.stdout


def test_shell_init_uses_configured_venv_path(tmp_path: Path) -> None:
    """Shell init should point at the configured shared venv rather than a hard-coded path."""
    repo_root, home_dir, _ = _create_fake_repo(tmp_path)
    venv_dir = tmp_path / "custom-venv"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home_dir),
            "PATH": f"{tmp_path / 'fake-bin'}:{env['PATH']}",
            "UV_PROJECT_ENVIRONMENT": str(venv_dir),
        }
    )

    completed = subprocess.run(
        [str(repo_root / ".devcontainer" / "scripts" / "unified-setup.sh"), "post-create"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    bashrc = (home_dir / ".bashrc").read_text(encoding="utf-8")
    assert f"source {venv_dir}/bin/activate 2>/dev/null || true" in bashrc
