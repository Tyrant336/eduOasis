extends CanvasLayer

## Keep in sync with `topdown_player.gd` ACCEL_COMMAND_DURATION_S.
const ACCEL_COMMAND_DURATION_S := 0.25

signal push_command_submitted(acceleration_m_s2: float, angle_degrees: float)

@onready var _distance_label: Label = %DistanceLabel
@onready var _bearing_label: Label = %BearingLabel
@onready var _next_jolt_label: Label = %NextJoltLabel
@onready var _compact_stats_label: Label = %CompactStatsLabel
@onready var _angle_line: LineEdit = %AngleLine
@onready var _accel_line: LineEdit = %AccelLine
@onready var _applied_label: Label = %AppliedLabel


func _ready() -> void:
	_apply_panel_and_text_contrast()
	_accel_line.text_submitted.connect(_on_accel_submitted)
	_accel_line.text_changed.connect(_on_accel_line_changed)
	_angle_line.text_submitted.connect(_on_angle_submitted)
	_angle_line.text_changed.connect(_on_angle_line_changed)


func _apply_panel_and_text_contrast() -> void:
	var panel_sb := StyleBoxFlat.new()
	panel_sb.bg_color = Color(0.12, 0.16, 0.14, 0.98)
	panel_sb.set_border_width_all(1)
	panel_sb.border_color = Color(0.28, 0.35, 0.3, 1)
	var panel_root := $LeftDock/Panel as PanelContainer
	panel_root.add_theme_stylebox_override(&"panel", panel_sb)

	var le_sb := StyleBoxFlat.new()
	le_sb.bg_color = Color(0.22, 0.28, 0.25, 1)
	le_sb.set_border_width_all(1)
	le_sb.border_color = Color(0.35, 0.42, 0.38, 1)
	for le: LineEdit in [_angle_line, _accel_line]:
		le.add_theme_stylebox_override(&"normal", le_sb)
		le.add_theme_stylebox_override(&"focus", le_sb)
		le.add_theme_color_override(&"font_color", Color(0.96, 1, 0.98, 1))
		le.add_theme_color_override(&"font_placeholder_color", Color(0.55, 0.62, 0.58, 1))
		le.add_theme_color_override(&"caret_color", Color(0.85, 0.98, 0.9, 1))

	_apply_label_colors_light($LeftDock)


func _apply_label_colors_light(n: Node) -> void:
	for c in n.get_children():
		if c is Label:
			(c as Label).add_theme_color_override(&"font_color", Color(0.9, 0.96, 0.92, 1))
		_apply_label_colors_light(c)


func setup_readouts(
	arena_width_m: float,
	arena_height_m: float,
	friction_mps2: float,
	player_mass_kg: float,
	monster_mass_kg: float,
) -> void:
	_compact_stats_label.text = (
		"Arena: %.1f×%.1f m  •  Friction: %.0f m/s²  •  Masses: %.0f kg / %.0f kg (you / monster)"
		% [arena_width_m, arena_height_m, friction_mps2, player_mass_kg, monster_mass_kg]
	)


func set_distance_m(distance_m: float) -> void:
	_distance_label.text = "Distance to monster: %.2f m" % distance_m


func set_bearing_to_monster_deg(angle_deg: float) -> void:
	_bearing_label.text = "Angle to monster (bearing): %.1f°  (0°=right, 90°=up)" % angle_deg


func set_next_monster_jolt(angle_deg: float, accel_mps2: float) -> void:
	_next_jolt_label.text = (
		"Monster next jolt (after you press Enter):  angle %.1f°  •  a = %.2f m/s²"
		% [angle_deg, accel_mps2]
	)


func _on_accel_line_changed(new_text: String) -> void:
	_apply_numeric_filter(new_text, _accel_line)


func _on_angle_line_changed(new_text: String) -> void:
	_apply_numeric_filter(new_text, _angle_line)


func _apply_numeric_filter(new_text: String, which: LineEdit) -> void:
	var filtered := _filter_float_string(new_text)
	if filtered == new_text:
		return
	which.set_block_signals(true)
	which.text = filtered
	which.set_block_signals(false)


func _filter_float_string(s: String) -> String:
	if s.is_empty():
		return ""
	var res := ""
	var i := 0
	if s[0] == "-":
		res = "-"
		i = 1
	var seen_dot := false
	while i < s.length():
		var ch: String = s.substr(i, 1)
		if ch == ".":
			if not seen_dot:
				res += "."
				seen_dot = true
		elif ch.is_valid_int():
			res += ch
		i += 1
	return res


func _angle_deg_from_field() -> float:
	var t := _angle_line.text.strip_edges()
	if t.is_valid_float():
		return t.to_float()
	return 0.0


func _try_emit_push() -> void:
	var ta := _accel_line.text.strip_edges()
	if not ta.is_valid_float():
		_applied_label.text = "Enter a valid acceleration (m/s²), then Enter."
		return
	var a := ta.to_float()
	var ang := _angle_deg_from_field()
	_applied_label.text = (
		"Last push:  a = %.3g m/s²,  θ = %.1f°"
		% [a, ang]
	)
	push_command_submitted.emit(a, ang)


func _on_accel_submitted(_text: String) -> void:
	_try_emit_push()
	_accel_line.release_focus()


func _on_angle_submitted(_text: String) -> void:
	_try_emit_push()
	_angle_line.release_focus()
