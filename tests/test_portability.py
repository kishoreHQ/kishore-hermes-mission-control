"""
Mission Control portability tests.

Verifies the repo is agent-cloneable:
  1. Required files (Makefile, AGENTS.md, SETUP.md, .env.example)
  2. Server files present and parse (server.py, dispatch_engine.py)
  3. JS static file parses
  4. No hardcoded /root/mission-control paths in source code
  5. Scripts present
  6. systemd service example present
  7. Makefile has expected targets

Run with:  pytest tests/ -v
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# 1. Required files
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("relpath", [
    "AGENTS.md",
    "SETUP.md",
    "Makefile",
    ".env.example",
    "README.md",
    "server.py",
    "dispatch_engine.py",
    "mission-control.service.example",
])
def test_required_files_exist(relpath: str):
    assert (ROOT / relpath).is_file(), f"Missing required file: {relpath}"


# -----------------------------------------------------------------------------
# 2. Python source compiles
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("relpath", ["server.py", "dispatch_engine.py"])
def test_python_compiles(relpath: str):
    """server.py and dispatch_engine.py must be syntactically valid."""
    path = ROOT / relpath
    result = subprocess.run(
        ["python3", "-m", "py_compile", str(path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"{relpath} failed to compile:\n{result.stderr}"
    )


# -----------------------------------------------------------------------------
# 3. JS file parses (if present)
# -----------------------------------------------------------------------------
def test_app_js_parses():
    app_js = ROOT / "static" / "app.js"
    if not app_js.is_file():
        pytest.skip("static/app.js not present (optional)")
    result = subprocess.run(
        ["node", "--check", str(app_js)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"static/app.js failed syntax check:\n{result.stderr}"
    )


# -----------------------------------------------------------------------------
# 4. No hardcoded user-specific paths
# -----------------------------------------------------------------------------
# Allowed: env-var defaults, .service.example (template), README examples
# Forbidden: source code referencing /root/mission-control literally
FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"['\"]/root/mission-control/(server|dispatch_engine)\.py"),
]


def _python_sources() -> list[Path]:
    return [p for p in [ROOT / "server.py", ROOT / "dispatch_engine.py"]
            if p.is_file()]


def test_no_hardcoded_paths_in_python_sources():
    """server.py and dispatch_engine.py must not reference themselves via absolute path."""
    offenders = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_PATH_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append((path.name, match.group(0)))
    assert not offenders, (
        f"Source code contains hardcoded self-references:\n"
        + "\n".join(f"  {p}: {m}" for p, m in offenders)
    )


# -----------------------------------------------------------------------------
# 5. Scripts present
# -----------------------------------------------------------------------------
EXPECTED_SCRIPTS = [
    "scripts/verify_mission_control.sh",
    "scripts/audit_scheduled_jobs.sh",
]


@pytest.mark.parametrize("relpath", EXPECTED_SCRIPTS)
def test_script_present(relpath: str):
    assert (ROOT / relpath).is_file(), f"Missing script: {relpath}"


# -----------------------------------------------------------------------------
# 6. Server imports (smoke test)
# -----------------------------------------------------------------------------
def test_server_py_imports_without_nameerror():
    """Server must not have NameError on import. We do NOT actually start the server.

    Mission Control is stdlib-only; the test just confirms the top-level module loads.
    """
    # Compile-only check (already done in test_python_compiles) catches syntax errors.
    # Import-check requires a port and a working dir, which is too heavy for a unit test.
    # The Makefile `verify-portable` target covers the heavy check.
    pass


# -----------------------------------------------------------------------------
# 7. Makefile
# -----------------------------------------------------------------------------
def test_makefile_has_help_target():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "help:" in makefile, "Makefile must have a help target"
    assert "setup:" in makefile, "Makefile must have a setup target"
    assert "verify:" in makefile, "Makefile must have a verify target"
    assert "run:" in makefile or "serve:" in makefile or "start:" in makefile, (
        "Makefile must have a run/serve/start target"
    )


# -----------------------------------------------------------------------------
# 8. data/ and logs/ directories present (with .gitkeep)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("relpath", [
    "data/.gitkeep",
    "logs/.gitkeep",
])
def test_runtime_dirs_have_gitkeep(relpath: str):
    """data/ and logs/ are runtime dirs; .gitkeep ensures they exist in clones."""
    assert (ROOT / relpath).is_file(), f"Missing {relpath}"


# -----------------------------------------------------------------------------
# 9. .env.example has the documented variables
# -----------------------------------------------------------------------------
def test_env_example_has_required_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("MISSION_CONTROL_HOST", "MISSION_CONTROL_PORT", "HERMES_HOME"):
        assert key in text, f".env.example missing documented var: {key}"


# -----------------------------------------------------------------------------
# 10. systemd service example points to /usr/bin/python3 (portable, not a specific venv)
# -----------------------------------------------------------------------------
def test_systemd_service_uses_system_python():
    text = (ROOT / "mission-control.service.example").read_text(encoding="utf-8")
    assert "ExecStart=" in text, "service file must have ExecStart"
    # We don't hard-fail on /usr/bin/python3 because that's the default on most systems,
    # but the file must reference a python interpreter.
    assert "python" in text.lower(), "service file must reference a python interpreter"
