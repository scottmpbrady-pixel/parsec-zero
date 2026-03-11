extends CharacterBody2D

const SPEED = 200.0

func _ready() -> void:
	pass

func _physics_process(_delta: float) -> void:
	var input_vector = Vector2.ZERO
	
	# WASD input
	if Input.is_action_pressed("ui_up") or Input.is_key_pressed(KEY_W):
		input_vector.y -= 1
	if Input.is_action_pressed("ui_down") or Input.is_key_pressed(KEY_S):
		input_vector.y += 1
	if Input.is_action_pressed("ui_left") or Input.is_key_pressed(KEY_A):
		input_vector.x -= 1
	if Input.is_action_pressed("ui_right") or Input.is_key_pressed(KEY_D):
		input_vector.x += 1
	
	# Normalize diagonal movement
	if input_vector.length() > 0:
		input_vector = input_vector.normalized()
		velocity = input_vector * SPEED
	else:
		velocity = Vector2.ZERO
	
	move_and_slide()
