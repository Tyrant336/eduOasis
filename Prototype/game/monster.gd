extends RigidBody2D

## Same scale and floor friction as player (100 px = 1 m).
const PIXELS_PER_METER := 100.0
const FRICTION_DECEL_MPS2 := 5.0
## Cap top speed so jolts + collisions cannot exceed this (m/s in HUD terms).
const MAX_SPEED_MPS := 20.0


func _ready() -> void:
	gravity_scale = 0.0
	lock_rotation = true
	linear_damp = 0.0
	can_sleep = false
	var img := Image.create(8, 8, false, Image.FORMAT_RGBA8)
	img.fill(Color.WHITE)
	$Sprite2D.texture = ImageTexture.create_from_image(img)


func _integrate_forces(state: PhysicsDirectBodyState2D) -> void:
	var v := state.linear_velocity
	var sp := v.length()
	if sp < 0.0001:
		return
	var decel := FRICTION_DECEL_MPS2 * PIXELS_PER_METER * state.step
	if decel >= sp:
		state.linear_velocity = Vector2.ZERO
		return
	v = v.normalized() * (sp - decel)
	var cap_px := MAX_SPEED_MPS * PIXELS_PER_METER
	if v.length_squared() > cap_px * cap_px:
		state.linear_velocity = v.normalized() * cap_px
	else:
		state.linear_velocity = v
