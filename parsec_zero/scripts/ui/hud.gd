## hud.gd
## Parsec Zero — HUD controller
##
## Displays:
##   - HP bar (top left)
##   - Level name (top centre)
##
## Usage: call hud.set_hp(current, max) from game_manager when HP changes.

extends CanvasLayer

@onready var hp_bar: ProgressBar = $HPBar
@onready var level_label: Label = $LevelLabel

func _ready() -> void:
	set_hp(5, 5)
	set_level_name("Reactor Deck — Entry")

func set_hp(current: int, max_hp: int) -> void:
	hp_bar.max_value = max_hp
	hp_bar.value = current

func set_level_name(name: String) -> void:
	level_label.text = name
