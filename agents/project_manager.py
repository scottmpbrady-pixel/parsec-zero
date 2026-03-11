"""
Agent 5 — Project Manager

Responsibilities:
  - Track task state across sessions via STATUS.md
  - Decide when to escalate to human (after max_retries exceeded)
  - Maintain game_bible.json as single source of truth
  - Promote QA-approved files from staging to final locations
  - Merge feature branches to main after QA passes
  - Tag successful builds
  - Write progress summaries to STATUS.md after each milestone

LLM: Claude Sonnet 4.6 — needs context retention and cross-session reasoning.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from crewai import Agent, LLM
from crewai.tools import tool
from dotenv import load_dotenv

from tools.godot_tools import promote_from_staging
from tools.chromadb_tools import query_design_memory, embed_design_document
from tools.git_tools import git_merge_to_main, git_tag_build

load_dotenv()

PROJECT_ROOT = Path(os.getenv("GODOT_PROJECT_PATH", "parsec_zero")).parent
STATUS_PATH = PROJECT_ROOT / "STATUS.md"
GAME_BIBLE_PATH = PROJECT_ROOT / "game_bible.json"

sonnet = LLM(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
)


# ── PM-specific tools ─────────────────────────────────────────────────────────
@tool("Read project status")
def read_status() -> str:
    """
    Read the current STATUS.md — the project's living progress document.
    Always read this at the start of each session to understand current state.

    Returns the full STATUS.md content.
    """
    if not STATUS_PATH.exists():
        return "STATUS.md not found."
    return STATUS_PATH.read_text(encoding="utf-8")


@tool("Append entry to project status log")
def append_status_log(agent_name: str, task_description: str, result: str) -> str:
    """
    Append a new entry to the activity log table in STATUS.md.

    Args:
        agent_name: Name of the agent that completed the task
        task_description: Brief description of what was done
        result: "Completed", "Failed", "Blocked", or short note

    Returns confirmation.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = f"| {timestamp} | {agent_name} | {task_description} | {result} |"

    content = STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists() else ""
    # Insert after the table header
    if "| Timestamp |" in content:
        # Find the separator line and insert after it
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("| ---") and i > 0 and "Timestamp" in lines[i - 1]:
                lines.insert(i + 1, new_row)
                break
        content = "\n".join(lines)
    else:
        content += f"\n{new_row}"

    STATUS_PATH.write_text(content, encoding="utf-8")
    return f"OK: Status log updated."


@tool("Update phase checklist item in STATUS.md")
def update_checklist_item(item_text: str, completed: bool) -> str:
    """
    Mark a checklist item in STATUS.md as complete or incomplete.

    Args:
        item_text: The exact text of the checklist item (without the [ ] or [x])
        completed: True to mark as [x], False to mark as [ ]

    Returns confirmation.
    """
    content = STATUS_PATH.read_text(encoding="utf-8")
    old_unchecked = f"- [ ] {item_text}"
    old_checked = f"- [x] {item_text}"
    new = f"- [x] {item_text}" if completed else f"- [ ] {item_text}"

    if old_unchecked in content:
        content = content.replace(old_unchecked, new)
    elif old_checked in content:
        content = content.replace(old_checked, new)
    else:
        return f"WARNING: Checklist item not found: '{item_text}'"

    STATUS_PATH.write_text(content, encoding="utf-8")
    return f"OK: Checklist item '{'[x]' if completed else '[ ]'} {item_text}' updated."


@tool("Read game bible for cross-session consistency check")
def pm_read_game_bible() -> str:
    """
    Read game_bible.json to check for contradictions before approving any agent output.
    The Project Manager must verify that new content doesn't conflict with existing decisions.

    Returns the game bible as JSON.
    """
    if not GAME_BIBLE_PATH.exists():
        return "ERROR: game_bible.json not found."
    return GAME_BIBLE_PATH.read_text(encoding="utf-8")


@tool("Flag issue for human review")
def escalate_to_human(issue: str, context: str, retries_exhausted: int) -> str:
    """
    Write a human-escalation notice to STATUS.md and a separate ESCALATION.md file.
    Call this when an agent has exceeded max_retries and cannot resolve a problem.

    Args:
        issue: Short description of the problem
        context: Full context — what was attempted, what failed
        retries_exhausted: Number of retry attempts that were made

    Returns confirmation that the escalation was written.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    escalation_content = f"""# ⚠️ HUMAN REVIEW REQUIRED

**Time:** {timestamp}
**Retries exhausted:** {retries_exhausted}

## Issue
{issue}

## Context
{context}

## Next steps
1. Review the error in STATUS.md activity log
2. Check agents_staging/ for the problematic file
3. Resolve manually or adjust the Designer's spec
4. Delete this file and re-run the orchestrator
"""
    escalation_path = PROJECT_ROOT / "ESCALATION.md"
    escalation_path.write_text(escalation_content, encoding="utf-8")

    append_status_log("Project Manager", f"ESCALATED: {issue}", "Awaiting human review")

    return (
        f"ESCALATED: '{issue}' written to ESCALATION.md. "
        "System is paused. Human intervention required."
    )


# ── Agent definition ──────────────────────────────────────────────────────────
project_manager_agent = Agent(
    role="Project Manager",
    goal=(
        "Track all task state across sessions. Prevent contradictions. "
        "Approve QA-tested files and promote them from staging to the Godot project. "
        "Merge feature branches to main after QA passes. "
        "Escalate to human when agents are stuck. "
        "Keep STATUS.md and game_bible.json current at all times."
    ),
    backstory=(
        "You are a senior technical project manager who has shipped 20+ software products. "
        "You are the memory and conscience of the Parsec Zero studio. "
        "You read STATUS.md at the start of every session. You never approve work you haven't "
        "verified against the spec. "
        "Your branch rule is absolute: nothing reaches main without QA approval. "
        "When agents get stuck in retry loops, you escalate — you never let the system thrash "
        "indefinitely. You document everything in STATUS.md so the next session starts informed."
    ),
    tools=[
        read_status,
        append_status_log,
        update_checklist_item,
        pm_read_game_bible,
        escalate_to_human,
        promote_from_staging,
        git_merge_to_main,
        git_tag_build,
        query_design_memory,
        embed_design_document,
    ],
    llm=sonnet,
    verbose=True,
    max_iter=5,
    allow_delegation=False,
)
