## player.gd
## Parsec Zero — Player controller
##
## Node type: CharacterBody2D
## WASD / arrow key movement with collision.
## Exposes take_damage() for enemies to call.

extends CharacterBody2D

const SPEED: float = 200.0
const MAX_HP: int = 5

var hp: int = MAX_HP
var _invincible_timer: float = 0.0

func _ready() -> void:
	add_to_group("player")

func _physics_process(delta: float) -> void:
	_invincible_timer = max(0.0, _invincible_timer - delta)
	var input_vector := Vector2.ZERO
	if Input.is_action_pressed("ui_up"):
		input_vector.y -= 1
	if Input.is_action_pressed("ui_down"):
		input_vector.y += 1
	if Input.is_action_pressed("ui_left"):
		input_vector.x -= 1
	if Input.is_action_pressed("ui_right"):
		input_vector.x += 1
	if input_vector != Vector2.ZERO:
		input_vector = input_vector.normalized()
	velocity = input_vector * SPEED
	move_and_slide()

func take_damage(amount: int) -> void:
	if _invincible_timer > 0.0:
		return
	hp -= amount
	_invincible_timer = 0.8
	var hud := get_tree().get_first_node_in_group("hud")
	if hud and hud.has_method("set_hp"):
		hud.set_hp(hp, MAX_HP)
	if hp <= 0:
		get_tree().reload_current_scene()
