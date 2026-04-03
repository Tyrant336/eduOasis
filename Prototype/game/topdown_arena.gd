extends Node2D

## 1 world pixel = 1/PIXELS_PER_METER meters (for labels only; physics uses same units as pixels for speed).
const PIXELS_PER_METER := 100.0
## Inner playable rectangle inside the wall colliders (see wall positions in topdown_arena.tscn).
const INNER_ARENA_WIDTH_PX := 1004.0
const INNER_ARENA_HEIGHT_PX := 934.0
## Match `topdown_player.gd` (shown on HUD).
const FRICTION_DECEL_MPS2 := 5.0
## Same as player pulse duration (`topdown_player.gd` ACCEL_COMMAND_DURATION_S).
const PUSH_DURATION_S := 0.25
## Monster jolt: pre-rolled before each player move, shown on HUD then consumed when Enter is pressed.
## Random `a` (m/s²) for the monster jolt is in this range; Δv = a × PUSH_DURATION_S.
const MONSTER_JOLT_ACCEL_MIN_MPS2 := 5.0
const MONSTER_JOLT_ACCEL_MAX_MPS2 := 20.0
## Must match `monster.gd` MAX_SPEED_MPS (used when simulating jolt outcome).
const MONSTER_MAX_SPEED_MPS := 20.0
## Matches `WorldBackdrop/SafeCore` in topdown_arena.tscn, inset for monster collider size.
const SAFE_ZONE_LEFT := 176.0
const SAFE_ZONE_TOP := 144.0
const SAFE_ZONE_RIGHT := 884.0
const SAFE_ZONE_BOTTOM := 846.0
const MONSTER_SAFE_MARGIN_PX := 26.0
const JOLT_ROLL_MAX_ATTEMPTS := 48
## Wait for both pucks to slow down before calling a win (or a “bounced back” cancel).
const REST_SPEED_PX := 10.0
const RESOLVE_TIMEOUT_S := 20.0

@onready var _game_over_ui: CanvasLayer = $GameOverUI
@onready var _danger_pulse: Polygon2D = $WorldBackdrop/DangerBase
@onready var _hud: CanvasLayer = $NumberInputHud
@onready var _player: RigidBody2D = $TopdownPlayer
@onready var _monster: RigidBody2D = $Monster

var _next_jolt_dir: Vector2 = Vector2.RIGHT
var _next_jolt_accel_mps2: float = 0.0
var _inputs_used: int = 0
var _outcome_pending: bool = false
var _resolve_elapsed: float = 0.0
var _game_ended: bool = false


func _ready() -> void:
	_start_danger_pulse()

	var w_m := INNER_ARENA_WIDTH_PX / PIXELS_PER_METER
	var h_m := INNER_ARENA_HEIGHT_PX / PIXELS_PER_METER
	_hud.setup_readouts(
		w_m,
		h_m,
		FRICTION_DECEL_MPS2,
		_player.mass,
		_monster.mass,
	)
	_hud.push_command_submitted.connect(_on_push_command)
	_roll_next_monster_jolt_preview()
	_sync_jolt_preview_to_hud()


func _process(_delta: float) -> void:
	if _game_ended:
		return
	var d_m := _player.global_position.distance_to(_monster.global_position) / PIXELS_PER_METER
	_hud.set_distance_m(d_m)
	var to_monster := _monster.global_position - _player.global_position
	var bearing_deg := rad_to_deg(atan2(-to_monster.y, to_monster.x))
	_hud.set_bearing_to_monster_deg(bearing_deg)


func _physics_process(delta: float) -> void:
	if _game_ended:
		return

	var m_void := _body_in_void(_monster)
	var p_void := _body_in_void(_player)
	var resting := _pucks_fully_resting()

	if not _outcome_pending:
		if m_void or p_void:
			_outcome_pending = true
			_resolve_elapsed = 0.0
		else:
			return
	else:
		_resolve_elapsed += delta

	if _resolve_elapsed > RESOLVE_TIMEOUT_S:
		if p_void:
			_finalize_lose()
		elif m_void:
			_finalize_win()
		else:
			_outcome_pending = false
			_resolve_elapsed = 0.0
		return

	if p_void:
		_finalize_lose()
		return

	if m_void and resting:
		_finalize_win()
		return

	if not m_void and not p_void and resting:
		_outcome_pending = false
		_resolve_elapsed = 0.0


func _sync_jolt_preview_to_hud() -> void:
	var ang := rad_to_deg(atan2(-_next_jolt_dir.y, _next_jolt_dir.x))
	_hud.set_next_monster_jolt(ang, _next_jolt_accel_mps2)


