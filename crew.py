"""
Parsec Zero — CrewAI Crew Definition

Defines the crew with all 5 agents and the task pipeline for Phase 1.
The orchestrator imports and runs this crew.
"""
from crewai import Crew, Task, Process

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
        "Design the complete specification for Level 1 of Parsec Zero.\n\n"
        "Steps:\n"
        "1. Read game_bible.json to confirm current player stats and level 1 requirements.\n"
        "2. Query ChromaDB for any existing level_1 documents to avoid contradictions.\n"
        "3. Write a detailed JSON specification covering:\n"
        "   - Player: HP=5, SPEED=200.0, sprite=32x32, collision=28x28, controls (WASD + arrows)\n"
        "   - Level 1: 800x600 room, player spawn at (400, 300), 4 StaticBody2D walls, no enemies\n"
        "   - Scene structure: Level1 (Node2D) → Player (instance), Walls (StaticBody2D nodes)\n"
        "   - Pixel art style: 'pixel art, 32x32, sci-fi space station, dark palette, neon accents'\n"
        "4. Embed the spec into ChromaDB with doc_id='level_1_spec'.\n"
        "5. Update game_bible.json if any values differ from what's there.\n\n"
        "Output: A complete JSON spec document ready for the Developer to implement."
    ),
    expected_output=(
        "A JSON document containing the Level 1 spec with all player stats, room dimensions, "
        "wall positions, scene node hierarchy, and asset requirements. "
        "Confirmation that the spec is embedded in ChromaDB."
    ),
    agent=systems_designer_agent,
)

task_generate_assets = Task(
    description=(
        "Generate the pixel art assets needed for Level 1.\n\n"
        "Steps:\n"
        "1. Query ChromaDB for the level_1_spec to understand what assets are required.\n"
        "2. Generate a player sprite: asset_name='player_idle', "
        "description='humanoid maintenance drone, front-facing, standing idle, sci-fi suit'.\n"
        "3. Generate a space station floor/wall tileset: asset_name='station_tileset', "
        "description='sci-fi space station floor tile with metal grating and neon trim, seamless'.\n"
        "4. Generate ambient background music: track_name='level_1_ambient', "
        "description='dark ambient, sci-fi space station, tension, slow electronic pulse, 60bpm'.\n"
        "5. Read and return the updated asset manifest so the Developer knows all file paths.\n\n"
        "Note: All SD prompts must start with the style prefix from game_bible.json."
    ),
    expected_output=(
        "Confirmation that player_idle.png, station_tileset.png, and level_1_ambient.wav "
        "are saved to res://assets/. The full asset manifest JSON showing all file paths."
    ),
    agent=asset_coordinator_agent,
    context=[task_design_level_1],
)

task_develop_level_1 = Task(
    description=(
        "Implement Level 1 of Parsec Zero as Godot 4.x GDScript and .tscn files.\n\n"
        "Steps:\n"
        "1. Query ChromaDB for 'level_1_spec' to get the exact requirements.\n"
        "2. Read the asset manifest to get sprite and audio file paths.\n"
        "3. Create a feature branch: feature/level-1-movement.\n"
        "4. Write scripts/player/player.gd to agents_staging:\n"
        "   - Extends CharacterBody2D\n"
        "   - SPEED = 200.0\n"
        "   - _physics_process: read ui_up/down/left/right, normalize direction, move_and_slide()\n"
        "   - No enemies, no combat — movement only\n"
        "5. Write scripts/systems/game_manager.gd to agents_staging:\n"
        "   - Extends Node\n"
        "   - Minimal: just initializes the level, no complex state yet\n"
        "6. Write scenes/entities/player.tscn to agents_staging:\n"
        "   - CharacterBody2D root named 'Player'\n"
        "   - Attach player.gd script\n"
        "   - CollisionShape2D with RectangleShape2D(28, 28)\n"
        "   - Sprite2D (use player_idle.png from manifest if available)\n"
        "7. Write scenes/levels/level_1.tscn to agents_staging:\n"
        "   - Node2D root named 'Level1'\n"
        "   - Instance of player.tscn at position (400, 300)\n"
        "   - 4 StaticBody2D wall nodes (top, bottom, left, right) covering 800x600 room\n"
        "   - Each wall has a CollisionShape2D\n"
        "8. Run syntax check on all staged scripts.\n"
        "9. Commit staged files to feature/level-1-movement.\n\n"
        "IMPORTANT: Never write directly to scenes/ or scripts/ — always use write_staging_file."
    ),
    expected_output=(
        "Confirmation that player.gd, game_manager.gd, player.tscn, and level_1.tscn "
        "are written to agents_staging/ and the syntax check passed with zero errors. "
        "Commit hash on feature/level-1-movement branch."
    ),
    agent=lead_developer_agent,
    context=[task_design_level_1, task_generate_assets],
)

