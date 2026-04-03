extends CanvasLayer

@onready var _title: Label = %Title
@onready var _message: Label = %Message
@onready var _restart_button: Button = %RestartButton


func _ready() -> void:
	hide()
	_restart_button.pressed.connect(_on_restart_pressed)


func show_game_over() -> void:
	show_result(false, 0)


## `input_rounds` is how many angle/acceleration submits were used (score on win).
func show_result(won: bool, input_rounds: int = 0) -> void:
	get_tree().paused = true
	if won:
		_title.text = "You win!"
		var s_suffix := ""
		if input_rounds != 1:
			s_suffix = "s"
		_message.text = (
			"Score: %d input round%s to knock the monster into the void.\n"
			+ "You stayed on the safe platform."
		) % [input_rounds, s_suffix]
	else:
		_title.text = "Game Over"
		_message.text = (
			"You fell into the danger zone.\n"
			+ "If the monster is in the void too, you still lose when you are not safe."
		)
	show()
	_restart_button.grab_focus()


func _on_restart_pressed() -> void:
	get_tree().paused = false
	hide()
	get_tree().reload_current_scene()
