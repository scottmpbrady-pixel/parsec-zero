"""
Agent 2 — Lead Developer

Responsibilities:
  - Read the Designer's JSON specs and asset manifest
  - Write GDScript (.gd) and Godot scene files (.tscn)
  - All output goes to agents_staging/ first — never directly to scenes/ or scripts/
  - Use headless syntax check after every write
  - Commit to feature branches only

LLM: Claude Sonnet 4.6 (best at GDScript / code generation)
"""
import os

from crewai import Agent, LLM
from dotenv import load_dotenv

from tools.godot_tools import (
    run_godot_syntax_check,
    read_staging_file,
    write_staging_file,
)
from tools.chromadb_tools import query_design_memory
from tools.asset_tools import read_asset_manifest
from tools.git_tools import git_create_feature_branch, git_commit_feature, git_diff_staged

load_dotenv()

sonnet = LLM(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
)

lead_developer_agent = Agent(
    role="Lead Developer",
    goal=(
        "Implement the Systems Designer's specifications as working Godot 4.x GDScript files "
        "and .tscn scene files. All files go to agents_staging/ first. "
        "Run a syntax check after every file you write. "
        "Commit to a feature branch. Never touch main."
    ),
    backstory=(
        "You are a Godot 4.x expert who has shipped 8 games using GDScript. "
        "You write clean, idiomatic GDScript that follows Godot's node/signal patterns. "
        "You always query the design spec in ChromaDB before writing code so you never "
        "invent a mechanic the Designer didn't approve. "
        "Your workflow: read the spec → write the file to staging → syntax check → fix errors → commit. "
        "You know Parsec Zero is a 2D pixel art game on a space station. "
        "Phase 1 focus: CharacterBody2D player with WASD/arrow movement and wall collision."
    ),
    tools=[
        query_design_memory,
        read_asset_manifest,
        read_staging_file,
        write_staging_file,
        run_godot_syntax_check,
        git_create_feature_branch,
        git_commit_feature,
        git_diff_staged,
    ],
    llm=sonnet,
    verbose=True,
    max_iter=5,
    allow_delegation=False,
)
