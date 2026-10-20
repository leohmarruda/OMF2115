# Jaguar and Shadow signature move trace

Four local OpenOMF recordings compare Jaguar's concussion cannon (animation
21) and Shadow Punch (animation 23) at near and distant spacing. The fixtures
are derived from `rectests/6P.REC`; original files are unchanged. They run at
speed 10 with the null renderer and audio backend. The `.REC`, CSV, and BMP
outputs are local in the ignored `build/` (traces) and `omf3k/build/` (captures) directories.

| Move and fixture | Start spacing at tick 126 | Source animation | First enemy health change | 3D capture |
| --- | ---: | --- | --- | --- |
| Jaguar, distant `jag-special-trace.csv` | 191.005 source x units | 21 on ticks 126–144 (19 ticks) | Shadow 196 to 174 at tick 144 | [far hit](../build/mesh-match-ticks/jag-special-far-144.bmp) |
| Jaguar, near `jag-special-near-trace.csv` | 42.8 units | 21 on ticks 126–144 | Shadow 196 to 174 at tick 132 | [near hit](../build/mesh-match-ticks/jag-special-near-132.bmp) |
| Shadow, near `shadow-special-trace.csv` | 32.934 units | 23 on ticks 126–140 (15 ticks) | Jaguar 213 to 199 at tick 136 | [near hit](../build/mesh-match-ticks/shadow-special-near-136.bmp) |
| Shadow, distant `shadow-special-far-trace.csv` | 184.134 units | 23 on ticks 126–140 | Jaguar 213 to 199 at tick 143 | [far hit](../build/mesh-match-ticks/shadow-special-far-143.bmp) |

Jaguar's observed sprite order is 0, 1, 2, 3, 4, 3, 2. Shadow's is 0, 1,
2, 3, 4, 5. The prototype already selects arm poses with those sprite IDs.
All four CSVs pass `omf3d_prototype --source-replay-check`. Damage and timing
come from OpenOMF; no prototype collision rule determines these results.

## Source object positions and 3D blockouts

Version 4 of the optional source CSV also records up to four active projectile
objects per tick: owner, animation, sprite, position, and facing. Jaguar's
concussion shot first appears at tick 131 as animation 38 at x=117, y=131;
it advances by about nine source x units per tick in the distant fixture.
At the near hit, the object switches to impact animation 37 at tick 132.
Shadow's projection first appears at tick 135 as animation 54 at x=190–191,
y=190. In the near fixture it switches to animation 60 at tick 136; in the
distant fixture it continues moving left before the later hit.

The replay draws an authored cyan shot blockout and a purple duplicate
blockout from those object positions. Compare the [Jaguar shot in flight](../build/mesh-match-ticks/jag-projectile-flight.bmp),
[Jaguar near impact](../build/mesh-match-ticks/jag-projectile-hit.bmp),
[Shadow projection in flight](../build/mesh-match-ticks/shadow-projection-flight.bmp),
and [Shadow near impact](../build/mesh-match-ticks/shadow-projection-hit.bmp).
These are local `omf3k/build/` captures. The shapes are placeholders; their source
travel positions and animation transitions are now visible and replayable.

The current visual pass replaces Jaguar's broad rectangular shot with a
direction-aligned layered bolt and trail. Shadow's duplicate now uses the
projectile's recorded facing and a shallow foreground presentation offset, so
the projection remains visible when its source position overlaps a fighter.
These are rendering-only fits: recorded projectile positions, timing, and hit
results remain unchanged. Local checks are in
`omf3k/build/omf3d_jag_projectile_tapered_hit_tick144.png` and
`omf3k/build/omf3d_shadow_projection_contact_tick136.png`.

Shadow Punch now visibly animates before its projection spawns. The original
animation begins with an already-extended arm, so the 3D pass also keys torso
lean and a wide two-leg lunge to source sprites 0–5, and adds a cyan hand flash
on sprites 0–2. The source projection appears at tick 135, followed by the
near-contact hit at tick 136. Review the local [startup](../build/omf3d_shadow_punch_start.png),
[active pose](../build/omf3d_shadow_punch_active.png),
[projection spawn](../build/omf3d_shadow_punch_projection.png),
[near hit](../build/omf3d_shadow_punch_near_hit.png), and
[far hit](../build/omf3d_shadow_punch_far_hit.png) captures. All fighter
state and hit timing continue to come from OpenOMF.
The later [near-contact spacing review](../build/mesh-match-ticks/shadow-special-near-contact-adjusted.bmp)
keeps the Shadow Punch lunge readable beside Jaguar without changing either
fighter's source position.

## Fixture construction

The Jaguar fixture starts from the short local kick fixture described in the
[Jaguar baseline](OMF3K_JAGUAR_BASELINE.md). It replaces the kick at tick 126
with `PUNCH|LEFT` (`0x71`) and inserts Jaguar `DOWNLEFT` (`0x60`) at tick 122
and `LEFT` (`0x70`) at tick 124. These inputs perform `P41` while Jaguar faces
right. The near variant sets Shadow x to 100 at tick 121.

The Shadow fixture starts from the same short fixture and assigns its tick
126 punch and tick 127 release to player 2. At ticks 122–125, it inserts
`DOWNLEFT`, `DOWN`, `DOWNRIGHT`, and `RIGHT` for Shadow, then
`PUNCH|RIGHT` (`0x31`) at tick 126. With Shadow facing left, this performs
`P4123`. The near variant sets Jaguar x to 220 at tick 121; the far variant
omits that position assertion.

Shadow's animation 23 has the base script `A1`, which OpenOMF disables as a
no-op for an unenhanced pilot. Its level-three enhancement selects the
populated fifth script. The fixture sets pilot 2's Shadow enhancement to 3
with `rectool -f <fixture.REC> -k enhancement -k 1 -k 1 -s 3 --inplace`.
Without that setting, the same input selects animation 24 (`P41`). This is
why the signature trace needs an explicit pilot upgrade.

## Remaining presentation work

The blockouts still need final shape, scale, and effects, including review of
non-projectile shadow trails. The trace samples up to four active projectiles
per tick. The Windows live shared-state channel carries the same projectile
snapshots; the launcher also completed a hidden live capture at source tick
160. The signature effects still need a human-controlled live match review.
Live readability through a complete match remains untested by a human.