func _roll_next_monster_jolt_preview() -> void:
	for _attempt in range(JOLT_ROLL_MAX_ATTEMPTS):
		var dir := Vector2.from_angle(randf_range(0.0, TAU)).normalized()
		var accel := randf_range(MONSTER_JOLT_ACCEL_MIN_MPS2, MONSTER_JOLT_ACCEL_MAX_MPS2)
		if not _monster_jolt_would_exit_safe_zone(dir, accel):
			_next_jolt_dir = dir
			_next_jolt_accel_mps2 = accel
			return
	var center := Vector2(
		(SAFE_ZONE_LEFT + SAFE_ZONE_RIGHT) * 0.5,
		(SAFE_ZONE_TOP + SAFE_ZONE_BOTTOM) * 0.5,
	)
	_next_jolt_dir = center - _monster.global_position
	if _next_jolt_dir.length_squared() < 0.0001:
		_next_jolt_dir = Vector2.RIGHT
	else:
		_next_jolt_dir = _next_jolt_dir.normalized()
	_next_jolt_accel_mps2 = MONSTER_JOLT_ACCEL_MIN_MPS2
	if _monster_jolt_would_exit_safe_zone(_next_jolt_dir, _next_jolt_accel_mps2):
		_next_jolt_accel_mps2 = 0.0


func _point_in_monster_safe_region(p: Vector2) -> bool:
	var ml := SAFE_ZONE_LEFT + MONSTER_SAFE_MARGIN_PX
	var mr := SAFE_ZONE_RIGHT - MONSTER_SAFE_MARGIN_PX
	var mt := SAFE_ZONE_TOP + MONSTER_SAFE_MARGIN_PX
	var mb := SAFE_ZONE_BOTTOM - MONSTER_SAFE_MARGIN_PX
	return p.x >= ml and p.x <= mr and p.y >= mt and p.y <= mb


func _monster_stopping_distance_px(vel_px: Vector2) -> float:
	var sp := vel_px.length()
	if sp < 0.0001:
		return 0.0
	var a_px := FRICTION_DECEL_MPS2 * PIXELS_PER_METER
	return (sp * sp) / (2.0 * a_px)


func _monster_velocity_after_jolt(dir: Vector2, accel_mps2: float) -> Vector2:
	var v := _monster.linear_velocity + dir * accel_mps2 * PUSH_DURATION_S * PIXELS_PER_METER
	var cap_px := MONSTER_MAX_SPEED_MPS * PIXELS_PER_METER
	if v.length_squared() > cap_px * cap_px:
		return v.normalized() * cap_px
	return v


## True if this jolt (given current monster motion) would skid to a stop outside the mint safe core.
func _monster_jolt_would_exit_safe_zone(dir: Vector2, accel_mps2: float) -> bool:
	var v1 := _monster_velocity_after_jolt(dir, accel_mps2)
	if v1.length_squared() < 1.0:
		return false
	var pos := _monster.global_position
	var dist := _monster_stopping_distance_px(v1)
	var stop_pos := pos + v1.normalized() * dist
	return not _point_in_monster_safe_region(stop_pos)


func _body_in_void(body: PhysicsBody2D) -> bool:
	for child in $DangerZones.get_children():
		if child is Area2D and child.overlaps_body(body):
			return true
	return false


func _pucks_fully_resting() -> bool:
	return (
		_player.linear_velocity.length() < REST_SPEED_PX
		and _monster.linear_velocity.length() < REST_SPEED_PX
	)


func _finalize_win() -> void:
	if _game_ended:
		return
	_game_ended = true
	_game_over_ui.show_result(true, _inputs_used)


func _finalize_lose() -> void:
	if _game_ended:
		return
	_game_ended = true
	_game_over_ui.show_result(false, _inputs_used)


func _on_push_command(accel_m_s2: float, angle_degrees: float) -> void:
	if _game_ended:
		return
	_inputs_used += 1
	_player.apply_acceleration(accel_m_s2, angle_degrees)
	_monster.linear_velocity += _next_jolt_dir * _next_jolt_accel_mps2 * PUSH_DURATION_S * PIXELS_PER_METER
	_roll_next_monster_jolt_preview()
	_sync_jolt_preview_to_hud()


func _start_danger_pulse() -> void:
	var tw := create_tween().set_loops()
	var hot := Color(1.18, 0.72, 0.72, 1)
	var base := Color(1, 1, 1, 1)
	tw.tween_property(_danger_pulse, "modulate", hot, 0.75)
	tw.tween_property(_danger_pulse, "modulate", base, 0.75)
