"""
Agent 1 — Systems Designer

Responsibilities:
  - Define all game mechanics, level progression, enemy stats, lore
  - Output structured JSON or Markdown specifications
  - Embed all specs into ChromaDB so other agents can query them
  - Maintain game_bible.json as the single source of truth
  - Never contradict a decision already embedded in ChromaDB

LLM: Claude Sonnet 4.6 (best at structured JSON + consistent lore generation)
"""
import json
import os
from pathlib import Path

from crewai import Agent
from crewai.tools import tool
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from tools.chromadb_tools import embed_design_document, query_design_memory

load_dotenv()

GAME_BIBLE_PATH = Path(os.getenv("GODOT_PROJECT_PATH", "parsec_zero")).parent / "game_bible.json"

# ── LLM ──────────────────────────────────────────────────────────────────────
sonnet = ChatAnthropic(
    model="claude-sonnet-4-6",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=8192,
)


# ── Designer-specific tools ──────────────────────────────────────────────────
@tool("Read game bible")
def read_game_bible() -> str:
    """
    Read the current game_bible.json — the single source of truth for all
    Parsec Zero mechanics, stats, and lore. Always read this before writing
    any new specification to avoid contradictions.

    Returns the game bible as a formatted JSON string.
    """
    if not GAME_BIBLE_PATH.exists():
        return "ERROR: game_bible.json not found."
    return GAME_BIBLE_PATH.read_text(encoding="utf-8")


@tool("Update game bible")
def update_game_bible(section: str, key: str, value: str) -> str:
    """
    Update a single value in game_bible.json.
    Use this to lock in a decision (e.g. player HP, enemy speed).
    The Project Manager will flag conflicts with existing values.

    Args:
        section: Top-level section (e.g. "player", "levels", "enemies")
        key: Key within the section (e.g. "hp", "speed")
        value: JSON-encoded value (e.g. "5", '"fast"', '{"x": 400, "y": 300}')

    Returns confirmation or error.
    """
    if not GAME_BIBLE_PATH.exists():
        return "ERROR: game_bible.json not found."

    bible = json.loads(GAME_BIBLE_PATH.read_text())

    if section not in bible:
        bible[section] = {}

    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value  # treat as plain string

    bible[section][key] = parsed_value
    GAME_BIBLE_PATH.write_text(json.dumps(bible, indent=2))
    return f"OK: Updated game_bible.json [{section}][{key}] = {parsed_value}"


# ── Agent definition ─────────────────────────────────────────────────────────
systems_designer_agent = Agent(
    role="Systems Designer",
    goal=(
        "Design the complete game mechanics, level layouts, enemy stats, and lore for Parsec Zero. "
        "Produce structured JSON specifications that the Lead Developer can implement directly. "
        "Always check ChromaDB memory and game_bible.json before making any design decision to ensure consistency."
    ),
    backstory=(
        "You are a veteran game designer specializing in sci-fi action-adventure games. "
        "You have shipped 12 titles and have a reputation for airtight design documents that "
        "developers can implement without asking follow-up questions. "
        "You think in systems: every mechanic must have a clear number, every stat must have a reason. "
        "You treat game_bible.json as law — you never contradict a decision already written there. "
        "Parsec Zero is your current project: a pixel art space station survival game. "
        "Phase 1 goal: playable Level 1 with WASD movement and room collision."
    ),
    tools=[
        read_game_bible,
        update_game_bible,
        embed_design_document,
        query_design_memory,
    ],
    llm=sonnet,
    verbose=True,
    max_iter=5,
    allow_delegation=False,
)
