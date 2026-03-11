"""
Git automation tools for CrewAI agents.

Branch strategy:
  - Developer commits to feature branches (e.g. feature/level-1-movement)
  - Project Manager merges to main after QA passes
  - Successful builds are tagged (e.g. v0.1.0-level1-complete)
  - Agents NEVER write directly to main
"""
import os
import subprocess
from pathlib import Path

from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(os.getenv("GODOT_PROJECT_PATH", "parsec_zero")).parent
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "Parsec Zero Studio Bot")
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "bot@parsec-zero.local")


def _git(*args: str) -> tuple[int, str]:
    """Run a git command and return (returncode, output)."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = GIT_AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = GIT_AUTHOR_EMAIL
    env["GIT_COMMITTER_NAME"] = GIT_AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = GIT_AUTHOR_EMAIL

    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


@tool("Create a new git feature branch")
def git_create_feature_branch(branch_name: str) -> str:
    """
    Create and switch to a new feature branch.
    Branch names should follow the convention: feature/<short-description>
    Example: feature/level-1-movement, feature/plasma-rifle

    Args:
        branch_name: Branch name (e.g. "feature/level-1-movement")

    Returns confirmation or error.
    """
    if not branch_name.startswith("feature/"):
        return "ERROR: Branch name must start with 'feature/'. Example: feature/level-1-movement"

    rc, out = _git("checkout", "-b", branch_name)
    if rc == 0:
        return f"OK: Created and switched to branch '{branch_name}'."
    # Branch may already exist — try switching to it
    rc2, out2 = _git("checkout", branch_name)
    if rc2 == 0:
        return f"OK: Switched to existing branch '{branch_name}'."
    return f"ERROR: {out}\n{out2}"


@tool("Stage and commit changes to current feature branch")
def git_commit_feature(message: str, files: list[str]) -> str:
    """
    Stage specific files and commit them to the current branch.
    Never commits directly to main — that is the Project Manager's job.

    Args:
        message: Commit message describing the change
        files: List of file paths relative to the repo root to stage

    Returns confirmation with commit hash or error.
    """
    current_branch_rc, current_branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if current_branch.strip() == "main":
        return (
            "BLOCKED: Cannot commit directly to main. "
            "Create a feature branch first with git_create_feature_branch."
        )

    # Stage specific files
    for f in files:
        rc, out = _git("add", f)
        if rc != 0:
            return f"ERROR staging '{f}': {out}"

    rc, out = _git("commit", "-m", message)
    if rc != 0:
        return f"ERROR committing: {out}"

    return f"OK: Committed to '{current_branch.strip()}'. {out}"


@tool("Show git diff of staged changes")
def git_diff_staged() -> str:
    """
    Return the git diff of currently staged changes.
    The QA agent reads this before approving a commit to catch semantic errors
    (wrong variable names, missing signals, spec mismatches) before a build runs.

    Returns the diff text.
    """
    rc, out = _git("diff", "--cached")
    if not out:
        return "No staged changes."
    return out[:8000]  # Cap output to avoid context overflow


@tool("Tag a successful build")
def git_tag_build(tag: str, message: str) -> str:
    """
    Create an annotated git tag on the current commit marking a successful build.
    Use after a level passes QA and the .exe exports successfully.
    Tag format: v<major>.<minor>.<patch>-<description>
    Example: v0.1.0-level1-complete

    Args:
        tag: Tag name (e.g. "v0.1.0-level1-complete")
        message: Description of what this build includes

    Returns confirmation or error.
    """
    rc, out = _git("tag", "-a", tag, "-m", message)
    if rc != 0:
        return f"ERROR tagging: {out}"
    return f"OK: Tagged current commit as '{tag}'. Push with: git push origin {tag}"


@tool("Merge feature branch to main")
def git_merge_to_main(feature_branch: str) -> str:
    """
    Merge a feature branch into main after QA approval.
    ONLY the Project Manager agent should call this tool.

    Args:
        feature_branch: The branch to merge (e.g. "feature/level-1-movement")

    Returns confirmation or error.
    """
    # Switch to main
    rc, out = _git("checkout", "main")
    if rc != 0:
        return f"ERROR switching to main: {out}"

    # Merge the feature branch (no-ff to preserve history)
    rc, out = _git("merge", "--no-ff", feature_branch, "-m", f"Merge {feature_branch} into main [QA approved]")
    if rc != 0:
        return f"ERROR merging '{feature_branch}': {out}"

    return f"OK: Merged '{feature_branch}' into main."
