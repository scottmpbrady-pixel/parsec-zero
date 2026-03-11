## enemy_base.gd
## Parsec Zero — Base enemy controller (Phase 3)
##
## Behaviour: simple left-right patrol between two points.
## Chases player when within detection range.
## Deals 1 HP damage on contact.

extends CharacterBody2D

enum State { PATROL, CHASE }

@export var patrol_distance: float = 120.0
@export var patrol_speed: float = 60.0
@export var chase_speed: float = 110.0
@export var detection_range: float = 160.0
@export var damage: int = 1
@export var hp: int = 3

var _state: State = State.PATROL
var _patrol_origin: Vector2
var _patrol_target: Vector2
var _player: Node2D = null
var _damage_cooldown: float = 0.0

func _ready() -> void:
	_patrol_origin = global_position
	_patrol_target = _patrol_origin + Vector2(patrol_distance, 0)

func _physics_process(delta: float) -> void:
	_damage_cooldown = max(0.0, _damage_cooldown - delta)

	# Lazy lookup — player may not be in group during _ready()
	if _player == null:
		_player = get_tree().get_first_node_in_group("player")

	match _state:
		State.PATROL:
			_do_patrol(delta)
			if _player and global_position.distance_to(_player.global_position) <= detection_range:
				_state = State.CHASE
		State.CHASE:
			_do_chase(delta)
			if not _player or global_position.distance_to(_player.global_position) > detection_range * 1.5:
				_state = State.PATROL

func _do_patrol(_delta: float) -> void:
	var direction := (_patrol_target - global_position).normalized()
	velocity = direction * patrol_speed
	move_and_slide()

	if global_position.distance_to(_patrol_target) < 4.0:
		# Swap patrol endpoints
		var temp := _patrol_origin
		_patrol_origin = _patrol_target
		_patrol_target = temp

func _do_chase(_delta: float) -> void:
	if not _player:
		return
	var direction := (_player.global_position - global_position).normalized()
	velocity = direction * chase_speed
	move_and_slide()

	# Damage on contact
	if _damage_cooldown <= 0.0 and global_position.distance_to(_player.global_position) < 48.0:
		if _player.has_method("take_damage"):
			_player.take_damage(damage)
			_damage_cooldown = 1.0

func take_damage(amount: int) -> void:
	hp -= amount
	if hp <= 0:
		queue_free()
