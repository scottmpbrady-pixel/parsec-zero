"""
Parsec Zero — CrewAI Crew Definition

Defines the crew with all 5 agents and the task pipeline for Phase 1.
The orchestrator imports and runs this crew.
"""
import os
import litellm
from crewai import Crew, Task, Process
from dotenv import load_dotenv

load_dotenv()

litellm.drop_params = True

from agents import (
    systems_designer_agent,
    lead_developer_agent,
    asset_coordinator_agent,
    qa_tester_agent,
    project_manager_agent,
)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 Tasks — Level 1: Player movement + room collision
# ─────────────────────────────────────────────────────────────────────────────

task_design_level_1 = Task(
    description=(
        "Read game_bible.json, then embed a Level 1 spec into ChromaDB (doc_id='level_1_spec').\n"
        "Spec must include: Player HP=5, SPEED=200.0, 32x32 sprite, 28x28 collision, WASD+arrow controls. "
        "Level 1: 800x600 room, player spawn (400,300), 4 StaticBody2D walls, no enemies. "
        "Art style: 'pixel art, 32x32, sci-fi space station, dark palette, neon accents'."
    ),
    expected_output="JSON spec embedded in ChromaDB with doc_id='level_1_spec'. game_bible.json updated.",
    agent=systems_designer_agent,
)

task_generate_assets = Task(
    description=(
        "Generate pixel art sprites for Level 1. Query ChromaDB for level_1_spec first.\n"
        "1. generate_sprite(asset_name='player_idle', description='humanoid maintenance drone, front-facing, sci-fi suit')\n"
        "2. generate_sprite(asset_name='station_tileset', description='sci-fi space station floor tile, metal grating, neon trim, seamless')\n"
        "3. Return the updated asset manifest."
    ),
    expected_output="player_idle.png and station_tileset.png saved to res://assets/sprites/. Asset manifest returned.",
    agent=asset_coordinator_agent,
    context=[task_design_level_1],
)

task_develop_level_1 = Task(
    description=(
        "Write Godot 4.x files to agents_staging/ only. Never write to scenes/ or scripts/ directly.\n"
        "1. Query ChromaDB for 'level_1_spec'. Read asset manifest.\n"
        "2. git_create_feature_branch('feature/level-1-movement')\n"
        "3. write_staging_file('scripts/player/player.gd'): CharacterBody2D, SPEED=200.0, WASD+arrow movement, move_and_slide()\n"
        "4. write_staging_file('scripts/systems/game_manager.gd'): extends Node, prints level name on _ready()\n"
        "5. write_staging_file('scenes/entities/player.tscn'): CharacterBody2D + CollisionShape2D(28x28) + Sprite2D, script=player.gd\n"
        "6. write_staging_file('scenes/levels/level_1.tscn'): Node2D + Player instance at (400,300) + 4 StaticBody2D walls. "
        "CRITICAL: shapes MUST use [sub_resource type='RectangleShape2D' id='unique_id'] blocks defined at the top of the file, then referenced as shape = SubResource('unique_id'). Never write shape = RectangleShape2D inline.\n"
        "7. run_godot_syntax_check()\n"
        "8. git_commit_feature('Add Level 1 player movement and room', ['parsec_zero/agents_staging/'])"
    ),
    expected_output="4 files in agents_staging/. Syntax check status:ok. Commit on feature/level-1-movement.",
    agent=lead_developer_agent,
    context=[task_design_level_1, task_generate_assets],
)

task_qa_review = Task(
    description=(
        "Validate staged files against spec and run tests. Return APPROVED or REJECTED.\n"
        "1. read_staging_file each of: scripts/player/player.gd, scripts/systems/game_manager.gd, "
        "scenes/entities/player.tscn, scenes/levels/level_1.tscn\n"
        "2. Verify: player.gd has SPEED=200.0, CharacterBody2D, move_and_slide(). "
        "level_1.tscn has Player at (400,300) and 4 wall StaticBody2D nodes. "
        "REJECT if level_1.tscn uses 'shape = RectangleShape2D' inline — shapes must use SubResource references.\n"
        "3. run_godot_syntax_check() — must be status:ok\n"
        "4. run_godot_smoke_test() — must be status:passed\n"
        "5. On any failure: embed_error_log() and return REJECTED with file/line/fix.\n"
        "6. On pass: return APPROVED."
    ),
    expected_output="APPROVED with verification summary, or REJECTED with specific file/line/fix details.",
    agent=qa_tester_agent,
    context=[task_develop_level_1],
)

task_promote_and_merge = Task(
    description=(
        "Only proceed if QA verdict is APPROVED. If REJECTED: escalate_to_human() and stop.\n"
        "1. promote_from_staging() for each: scripts/player/player.gd, scripts/systems/game_manager.gd, "
        "scenes/entities/player.tscn, scenes/levels/level_1.tscn\n"
        "2. git_merge_to_main('feature/level-1-movement')\n"
        "3. git_tag_build('v0.1.0-level1-complete', 'Phase 1: player movement + room collision')\n"
        "4. update_checklist_item() for all Phase 1 items\n"
        "5. append_status_log('Project Manager', 'Phase 1 complete', 'v0.1.0-level1-complete')"
    ),
    expected_output="4 files promoted. Merged to main. Tagged v0.1.0-level1-complete. STATUS.md updated.",
    agent=project_manager_agent,
    context=[task_qa_review],
)


# ─────────────────────────────────────────────────────────────────────────────
# Crew
# ─────────────────────────────────────────────────────────────────────────────

def build_phase_1_crew() -> Crew:
    """Build and return the Phase 1 CrewAI crew."""
    return Crew(
        agents=[
            systems_designer_agent,
            asset_coordinator_agent,
            lead_developer_agent,
            qa_tester_agent,
            project_manager_agent,
        ],
        tasks=[
            task_design_level_1,
            task_generate_assets,
            task_develop_level_1,
            task_qa_review,
            task_promote_and_merge,
        ],
        process=Process.sequential,
        verbose=True,
        memory=False,  # We use ChromaDB directly for cross-session memory
        max_rpm=5,    # Requests per minute — respects Anthropic rate limits
    )
