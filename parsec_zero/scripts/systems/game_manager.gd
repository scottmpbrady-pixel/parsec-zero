## game_manager.gd
## Parsec Zero — Game Manager (Phase 1 stub)
##
## Node type: Node
## Attached to the root of each level scene.
## Phase 1: minimal — just confirms the level is running.
## Later phases: tracks HP, score, save state, scene transitions.

extends Node

func _ready() -> void:
	print("[GameManager] Level loaded: ", get_tree().current_scene.name)
