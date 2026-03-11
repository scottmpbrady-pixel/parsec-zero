## smoke_test.gd
## Parsec Zero — Headless smoke test
##
## Run with:
##   godot --headless --path parsec_zero/ res://tests/smoke_test.tscn
##
## Exit code 0 = PASSED
## Exit code 1 = FAILED
##
## Checks:
##   1. Player scene loads without error
##   2. Player node is a CharacterBody2D
##   3. Player has the _physics_process method (script attached)
##   4. Player has a CollisionShape2D child
##   5. Runtime: no crashes after 3 seconds
##
## The QA agent runs this as the final validation gate.

extends Node

func _ready() -> void:
	print("[SMOKE TEST] Starting Parsec Zero smoke test...")

	# ── Test 1: Load player scene ─────────────────────────────────────────────
	var player_scene: PackedScene = load("res://scenes/entities/player.tscn")
	if player_scene == null:
		_fail("Cannot load res://scenes/entities/player.tscn")
		return

	var player: Node = player_scene.instantiate()
	add_child(player)
	print("[SMOKE TEST] ✓ player.tscn loaded and instantiated")

	# ── Test 2: Node type ─────────────────────────────────────────────────────
	if not player is CharacterBody2D:
		_fail("Player root node is not CharacterBody2D (got: %s)" % player.get_class())
		return
	print("[SMOKE TEST] ✓ Player is CharacterBody2D")

	# ── Test 3: Script attached ───────────────────────────────────────────────
	if not player.has_method("_physics_process"):
		_fail("Player script not attached or missing _physics_process")
		return
	print("[SMOKE TEST] ✓ Player script attached (_physics_process found)")

	# ── Test 4: Collision shape ───────────────────────────────────────────────
	var collision: Node = player.find_child("CollisionShape2D", true, false)
	if collision == null:
		_fail("Player has no CollisionShape2D child")
		return
	print("[SMOKE TEST] ✓ Player CollisionShape2D found")

	# ── Test 5: Runtime stability (3 seconds, no crash) ───────────────────────
	print("[SMOKE TEST] Running for 3 seconds to check for runtime errors...")
	await get_tree().create_timer(3.0).timeout

	print("[SMOKE TEST] ===========================")
	print("[SMOKE TEST] PASSED — All checks OK")
	print("[SMOKE TEST] ===========================")
	get_tree().quit(0)


func _fail(reason: String) -> void:
	push_error("[SMOKE TEST] FAILED: " + reason)
	print("[SMOKE TEST] ===========================")
	print("[SMOKE TEST] FAILED: " + reason)
	print("[SMOKE TEST] ===========================")
	get_tree().quit(1)
