"""
Parsec Zero — Main Orchestrator

Entry point for the automated game studio. Manages:
  - Phased crew execution (Phase 1 → 2 → ... → 6)
  - Retry logic with cooldown (max 5 retries, 30s between)
  - Daily API budget enforcement with 50% and 90% alerts
  - Token usage logging (every API call logged to logs/tokens.jsonl)
  - Human checkpoints after each completed level

Usage:
    python orchestrator.py                     # Run Phase 1 (default)
    python orchestrator.py --phase 1           # Explicit phase
    python orchestrator.py --dry-run           # Validate config, don't run agents
    python orchestrator.py --status            # Print STATUS.md and exit
"""
import json
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import click
import structlog
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
TOKEN_LOG_PATH = Path(os.getenv("TOKEN_LOG_PATH", "logs/tokens.jsonl"))
BUDGET_LOG_PATH = LOG_DIR / "budget.json"

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()
console = Console()

# ── Config ────────────────────────────────────────────────────────────────────
MAX_RETRIES = int(os.getenv("MAX_RETRIES_PER_TASK", "5"))
RETRY_COOLDOWN = int(os.getenv("RETRY_COOLDOWN_SECONDS", "30"))
DAILY_BUDGET = float(os.getenv("DAILY_API_BUDGET_USD", "10.00"))
HUMAN_CHECKPOINT = os.getenv("HUMAN_CHECKPOINT_ENABLED", "true").lower() == "true"
STATUS_PATH = Path("STATUS.md")

# Anthropic pricing (per 1M tokens, as of 2026)
PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
}


# ─────────────────────────────────────────────────────────────────────────────
# Budget tracking
# ─────────────────────────────────────────────────────────────────────────────

def _load_budget_state() -> dict:
    today = str(date.today())
    if BUDGET_LOG_PATH.exists():
        state = json.loads(BUDGET_LOG_PATH.read_text())
        if state.get("date") == today:
            return state
    # New day — reset
    return {"date": today, "spent_usd": 0.0, "calls": 0, "alert_50_sent": False, "alert_90_sent": False}


def _save_budget_state(state: dict) -> None:
    BUDGET_LOG_PATH.write_text(json.dumps(state, indent=2))


def log_token_usage(model: str, input_tokens: int, output_tokens: int, task: str) -> None:
    """Log one API call and update daily budget. Raises if budget exceeded."""
    pricing = PRICING.get(model, {"input": 5.0, "output": 15.0})
    cost = (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])

    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "task": task,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }
    TOKEN_LOG_PATH.parent.mkdir(exist_ok=True)
    with TOKEN_LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    state = _load_budget_state()
    state["spent_usd"] = round(state["spent_usd"] + cost, 6)
    state["calls"] += 1

    pct = state["spent_usd"] / DAILY_BUDGET * 100

    if pct >= 50 and not state["alert_50_sent"]:
        console.print(Panel(
            f"[yellow]⚠️  API BUDGET ALERT: {pct:.0f}% used (${state['spent_usd']:.2f} / ${DAILY_BUDGET:.2f})[/yellow]",
            title="Budget Warning",
        ))
        state["alert_50_sent"] = True

    if pct >= 90 and not state["alert_90_sent"]:
        console.print(Panel(
            f"[bold red]🚨 API BUDGET CRITICAL: {pct:.0f}% used (${state['spent_usd']:.2f} / ${DAILY_BUDGET:.2f})[/bold red]",
            title="Budget Critical",
        ))
        state["alert_90_sent"] = True

    if state["spent_usd"] >= DAILY_BUDGET:
        _save_budget_state(state)
        raise RuntimeError(
            f"DAILY API BUDGET EXCEEDED: ${state['spent_usd']:.2f} / ${DAILY_BUDGET:.2f}. "
            "System paused. Set a higher DAILY_API_BUDGET_USD in .env to continue."
        )

    _save_budget_state(state)
    logger.debug("token_usage", **entry)


# ─────────────────────────────────────────────────────────────────────────────
# Retry wrapper
# ─────────────────────────────────────────────────────────────────────────────

