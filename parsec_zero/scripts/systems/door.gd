## door.gd
## Parsec Zero — Scene transition door
##
## Node type: Area2D
## When the player walks into the Area2D, loads the target scene.
## @export target_scene: path to the next level scene.

extends Area2D

@export var target_scene: String = ""

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node) -> void:
	if body.is_in_group("player") and target_scene != "":
		get_tree().change_scene_to_file(target_scene)
