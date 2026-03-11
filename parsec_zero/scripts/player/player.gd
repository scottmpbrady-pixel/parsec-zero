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
var _hud: Node = null
var _invincible_timer: float = 0.0

func _ready() -> void:
	add_to_group("player")
	_hud = get_tree().get_first_node_in_group("hud")

func _physics_process(delta: float) -> void:
	_invincible_timer = max(0.0, _invincible_timer - delta)
	var input_vector := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	velocity = input_vector * SPEED
	move_and_slide()

func take_damage(amount: int) -> void:
	if _invincible_timer > 0.0:
		return
	hp -= amount
	_invincible_timer = 0.8
	if _hud and _hud.has_method("set_hp"):
		_hud.set_hp(hp, MAX_HP)
	if hp <= 0:
		get_tree().reload_current_scene()