def run_with_retry(fn, task_name: str, max_retries: int = MAX_RETRIES) -> any:
    """
    Run fn() with up to max_retries attempts and RETRY_COOLDOWN seconds between tries.
    On final failure, raises the last exception.
    """
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("task_attempt", task=task_name, attempt=attempt, max=max_retries)
            result = fn()
            logger.info("task_success", task=task_name, attempt=attempt)
            return result
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "task_failed",
                task=task_name,
                attempt=attempt,
                error=str(exc),
                cooldown_seconds=RETRY_COOLDOWN,
            )
            if attempt < max_retries:
                console.print(
                    f"[yellow]Retry {attempt}/{max_retries} for '{task_name}'. "
                    f"Waiting {RETRY_COOLDOWN}s...[/yellow]"
                )
                time.sleep(RETRY_COOLDOWN)

    raise RuntimeError(
        f"Task '{task_name}' failed after {max_retries} attempts. "
        f"Last error: {last_exc}"
    ) from last_exc


# ─────────────────────────────────────────────────────────────────────────────
# Human checkpoint
# ─────────────────────────────────────────────────────────────────────────────

def human_checkpoint(phase: int, description: str) -> bool:
    """
    Pause and ask for human approval before continuing.
    Returns True if approved, False if rejected.
    Only active when HUMAN_CHECKPOINT_ENABLED=true.
    """
    if not HUMAN_CHECKPOINT:
        return True

    console.print(Panel(
        f"[bold cyan]HUMAN CHECKPOINT — Phase {phase} complete[/bold cyan]\n\n"
        f"{description}\n\n"
        "Review STATUS.md and the exports/ directory before approving.\n"
        "Type [bold]yes[/bold] to continue to the next phase, [bold]no[/bold] to stop.",
        title="Approval Required",
    ))

    while True:
        answer = input("Approve? (yes/no): ").strip().lower()
        if answer in ("yes", "y"):
            logger.info("human_checkpoint_approved", phase=phase)
            return True
        elif answer in ("no", "n"):
            logger.info("human_checkpoint_rejected", phase=phase)
            return False
        print("Please type 'yes' or 'no'.")


# ─────────────────────────────────────────────────────────────────────────────
# Phase runners
# ─────────────────────────────────────────────────────────────────────────────

def run_phase_1() -> dict:
    """Phase 1: Project scaffold → Level 1 design → assets → code → QA → merge."""
    from crew import build_phase_1_crew

    console.print(Panel(
        "[bold green]Phase 1 — Level 1: Player movement + room collision[/bold green]\n"
        "Agents: Systems Designer → Asset Coordinator → Lead Developer → QA Tester → Project Manager",
        title="Parsec Zero Studio",
    ))

    crew = build_phase_1_crew()

    def _run():
        return crew.kickoff(inputs={
            "game_title": "Parsec Zero",
            "phase": 1,
            "seed_prompt": (
                "Design, build, and validate Level 1 of Parsec Zero: "
                "a single room of a derelict space station with WASD player movement and wall collision. "
                "Pixel art, 32x32 sprites, sci-fi theme. "
                "Phase 1 definition of done: smoke test passes, .exe exports successfully."
            ),
        })

    result = run_with_retry(_run, task_name="Phase 1 crew kickoff")
    return {"phase": 1, "result": str(result), "status": "complete"}


