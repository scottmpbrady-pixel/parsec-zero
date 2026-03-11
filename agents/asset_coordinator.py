"""
Agent 3 — Asset Coordinator

Responsibilities:
  - Generate pixel art sprites via Stable Diffusion (local Automatic1111)
  - Generate background music via Suno API
  - Generate SFX via ElevenLabs
  - Save all files to res://assets/ and maintain manifest.json
  - Pass exact file paths to the Developer via the manifest

LLM: Claude Haiku 4.5 — only writes SD prompts and manages file I/O; cheap and fast.
"""
import os

from crewai import Agent
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from tools.asset_tools import (
    generate_sprite,
    generate_music,
    generate_sfx,
    read_asset_manifest,
    update_asset_manifest,
)
from tools.chromadb_tools import query_design_memory

load_dotenv()

haiku = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4096,
)

asset_coordinator_agent = Agent(
    role="Asset Coordinator",
    goal=(
        "Generate all pixel art sprites, background music, and sound effects for Parsec Zero. "
        "Save every asset to its correct res://assets/ subdirectory and keep manifest.json current "
        "so the Lead Developer can wire assets into scenes without hunting for file paths."
    ),
    backstory=(
        "You are a technical art director who specializes in pixel art for indie games. "
        "You know that all Parsec Zero art must follow the style: "
        "'pixel art, 32x32, sci-fi space station, dark palette, neon accents'. "
        "You always prepend this style prefix to every Stable Diffusion prompt you write. "
        "You never invent new characters or props that the Systems Designer hasn't approved — "
        "you query ChromaDB first to check what assets are needed. "
        "Your deliverables are file paths in manifest.json, not opinions."
    ),
    tools=[
        query_design_memory,
        generate_sprite,
        generate_music,
        generate_sfx,
        read_asset_manifest,
        update_asset_manifest,
    ],
    llm=haiku,
    verbose=True,
    max_iter=8,
    allow_delegation=False,
)
