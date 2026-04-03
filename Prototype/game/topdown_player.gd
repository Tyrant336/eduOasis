extends RigidBody2D

## Same as arena: 100 px = 1 m so HUD speeds and distances match motion.
const PIXELS_PER_METER := 100.0
## Friction removes speed at this rate (m/s² in SI); applied in px/s² internally.
const FRICTION_DECEL_MPS2 := 5.0
## Δv (m/s) = acceleration (m/s²) × this time — scaled to px/s for the engine.
const ACCEL_COMMAND_DURATION_S := 0.25


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
	else:
		state.linear_velocity = v.normalized() * (sp - decel)


## Angle convention: 0° = right (+X), 90° = up on screen (−Y), 180° = left.
func apply_acceleration(acceleration_m_s2: float, angle_degrees: float) -> void:
	if acceleration_m_s2 == 0.0:
		return
	var rad := deg_to_rad(angle_degrees)
	var dir := Vector2(cos(rad), -sin(rad))
	linear_velocity += dir * acceleration_m_s2 * ACCEL_COMMAND_DURATION_S * PIXELS_PER_METER
