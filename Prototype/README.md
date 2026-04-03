# Top-down arena (physics puck game)

A small Godot **4.6** game: you and a monster are **friction pucks** on a mint **safe** platform surrounded by a red **void**. Knock the monster into the void while staying safe yourself.

---

## How to open and run

1. Install **[Godot 4.6](https://godotengine.org/download)** (this project targets `config/features` **4.6**).
2. In Godot: **Import** or **Scan**, then open this folder’s **`project.godot`**.
3. Press **F5** (or **Project → Run Project**).  
   The entry scene is **`game/main_menu.tscn`** (`run/main_scene` in `project.godot`).

No extra build steps. On first open, the editor may re-import `icon.webp` and rebuild `.godot` cache.

---

## How to play

### Goal

- **Win:** The monster ends up in the **void** (red danger `Area2D` strips), you are **not** in the void, and the round **settles** (both bodies nearly stopped). Your **score** is the number of **input rounds** (each successful submit counts once).
- **Lose:** Your puck touches the void — you lose **even if** the monster is also in the void.
- **Retry:** Use **Retry** on the end screen; it reloads the whole scene.

### Controls and UI

- Read the laws on the **main menu**, then **START** to enter the arena.
- Left panel (**560 px** wide): stats, distance to monster, bearing, and the **next monster jolt** preview.
- Enter **angle** (degrees) and **acceleration** `a` (m/s²):
  - **0°** = push to the right, **90°** = up on the screen, etc.
- Press **Enter** in either **Angle** or **Accel** line to **submit** one move (both fields are read together).
- Each submit applies your push and the **pre-announced** monster jolt, then rolls a **new** preview for the *following* turn.

### What you see

- **Mint** area: safe platform (aligned with walls / backdrop).
- **Red** edge: void — **RigidBody2D** overlap with those areas is used for win/lose (see technical section).

The player and monster are simple scaled squares (textures are created in code in `topdown_player.gd` / `monster.gd`).

---

## Project layout (where things live)

| Path | Role |
|------|------|
| `project.godot` | Engine config; `run/main_scene` = `game/main_menu.tscn`; 2D gravity **0**; 120 Hz physics |
| `game/main_menu.tscn` + `main_menu.gd` | Laws + **START** → loads arena |
| `game/topdown_arena.tscn` + `topdown_arena.gd` | Arena, walls, void zones, camera, win/lose logic, monster jolt pipeline |
| `game/topdown_player.tscn` + `topdown_player.gd` | Player `RigidBody2D`, friction integrate, `apply_acceleration` |
| `game/monster.tscn` + `monster.gd` | Monster `RigidBody2D`, friction + **max speed** cap |
| `game/number_input_hud.tscn` + `number_input_hud.gd` | Left UI, `push_command_submitted` signal |
| `game/game_over_ui.tscn` + `game_over_ui.gd` | Pause + win/lose text + **Retry** |

---

## Technical overview

### Units and scale

- **`PIXELS_PER_METER = 100`** in arena and puck scripts: **1 m = 100 px** for HUD distances and for turning **m/s²** into engine velocity changes.
- Speed in Godot is **pixels per second**; labels convert positions with `/ 100` where needed.

### Top-down “floor friction” (no gravity)

Both pucks use **`_integrate_forces`** to emulate sliding friction with constant deceleration magnitude **`FRICTION_DECEL_MPS2 = 5` m/s²**:

Each physics step, with current speed `|v|` and step `Δt`:

- Decrement applied in speed: `Δ|v| = 5 × 100 × Δt` (px/s) until rest.

This matches a kinematic “braking” model along the velocity direction, not `linear_damp`.

### One “push”: fixed-duration acceleration impulse

Your input and the monster jolt both use the same **pulse duration** **`PUSH_DURATION_S = ACCEL_COMMAND_DURATION_S = 0.25` s**.

For acceleration command **a** (m/s²) and direction **û** (unit vector from angle **θ**):

\[
\Delta \mathbf{v} = \hat{u} \cdot a \cdot (0.25\ \text{s}) \cdot 100\ \text{(px/s per m/s)}
\]

In code (`topdown_player.gd` / `_on_push_command` on the monster):

```text
linear_velocity += dir * acceleration_m_s2 * 0.25 * 100.0
```

**Direction from angle** (0° = +X, 90° = up = −Y on screen):

\[
\hat{u} = (\cos\theta,\ -\sin\theta)
\]

**Bearing** (HUD) from player to monster uses `atan2(-Δy, Δx)` for the same convention.

### Collisions and momentum (engine vs your code)

- **Your GDScript** does **not** implement puck–puck or puck–wall collisions by hand: no explicit **p = mv**, no **`apply_impulse`** for those contacts, and no **μN** friction model on impact.
- **Godot’s `RigidBody2D` solver** still resolves overlaps using **contact impulses**. Conceptually each body gets **Δv** from an impulse so that **Δp = mΔv** (with rotation locked here, it’s mainly linear). The solver also enforces **separating** motion and **equal-and-opposite** impulses between the two bodies (**Newton’s third law**), and your **`PhysicsMaterial`** **bounce** values add **restitution** (partially elastic bumps).
- So collisions **do** use the usual **impulse–momentum** picture — **inside the engine** — while your **custom** physics is only the **floor braking** in `_integrate_forces` and the **velocity kick** **Δv = a·Δt** for inputs/jolts.

**Masses** in the scenes: **`70`** kg (player) / **`55`** kg (monster).

### Monster max speed

After friction integration, velocity is clamped so **`|v| ≤ 20` m/s** (`monster.gd`, `MAX_SPEED_MPS`), so jolts + impacts do not exceed that cap.

---

## Randomness (monster jolt)

Implemented in **`topdown_arena.gd`**.

1. **Uniform random direction** on the circle:  
   `Vector2.from_angle(randf_range(0.0, TAU)).normalized()`
2. **Uniform random acceleration** in **[5, 20] m/s²**:  
   `randf_range(MONSTER_JOLT_ACCEL_MIN_MPS2, MONSTER_JOLT_ACCEL_MAX_MPS2)`
3. **Rejection sampling (up to 48 tries):**  
   A candidate jolt is **discarded** if a simple prediction says the monster would **skid to a stop outside** the mint safe rectangle (with margin).  
   The test uses:
   - post-jolt velocity **`v₁`** (current velocity + jolt, then **capped** at 20 m/s),
   - straight-line **stopping distance** under the same friction model (see below),
   - stop position = position + **`v̂₁` × stopping distance**; must lie inside the padded safe rect.
4. **Fallback** if all random tries fail: jolt **toward the center** of the safe rect with minimum **`a`**; if still “bad”, **`a = 0`** for that preview.

The **next** jolt is rolled **after** your move is applied (`_on_push_command`), and the HUD always shows what will apply **on the next Enter**.

### Stopping distance used in rejection (technical)

With speed **`s = |v₁|`** (px/s) and **`a_px = FRICTION_DECEL_MPS2 × PIXELS_PER_METER`** (px/s² for deceleration magnitude):

\[
d_{\text{stop}} = \frac{s^2}{2 a_{\text{px}}}
\]

(This is `v²/(2a)` for braking to zero; **walls/bounces are not simulated** in this preview.)

---

## Win/lose resolution (why it waits)

In **`topdown_arena.gd` → `_physics_process`:**

- **Void test:** `Area2D.overlaps_body` on each child of **`DangerZones`** (`collision_mask` includes player + monster layers).
- When **either** body touches void, a **pending resolution** phase starts.
- **Every frame while pending:** if the **player** overlaps void → **lose** (takes priority over win).
- **Win** only if: monster in void, **player not** in void, and both speeds **< `REST_SPEED_PX` (10 px/s)** so the outcome isn’t decided mid-scramble.
- If **neither** is in void and both are resting → **cancel** pending (e.g. monster bounced back).
- **Timeout `RESOLVE_TIMEOUT_S` (20 s):** lose if player in void; else win if monster still in void; else cancel.

Input rounds are counted in **`_on_push_command`** (`_inputs_used++`) and passed to **`game_over_ui.gd` → `show_result(true, score)`** on win.

---

## Optional tweaks

All main tuning constants live at the **top** of:

- `topdown_arena.gd` — jolt ranges, safe rect, rest speed, resolve timeout  
- `topdown_player.gd` / `monster.gd` — friction, pulse duration (player), max speed (monster)  
- `number_input_hud.gd` — `ACCEL_COMMAND_DURATION_S` should stay equal to arena/player **0.25** if you change it  

`project.godot` still has legacy **InputMap** entries (`jump`, `move_*`) from the old demo; this top-down mode does not use them for gameplay.

---

## Appendix: complete physics inventory

Checklist of **everything** that affects motion, collision, or outcomes. Values are as in the repo unless noted.

### 1. Engine (`project.godot`)

| Setting | Value | Effect |
|--------|--------|--------|
| `2d/default_gravity` | `0` | No global gravity. |
| `common/physics_ticks_per_second` | `120` | Physics step rate (Hz). |
| `common/physics_interpolation` | `true` | Smoother display between physics states. |

### 2. Arena static geometry (`topdown_arena.tscn`)

| Body | Type | `collision_layer` | `collision_mask` | Shape / notes |
|------|------|-------------------|------------------|----------------|
| WallTop | `StaticBody2D` | **1** | *(not set in file; Godot default)* | `RectangleShape2D` **1060×28**, center `(530, 14)` |
| WallBottom | `StaticBody2D` | **1** | same | **1060×28**, `(530, 976)` |
| WallLeft | `StaticBody2D` | **1** | same | **28×990**, `(14, 495)` |
| WallRight | `StaticBody2D` | **1** | same | **28×990**, `(1046, 495)` |

Walls have **no** `PhysicsMaterial` in the scene (engine defaults for friction/bounce on the static side of contacts).

### 3. Void detection (`topdown_arena.tscn`)

`Area2D` nodes **`DangerTop` / `DangerBottom` / `DangerLeft` / `DangerRight`** (under `DangerZones`):

| Property | Value |
|----------|--------|
| `collision_mask` | **3** (binary `11` → layers **1** and **2**) |
| `monitoring` | `true` |
| `monitorable` | `false` |

Rough world sizes (shape size + node position): **top/bottom** strips **1060×144**; **left/right** **176×702**. Used only for **overlap queries** (`overlaps_body`); they are **not** solid colliders.

**Backdrop** (`Polygon2D` under `WorldBackdrop`) is **visual only** (no `CollisionShape2D`).

### 4. Player puck (`topdown_player.tscn` + `topdown_player.gd`)

| Property / constant | Value |
|---------------------|--------|
| Type | `RigidBody2D`, group **`player`** |
| `collision_layer` | **2** |
| `collision_mask` | **1** |
| `mass` | **70** kg |
| `gravity_scale` | **0** |
| `lock_rotation` | `true` |
| `linear_damp` / `angular_damp` | **0** (custom friction in code instead) |
| `can_sleep` | `false` |
| `PhysicsMaterial` | `bounce = **0.06**` (friction not set → default) |
| Collision | `RectangleShape2D` **36×36** px |
| Sprite scale | **2.5** (visual only) |

**Script physics (`_integrate_forces`):** each step, speed magnitude reduced by **`FRICTION_DECEL_MPS2 × PIXELS_PER_METER × step`** with **`FRICTION_DECEL_MPS2 = 5`** and **`PIXELS_PER_METER = 100`**, along current direction, until speed ~0.

**`apply_acceleration`:** adds **`linear_velocity += û × a × 0.25 × 100`** with **`ACCEL_COMMAND_DURATION_S = 0.25`**, **`û = (cos θ, −sin θ)`**.

### 5. Monster puck (`monster.tscn` + `monster.gd`)

| Property / constant | Value |
|---------------------|--------|
| Type | `RigidBody2D`, group **`monster`** |
| `collision_layer` | **1** |
| `collision_mask` | **3** (layers **1** and **2** → walls + player) |
| `mass` | **55** kg |
| `gravity_scale` | **0** |
| `lock_rotation` | `true` |
| `linear_damp` / `angular_damp` | **0** |
| `can_sleep` | `false` |
| `PhysicsMaterial` | `bounce = **0.08**` |
| Collision | `RectangleShape2D` **34×40** px |
| Sprite scale | **2.3** (visual; `modulate` for color) |

**Same friction integrator** as player (**5 m/s²** decel, **100 px/m**).

**After friction step:** speed clamped to **`MAX_SPEED_MPS = 20`** m/s (in px/s: ×100).

### 6. Arena controller (`topdown_arena.gd`) — extra physics-related logic

| Symbol | Value | Role |
|--------|--------|------|
| `PIXELS_PER_METER` | 100 | HUD + impulse scaling. |
| `PUSH_DURATION_S` | 0.25 | Monster jolt pulse (matches player). |
| `MONSTER_JOLT_ACCEL_*` | 5 … 20 m/s² | Uniform draw for jolt **a**. |
| `MONSTER_MAX_SPEED_MPS` | 20 | Matches monster script cap; used in jolt **simulation**. |
| Safe rect + `MONSTER_SAFE_MARGIN_PX` | core **176–884**, **144–846**; margin **26** | Jolt **rejection** test only. |
| `JOLT_ROLL_MAX_ATTEMPTS` | 48 | Max random jolt retries. |
| `REST_SPEED_PX` | 10 | “At rest” for win / cancel (~0.1 m/s). |
| `RESOLVE_TIMEOUT_S` | 20 | Win/lose resolution timeout. |

**On each submitted push:** monster gets **`linear_velocity += jolt_dir × a_monster × 0.25 × 100`** (same pattern as player).

**Jolt preview math:** post-jolt speed → stopping distance **`s² / (2 × 5 × 100)`** px — compare stop position to padded safe rectangle.

**Player–monster / puck–wall contact:** handled entirely by **`RigidBody2D`** (masses **70 / 55**, bounces **0.06 / 0.08**); **no** custom `apply_impulse` in scripts — the engine applies **contact impulses** (impulse–momentum / **Δp = mΔv** internally). See **“Collisions and momentum”** above.

### 7. What is *not* customized

- No `CharacterBody2D`, no `Area2D` on pucks for movement.
- No `custom_integrator` / `CENTER_OF_MASS_MODE_CUSTOM`.
- No `continuous_cd` override on bodies (engine default).
- No per-step `apply_central_impulse` for the player move — only **`linear_velocity +=`** for the command pulse.

This list should match the code; if you change a constant, update **both** the script and this section if you keep docs in sync.
