# OMF2115 match state and presentation boundary (spike draft)

The source-driven replay and live views now follow OpenOMF combat ticks. This
contract records the state the 3D presentation layer receives and the events
still needed for complete match presentation. The fighting plane is horizontal `x`
plus jump height `y`; arena depth is visual only. Left and right inputs always
mean screen left and screen right, even after fighters cross.

## Per fixed combat tick

| Value | Owner | Presentation use |
| --- | --- | --- |
| Tick number and input actions for both players | Match simulation | Replay/debug overlay only |
| Fighter position, velocity, facing, health, guard, stun, and current move/animation frame | Match simulation | Place and animate 3D HARs; draw HUD |
| Hit, block, knockback, hazard, round, and result events | Match simulation | Effects, sound, camera cues, and transitions |
| Camera position, mesh pose, lighting, particles, and screen effects | Presentation | Display only; never determine hit or movement rules |

The renderer may interpolate between completed ticks. It must not change an
input action, collision, damage, winner, or the fighter's discrete facing.
Attack directions are interpreted by combat rules before camera motion.

## Source trace

In OpenOMF, `game_state_tick_controllers()` polls player controllers. During
`game_state_dynamic_tick()`, the arena polls actions, then the game state
moves objects, collides them, dynamically ticks them, and increments the match
tick (`src/game/game_state.c`). `arena_handle_events()` passes action events
to `object_act()` and records them for replay (`src/game/scenes/arena.c`). HAR
move, block, hit, and animation behavior lives in `src/game/objects/har.c` and
the object/animation layer. `object_render()` draws the current sprite through
`video_draw_full()` (`src/game/protos/object.c`); the OpenGL 3 renderer is a
sprite presentation backend, not the owner of the combat result.

An opt-in CSV probe now observes OpenOMF fights at the end of each
dynamic tick. It exports positions, velocities, facing, health, HAR state,
move, animation, and sprite frame. The trace and live state also export the
arena's declared match winner (`-1` until the match is decided), plus tick-level
hit and block masks and a round winner (`-1` except on the round-ending tick).
Version 4 adds up to four active projectiles per completed tick, including
owner, animation, sprite, position, and facing. Its final `projectiles` CSV
field is `-` when empty or pipe-separated
`owner:animation:sprite:x:y:facing` entries. Older trace files remain
readable. The Windows shared-state channel carries the same projectile
snapshots. The trace does not yet export input actions or shadow trail objects.
A local live experiment sends 3D-window key states to OpenOMF's controller
and follows its completed ticks, so source combat logic resolves movement and
attacks. Do not infer
move timings from the 3D meshes.
Initial Jaguar measurements are in `project/docs/OMF2115_JAGUAR_BASELINE.md`.

`project/prototype/main.c` now reads the exported CSV as a source-driven replay
view. It maps the source arena's x=20..300 and y=190 floor to placeholder 3D
robot positions and uses source facing, health, and animation IDs for display.
The view advances one completed source tick at a time and does not call its
own combat simulation while replaying or following live ticks. Live input and
fighter state and hit/block/round events currently use local shared memory
channels on Windows. Exact 3D animation poses and an in-process state bridge
remain future work.

## Current spike deviations to measure

`project/prototype/main.c` currently uses a fixed 60 Hz simulation, authored
placeholder robots, simple distance/height hit checks, and provisional
movement, jump, damage, stun, and guard values. `J` and `K` are punch/kick,
`W` jumps, and holding back guards while grounded. These are usability
controls for the spike, not a
claim of source input parity. There is one AI opponent and no source HAR
animation data or arena hazard. Compare these behaviors with the source match
before implementing Jaguar's move set.
