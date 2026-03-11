"""
Parsec Zero — Shared tools for CrewAI agents.
"""
from tools.godot_tools import (
    run_godot_syntax_check,
    run_godot_smoke_test,
    run_godot_export,
    read_staging_file,
    write_staging_file,
    promote_from_staging,
)
from tools.chromadb_tools import (
    embed_design_document,
    query_design_memory,
    embed_error_log,
    query_error_history,
)
from tools.asset_tools import (
    generate_sprite,
    generate_music,
    generate_sfx,
    update_asset_manifest,
    read_asset_manifest,
)
from tools.git_tools import (
    git_commit_feature,
    git_create_feature_branch,
    git_diff_staged,
    git_tag_build,
)

__all__ = [
    "run_godot_syntax_check",
    "run_godot_smoke_test",
    "run_godot_export",
    "read_staging_file",
    "write_staging_file",
    "promote_from_staging",
    "embed_design_document",
    "query_design_memory",
    "embed_error_log",
    "query_error_history",
    "generate_sprite",
    "generate_music",
    "generate_sfx",
    "update_asset_manifest",
    "read_asset_manifest",
    "git_commit_feature",
    "git_create_feature_branch",
    "git_diff_staged",
    "git_tag_build",
]
