## player.gd
## Parsec Zero — Player controller (Phase 1)
##
## Node type: CharacterBody2D
## Handles WASD / arrow key movement with collision.
## No combat, no animation states yet — movement only.
##
## Stats (from game_bible.json):
##   SPEED = 200.0
##   HP    = 5  (tracked by game_manager in later phases)

extends CharacterBody2D

const SPEED: float = 200.0

## Called every physics frame. Reads input and moves the player.
func _physics_process(_delta: float) -> void:
	var direction := Vector2.ZERO

	direction.x = Input.get_axis("ui_left", "ui_right")
	direction.y = Input.get_axis("ui_up", "ui_down")

	if direction != Vector2.ZERO:
		direction = direction.normalized()

	velocity = direction * SPEED
	move_and_slide()