def run_phase_5_marketing(commit_message: str, screenshot_path: str = "") -> None:
    """Phase 5: Trigger n8n marketing webhook after a successful build commit."""
    import requests

    n8n_url = os.getenv("N8N_WEBHOOK_URL", "")
    if not n8n_url:
        logger.warning("n8n_skipped", reason="N8N_WEBHOOK_URL not set in .env")
        return

    payload = {
        "event": "build_complete",
        "commit_message": commit_message,
        "screenshot_path": screenshot_path,
        "timestamp": datetime.now().isoformat(),
        "game": "Parsec Zero",
    }

    try:
        resp = requests.post(n8n_url, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("n8n_webhook_triggered", status=resp.status_code)
    except Exception as e:
        logger.warning("n8n_webhook_failed", error=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_config() -> list[str]:
    """Check required environment variables. Returns list of missing items."""
    required = [
        ("ANTHROPIC_API_KEY", "Anthropic API key"),
        ("GODOT_EXECUTABLE", "Path to Godot executable"),
        ("GODOT_PROJECT_PATH", "Path to Godot project"),
    ]
    optional_warned = [
        ("SUNO_API_KEY", "Music generation (Phase 4)"),
        ("ELEVENLABS_API_KEY", "SFX generation (Phase 4)"),
        ("N8N_WEBHOOK_URL", "Marketing automation (Phase 5)"),
        ("GITHUB_TOKEN", "GitHub push (Phase 3+)"),
    ]

    missing = []
    for key, desc in required:
        if not os.getenv(key):
            missing.append(f"MISSING (required): {key} — {desc}")

    for key, desc in optional_warned:
        if not os.getenv(key):
            console.print(f"[dim]  ℹ  {key} not set — {desc} disabled[/dim]")

    return missing


def print_budget_status() -> None:
    state = _load_budget_state()
    table = Table(title="Daily API Budget")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Date", state["date"])
    table.add_row("Spent", f"${state['spent_usd']:.4f}")
    table.add_row("Budget", f"${DAILY_BUDGET:.2f}")
    table.add_row("Remaining", f"${max(0, DAILY_BUDGET - state['spent_usd']):.4f}")
    table.add_row("API calls today", str(state["calls"]))
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--phase", default=1, type=int, help="Which phase to run (1–6). Default: 1.")
@click.option("--dry-run", is_flag=True, help="Validate config only — don't run agents.")
@click.option("--status", is_flag=True, help="Print STATUS.md and budget, then exit.")
@click.option("--budget", is_flag=True, help="Print current budget usage and exit.")
def main(phase: int, dry_run: bool, status: bool, budget: bool) -> None:
    """Parsec Zero — Automated AI Game Studio Orchestrator."""

    if status:
        if STATUS_PATH.exists():
            console.print(STATUS_PATH.read_text())
        else:
            console.print("[yellow]STATUS.md not found.[/yellow]")
        print_budget_status()
        return

    if budget:
        print_budget_status()
        return

    console.print(Panel(
        "[bold]Parsec Zero — Automated Game Studio[/bold]\n"
        "Validating configuration...",
        title="Startup",
    ))

    missing = validate_config()
    if missing:
        console.print("[bold red]Configuration errors:[/bold red]")
        for m in missing:
            console.print(f"  [red]✗ {m}[/red]")
        console.print("\nCopy .env.example to .env and fill in the required values.")
        sys.exit(1)

    console.print("[green]✓ Configuration valid[/green]")

    if dry_run:
        console.print("[cyan]Dry run complete — no agents were started.[/cyan]")
        return

    # ── Run the requested phase ───────────────────────────────────────────────
    phase_runners = {
        1: run_phase_1,
    }

    if phase not in phase_runners:
        console.print(f"[red]Phase {phase} not yet implemented. Available: {list(phase_runners.keys())}[/red]")
        sys.exit(1)

    try:
        result = phase_runners[phase]()
        console.print(Panel(
            f"[bold green]Phase {phase} complete![/bold green]\n\n"
            f"Result: {result.get('status', 'unknown')}",
            title="Done",
        ))

        # Human checkpoint before moving to next phase
        if result.get("status") == "complete":
            approved = human_checkpoint(
                phase=phase,
                description=(
                    "Level 1 is built. Review the exports/ directory for the .exe, "
                    "check STATUS.md for the full activity log, and verify the game runs correctly."
                ),
            )
            if approved:
                console.print(f"[green]Phase {phase} approved. Run with --phase {phase + 1} to continue.[/green]")
            else:
                console.print(f"[yellow]Phase {phase} rejected. Fix issues and re-run.[/yellow]")

        # Trigger marketing webhook if Phase 4+ is done
        if phase >= 4:
            run_phase_5_marketing(
                commit_message=f"Phase {phase} complete",
                screenshot_path="",
            )

    except RuntimeError as e:
        console.print(Panel(f"[bold red]{e}[/bold red]", title="Fatal Error"))
        logger.error("orchestrator_fatal", error=str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
