"""
Godot CLI tools for CrewAI agents.

Wraps headless Godot commands and staging file I/O.
The QA agent and Developer agent use these tools.
"""
import os
import shutil
import subprocess
from pathlib import Path

from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

GODOT_EXE = os.getenv("GODOT_EXECUTABLE", "godot")
PROJECT_PATH = Path(os.getenv("GODOT_PROJECT_PATH", "parsec_zero"))
STAGING_DIR = PROJECT_PATH / "agents_staging"


def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


@tool("Run Godot syntax check")
def run_godot_syntax_check(target_script: str = "") -> str:
    """
    Run `godot --headless --check-only` on the project to validate GDScript syntax.
    Pass an optional relative path to check a single script file, or leave empty
    to check the entire project.

    Returns a JSON-style summary: {"status": "ok"|"error", "output": "...", "errors": [...]}
    """
    cmd = [GODOT_EXE, "--headless", "--check-only", "--path", str(PROJECT_PATH)]
    if target_script:
        cmd += [target_script]

    returncode, stdout, stderr = _run(cmd)
    combined = stdout + stderr
    errors = [line for line in combined.splitlines() if "ERROR" in line or "error" in line.lower()]

    if returncode == 0 and not errors:
        return f'{{"status": "ok", "output": {repr(combined)}, "errors": []}}'
    else:
        return f'{{"status": "error", "returncode": {returncode}, "output": {repr(combined)}, "errors": {errors}}}'


@tool("Run Godot headless smoke test")
def run_godot_smoke_test() -> str:
    """
    Run `godot --headless` with the smoke test scene (res://tests/smoke_test.tscn).
    The smoke test scene spawns the player and runs for 3 seconds, then quits.
    A zero exit code means the test passed.

    Returns a JSON-style summary with pass/fail status and output.
    """
    cmd = [
        GODOT_EXE,
        "--headless",
        "--path", str(PROJECT_PATH),
        "res://tests/smoke_test.tscn",
    ]
    returncode, stdout, stderr = _run(cmd, timeout=30)
    combined = stdout + stderr
    passed = returncode == 0 and "SMOKE TEST: PASSED" in combined

    return (
        f'{{"status": "{"passed" if passed else "failed"}", '
        f'"returncode": {returncode}, '
        f'"output": {repr(combined)}}}'
    )


@tool("Export Godot project")
def run_godot_export(preset: str = "Windows Desktop") -> str:
    """
    Export the Godot project using the named export preset.
    Common presets: "Windows Desktop", "HTML5".
    The compiled build is placed in parsec_zero/exports/.

    Returns a JSON-style summary with success/failure.
    """
    export_path = PROJECT_PATH / "exports" / "parsec_zero.exe"
    cmd = [
        GODOT_EXE,
        "--headless",
        "--path", str(PROJECT_PATH),
        "--export-release", preset,
        str(export_path),
    ]
    returncode, stdout, stderr = _run(cmd, timeout=300)
    combined = stdout + stderr
    success = returncode == 0 and export_path.exists()

    return (
        f'{{"status": "{"ok" if success else "error"}", '
        f'"export_path": "{export_path}", '
        f'"returncode": {returncode}, '
        f'"output": {repr(combined)}}}'
    )


@tool("Read file from agents staging area")
def read_staging_file(relative_path: str) -> str:
    """
    Read a file from the agents_staging/ directory.
    Agents write here first; the Project Manager promotes approved files.

    Args:
        relative_path: Path relative to agents_staging/ (e.g. "scripts/player/player.gd")

    Returns the file contents as a string, or an error message.
    """
    full_path = STAGING_DIR / relative_path
    if not full_path.exists():
        return f"ERROR: File not found in staging: {full_path}"
    return full_path.read_text(encoding="utf-8")


@tool("Write file to agents staging area")
def write_staging_file(relative_path: str, content: str) -> str:
    """
    Write a file to the agents_staging/ directory.
    No agent may write directly to scenes/ or scripts/ — use this tool instead.
    The Project Manager will move files to their final location after QA approval.

    Args:
        relative_path: Path relative to agents_staging/ (e.g. "scripts/player/player.gd")
        content: The file content to write.

    Returns a confirmation message or error.
    """
    full_path = STAGING_DIR / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return f"OK: Written to staging: {full_path}"


@tool("Promote staged file to final location")
def promote_from_staging(relative_path: str) -> str:
    """
    Move a file from agents_staging/ to its final location in the Godot project.
    Only the Project Manager agent should call this tool after QA approval.

    Args:
        relative_path: Path relative to agents_staging/ AND the project root.
                       Example: "scripts/player/player.gd" moves from
                       agents_staging/scripts/player/player.gd
                       to parsec_zero/scripts/player/player.gd

    Returns confirmation or error.
    """
    src = STAGING_DIR / relative_path
    dst = PROJECT_PATH / relative_path

    if not src.exists():
        return f"ERROR: Staged file not found: {src}"

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    src.unlink()
    return f"OK: Promoted {relative_path} → {dst}"