task_qa_review = Task(
    description=(
        "Review all staged files and run the headless smoke test. Issue a final APPROVED or REJECTED verdict.\n\n"
        "Steps:\n"
        "1. Query ChromaDB for 'level_1_spec' to know what the files should implement.\n"
        "2. Read each staged file (player.gd, game_manager.gd, player.tscn, level_1.tscn).\n"
        "3. Check the git diff of staged changes.\n"
        "4. Verify against spec:\n"
        "   - player.gd: SPEED == 200.0, uses CharacterBody2D, handles all 4 directions, calls move_and_slide()\n"
        "   - level_1.tscn: Player instance at (400, 300), 4 wall nodes with collision shapes\n"
        "   - No TODO comments, no placeholder values left in\n"
        "5. Query error history in case any current errors have known fixes.\n"
        "6. Run: run_godot_syntax_check() — must return status:ok.\n"
        "7. Run: run_godot_smoke_test() — must return status:passed.\n"
        "8. If any check fails: embed the error into ChromaDB with the suggested fix, "
        "return REJECTED with specific line-level feedback for the Developer.\n"
        "9. If all checks pass: return APPROVED with a summary of what was verified."
    ),
    expected_output=(
        "APPROVED or REJECTED verdict. "
        "If APPROVED: summary of what was verified (syntax clean, smoke test passed, spec compliant). "
        "If REJECTED: exact file paths, line numbers, and fixes required."
    ),
    agent=qa_tester_agent,
    context=[task_develop_level_1],
)

task_promote_and_merge = Task(
    description=(
        "After QA approval: promote staged files, merge the feature branch, and tag the build.\n\n"
        "Steps:\n"
        "1. Read STATUS.md to confirm current phase status.\n"
        "2. Read the QA verdict from context — only proceed if it contains 'APPROVED'.\n"
        "   If REJECTED: call escalate_to_human and stop.\n"
        "3. Promote each staged file to its final location:\n"
        "   - promote_from_staging('scripts/player/player.gd')\n"
        "   - promote_from_staging('scripts/systems/game_manager.gd')\n"
        "   - promote_from_staging('scenes/entities/player.tscn')\n"
        "   - promote_from_staging('scenes/levels/level_1.tscn')\n"
        "4. Merge feature/level-1-movement to main.\n"
        "5. Tag the build: v0.1.0-level1-complete\n"
        "   Tag message: 'Phase 1 complete: player movement + room collision, smoke test passed'\n"
        "6. Update STATUS.md: mark all Phase 1 checklist items as complete.\n"
        "7. Append to activity log: 'Project Manager | Phase 1 complete | v0.1.0-level1-complete'\n"
        "8. Embed a summary into ChromaDB: doc_id='phase_1_complete', "
        "title='Phase 1 Completion Summary'."
    ),
    expected_output=(
        "Confirmation that all 4 files are promoted from staging to the Godot project. "
        "Merge confirmation. Tag v0.1.0-level1-complete created. "
        "STATUS.md updated with all Phase 1 checklist items marked complete."
    ),
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
        max_rpm=10,    # Requests per minute — respects Anthropic rate limits
    )
