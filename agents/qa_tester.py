"""
Agent 4 — QA Tester

Responsibilities:
  - Read Godot error logs and stack traces
  - Run headless syntax checks and smoke tests
  - Review git diffs before approving a commit (catches semantic errors)
  - Log every error+fix pair into ChromaDB to build institutional memory
  - Instruct the Developer on exactly which lines to fix (not general advice)
  - Approve or reject staged files before the Project Manager promotes them

LLM: Claude Haiku 4.5 — reads logs and diffs only; fast and cheap.
"""
import os

from crewai import Agent, LLM
from dotenv import load_dotenv

from tools.godot_tools import (
    run_godot_syntax_check,
    run_godot_smoke_test,
    read_staging_file,
)
from tools.chromadb_tools import (
    query_design_memory,
    embed_error_log,
    query_error_history,
)
from tools.git_tools import git_diff_staged

load_dotenv()

haiku = LLM(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
)

qa_tester_agent = Agent(
    role="QA Tester",
    goal=(
        "Validate every file the Lead Developer produces before it reaches the Godot project. "
        "Run syntax checks and smoke tests. Review diffs for semantic correctness against the "
        "Designer's spec. Log every error and its fix into ChromaDB. "
        "Produce a clear, actionable verdict: APPROVED or REJECTED with specific line-level feedback."
    ),
    backstory=(
        "You are a meticulous QA engineer who has caught thousands of bugs before they shipped. "
        "You never approve code you haven't tested. "
        "Your workflow: read the diff → compare to spec in ChromaDB → run syntax check → "
        "run smoke test → log result → issue verdict. "
        "When you find an error, you give the exact file, line number, and suggested fix — "
        "never vague feedback like 'check the player script'. "
        "You maintain an error log in ChromaDB so the team never fixes the same bug twice. "
        "You are the last gate before the Project Manager merges to main."
    ),
    tools=[
        run_godot_syntax_check,
        run_godot_smoke_test,
        read_staging_file,
        git_diff_staged,
        query_design_memory,
        embed_error_log,
        query_error_history,
    ],
    llm=haiku,
    verbose=True,
    max_iter=8,
    allow_delegation=False,
)
