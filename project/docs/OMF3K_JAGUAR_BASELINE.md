# Jaguar combat baseline — source data and replay trace

This sheet records values read locally from `OMF2097/FIGHTR0.AF` with
OpenOMF's `aftool`. `src/resources/ids.c` maps Jaguar to that file. These are
source data values. The replay observations below are a separate measurement
from OpenOMF's end-of-tick match state. The original data is kept local and is
not part of a distributable build.

## HAR file values

| Field | Raw value | Interpretation |
| --- | ---: | --- |
| Fighter ID | 0 | Jaguar |
| Health | 200 | Base HAR file value |
| Forward speed | 5 | Source position units per dynamic tick before pilot scaling |
| Reverse speed | 4 | Source position units per dynamic tick before pilot scaling |
| Jump speed | -14.5 | Source vertical velocity; screen Y increases downward |
| Fall speed | 1.148438 | Base gravity value |
| Execution window | 10 | File value; exact move-input behavior needs match observation |
| Upward jump frame limit | 2 | File value; exact effect needs match observation |

OpenOMF scales movement by the selected pilot's agility in
`src/game/objects/har.c`. Forward/reverse/fall use `(agility + 20) / 30`;
jump uses `(agility + 35) / 45`, a further `216 / 256` factor, and a game
jump multiplier. Record the pilot before comparing speed or jump height.

At the default game-speed setting of 5, `game_state_ms_per_dyntick()` returns
48 ms for an arena tick; speed 10 gives 28 ms. Replay tests run at speed 10.
The prototype currently uses 60 Hz and world units, so raw AF values cannot
be pasted directly into it as seconds or metres.

## Move records for the first comparison

The input strings below are the exact AF strings. Numbers use OpenOMF's
relative numpad directions; `P` is punch and `K` is kick. Move categories and
damage are file fields. A move's final startup, active, recovery, and range
depend on its animation script, pilot modifiers, hit coordinates, and runtime
state. They still need a tick trace and visual reference match.

| Move ID | AF input | Category | Damage field | Next check |
| ---: | --- | --- | ---: | --- |
| 42 | `P` | High | 8 | Standing basic punch; animation, hit, and guard measured below |
| 41 | `K` | Medium | 22 | Standing basic kick; animation and contact measured below |
| 18 | `K3` | Low | 10 | Down-forward kick; test low guard |
| 19 | `K2` | Low | 22 | Down kick; test low guard |
| 20 | `P6` | Close | 45 | Close throw behavior measured below |
| 30 | `P2` | Medium | 22 | Down punch |
| 32 | `P1` | High | 35 | Down-back punch |
| 15 | `P63` | Jumping | 30 | Test air version and entry conditions |
| 17 | `P63` | High | 30 | Test grounded version and entry conditions |
| 16 | `P6321` | High | 30 | Test full directional sequence |
| 21 | `P41` | High | 10 | Animation contains `m38`; trace projectile spawn |
| 38 | `!` | Projectile | 26 | Spawned projectile record, not a direct input |

OpenOMF's `har_is_blocking()` treats back (`4`) and down-back (`1`) as
standing guard; low moves require down-back. Close moves cannot be blocked.
The side-on spike now uses back to block and Jaguar's 5:4 forward/reverse
speed ratio, but its absolute pace and attack timings remain provisional.

## Observed OpenOMF replay values

These values come from an opt-in end-of-dynamic-tick CSV probe in
`src/game/game_state.c`, built with `OMF3K_SOURCE_TRACE=ON`. Both replays were
run headlessly at game speed 10 (28 ms per dynamic tick) with the null video
and audio backends. Tick numbers refer to the CSV's completed ticks. The CSV
files are local in the ignored `build/omf_trace_z7/` directory. Repeating the
corner-throw replay produced a byte-identical CSV (SHA-256 compared).

| Fixture and setting | Observation | Confidence |
| --- | --- | --- |
| `JAG-CORNER-THROW.REC`: Crystal/Jaguar (agility 16) vs Shirro/Electra (agility 1), Stadium, hazards off | Jaguar reversed from x=110 at tick 90 to x=105.2 at tick 91, then moved 4.8 source position units per tick until the corner. This equals raw reverse speed 4 × `(16+20)/30`. | High for this pilot and replay |
| Same fixture | Jaguar advanced from x=20 at tick 187 to x=26 at tick 188, then x=32 and 38 on the next two ticks: 6 units per tick, or raw forward speed 5 × `(16+20)/30`. | High for this pilot and replay |
| Same fixture, close `P6` throw | Jaguar entered animation 20 at tick 191. Electra entered throw state 7 and animation 9 on that same completed tick. Jaguar remained in animation 20 through tick 213 and returned to idle at tick 214: 23 sampled ticks. | High for this replay; animation duration includes its scripted sequence |
| Same throw | Electra's health changed from 196 to 158 at tick 210, 19 ticks after the first sampled throw frame. The observed 38-point loss reflects match modifiers; the AF damage field is 45. | High for the observed health delta; no claim of a universal damage value |
| `6P.REC`: Crystal/Jaguar vs Shirro/Shadow, Stadium, hazards on | Standing punch animation 42 occupied ticks 126–133, returning to idle at 134. A second punch occupied ticks 148–155, returning to idle at 156. Each took 8 sampled ticks. Both missed at large separation. | High for animation duration |
| Local short variant of `6P.REC`, same pilots and settings | A replay assertion placed Shadow at x=88 on tick 123. The fighters settled at x=62.8 and x=92 by tick 125 (29.2 units apart). Jaguar entered punch animation 42 at tick 126; Shadow's health fell from 196 to 189 at tick 128, when Jaguar's animation tick was 4 and sprite ID was 3. Shadow entered hit state 7/animation 9, then moved back. | High for this hit timing and 7-point match damage; one spacing sample, not maximum range |
| Local guard variant of that short replay | Shadow held back from tick 124. At tick 128, the same punch caused block state 10/animation 5 and pushback, with health unchanged at 196 because block damage was set to 0. Block state lasted through tick 136. | High for this guarded case; Shadow moved during guard, so spacing differs from the hit variant |
| Local punch range sweep, same short replay and grounded Shadow | With Jaguar at x=66.8, a stationary Shadow at x=154 (87.2 units apart) was hit at tick 128; at x=155 (88.2 apart), it was not hit during the whole punch. Selected placements from x=94 through x=192, including every integer from 153 to 159, bracketed this boundary. | High for this pilot/HAR/pose/replay; no universal HAR range claim |
| Local late-entry sweep, Shadow placed at x=120 or x=88 during the punch | Shadow entering range on tick 128, 129, or 130 was hit on that tick. Entering on tick 131, 132, or 133 did not connect, even at x=88. Shadow already in range before tick 128 was first hit on tick 128. | High for a three-tick active window (128–130) against this grounded target |
| Local neutral-jump variant of `6P.REC`, Crystal/Jaguar | Jaguar left the ground at tick 126 from y=190, reached its highest sampled position at tick 136 (y=113.275, 76.725 units above the floor), and first returned to grounded idle at tick 147. It was airborne on 21 completed ticks, 126–146. Post-tick vertical velocity was −12.487 at takeoff, rose by about 1.378 each tick, and was capped at +13 during descent. | High for this pilot, 100% jump-height setting, and unopposed jump |
| Local standing-kick variant, same pilots/settings | Jaguar entered kick animation 41 at tick 126, remained through tick 140, and returned to idle at tick 141: 15 sampled ticks. With Shadow at x=120, the first hit was tick 129; health fell from 196 to 177 (19 match HP, versus AF damage field 22). | High for animation and observed contact/damage |
| Local kick late-entry variants | Shadow entering range at tick 132 or 133 was hit on that tick. Entering at tick 134 or later did not connect, including at close x=88. A target already in range first took damage at tick 129, giving an observed active window of ticks 129–133. | High for this grounded Jaguar–Shadow setup |
| Same kick hit, Shadow knockback | Shadow's x velocity was +7 at hit tick 129 and decreased by 1 per tick to 0 at tick 136. Its x position moved from 120 to 148, a total of 28 source units. | High for this unblocked mid-stage hit |

The trace reports positions after movement, collisions, and dynamic object
updates. The first sampled punch frame is tick 126, so the first active frame
at tick 128 follows two completed ticks (56 ms at speed 10). The observed
active window is three ticks, ending at tick 130; the animation returns to
idle at tick 134. This does not yet prove the exact input-recovery boundary.
Sprite IDs and animation ticks are present in the CSV for frame-by-frame
inspection. The local `.REC` variants and CSVs are in `build/omf_trace_z7/`;
they are measurement fixtures, not original game files or distributable
assets. All range and late-entry variants ended normally with exit code 0.

### Jaguar standing-punch presentation timeline

The 3D blockout now follows animation 42's observed sprite sequence rather
than a generic sine curve. Exported Jaguar sprites 0–3 in the local
`omf3k/docs/OMF2097/poses/jaguar/punch-frames/` directory guide four authored arm
poses. OpenOMF's completed tick selects the pose; the renderer does not change
hit timing or damage.

| Completed tick | Animation tick | Sprite | Blockout arm pose |
| ---: | ---: | ---: | --- |
| 126 | 2 | 1 | Start extension |
| 127 | 3 | 2 | Extend |
| 128–129 | 4–5 | 3 | Full extension, compact fist |
| 130 | 6 | 2 | Begin retraction |
| 131–132 | 7–8 | 1 | Recover |
| 133 | 9 | 0 | Return to rest |

The sprite order and holds are observed in `6p-trace.csv`; the arm joint
positions are a first visual fit to those sprites. Capture checks at ticks
126, 128, 131, and 133 show the extension, hold, and recovery. Exact mesh
silhouette and the other Jaguar and Shadow moves still need their own fits.

### Jaguar standing-kick presentation timeline

Animation 41 now selects four authored front-leg poses from source sprite IDs.
The knee chambers, extends, holds, and retracts with the recorded source
sequence; this changes presentation only. The local source references are in
`omf3k/build/pose-reference/jaguar/41/`, and fight-camera captures are in
`omf3k/build/omf3d_jaguar_kick_126.bmp`, `_128.bmp`, `_130.bmp`, and `_139.bmp`.

| Completed ticks | Sprite | Blockout leg pose |
| --- | ---: | --- |
| 126–127 | 1 | Knee raised, foot tucked |
| 128–129 | 2 | Leg extending |
| 130–132 | 3 | Full horizontal extension |
| 133–135 | 2 | Begin retraction |
| 136–138 | 1 | Knee chambered again |
| 139–140 | 0 | Return toward stance |

The source sprites establish the visible side profile and frame order, while
the approved Jaguar three-view references still govern the 3D robot shape.
The original indexed sprites were matched by pixel fingerprint to all four
higher-resolution kick frames in
[OMF 2097 Remastered](https://github.com/Jared-woodruff/OMF-2097-Remastered).
The HD frames show a higher knee and toe at full extension, which informed
the revised sprite-3 joint fit. The Remastered blue armor and palette are not
the OMF3K design reference; the approved three-view sheets remain authoritative.

To rebuild the local variants, use `rectool` on a copy of `rectests/6P.REC`:
insert a `set` assertion at tick 123 for HAR 2's x position to 88, truncate
events after tick 140, and add a HAR 1 health `> 0` assertion at tick 139 so
playback continues past the punch. For the guarded variant, also insert a
player 2 `RIGHT` action (`0x30`) at tick 124; Shadow faces left, so this is
back. The untouched fixture remains in `rectests/`.

The range sweep changes that tick-123 x value. The late-entry sweep instead
sets Shadow's x position on individual ticks 127–134, starting from the short
fixture without its tick-123 position change.

For the isolated jump and kick, the short fixture's tick-126 punch input was
changed to `UP` (`0x10`) or `KICK` (`0x02`), its punch-animation assertion was
removed, and its final health assertion was moved to tick 200. The kick hit
variant places Shadow at x=120 on tick 123; the kick late-entry variants move
that placement to a specified later tick. `rectool` currently prints the
`0x02` kick action as “PUNCH,” but the resulting replay enters Jaguar's kick
animation 41.

## Prototype comparison

Jaguar's down punch (`P2`, animation 30) now has four source-sprite arm fits.
Each original indexed frame was matched by fingerprint to the corresponding
HD Jaguar atlas frame in the local sibling `OMF-2097-Remastered` project.
Those frames show a forward body lean and split-leg lunge rather than a
stationary standing punch. The 3D blockout now leans from the hips and spreads
the legs through the four authored frames. The fight-camera check used a
synthetic sprite sequence in `omf3k/build/jaguar-down-punch-preview.csv`, with its
final capture in `omf3k/build/omf3d_source_replay_capture.bmp`. This checks visual
selection; the source timing is now measured separately below. The model is
still a blockout, and the approved Jaguar three-view sheets control its armor
design.

An actual OpenOMF down-punch trace is captured in
`build/omf_trace_z7/jag-down-punch.csv`, made from a local copy of the short
Jaguar–Shadow fixture. At speed 10 (28 ms per source tick), Jaguar starts at
x=62.8 and Shadow at x=92.0, 29.2 source units apart. A replay assertion
confirms animation 30. The recorded sprite order is 1 on ticks 126–127, 2 on
128–129, 3 on 130–132, and 2 on 133–134. Shadow loses 19 HP (196 to 177) on
tick 129, when Jaguar is on animation tick 5/sprite 2; the event mask confirms
player 2 was hit. This is one close-range contact sample, not a range or full
recovery measurement: the trace ends at tick 134 while animation 30 is still
active. The 3D view now folds Jaguar's down-punch arm toward a nearby opponent
at contact, like its standing punch fit. Local before/after captures are
`omf3k/build/omf3d_jag_down_punch_tick129.png` and
`omf3k/build/omf3d_jag_down_punch_contact_tick129.png`.

The side-on prototype uses a 60 Hz simulation and world units. Its current
light punch lasts 0.27 seconds (about 16 prototype ticks), checks contact
about 0.10 seconds after starting, and deals 11 HP for the player. Its guard
reduces damage to 20% rather than using the source replay's zero block-damage
setting. These numbers are provisional. At the source's default speed 5,
eight combat ticks span 384 ms; at replay speed 10, they span 224 ms. Preserve
the source combat tick and match settings when integrating rules, rather than
converting one replay's wall-clock times into fixed 60 Hz constants.
The prototype's kick duration is 0.44 seconds and its jump uses separate
world-unit velocity/gravity values; neither has been calibrated to this
source trace. Fifteen source ticks for the kick span 720 ms at default speed 5
and 420 ms at replay speed 10. The observed jump spans 22 ticks from takeoff
input through first grounded state (1,056 ms or 616 ms at those speeds).

To reproduce, configure a separate build with `-DOMF3K_SOURCE_TRACE=ON`, set
`OMF3K_TRACE_PATH` to a writable CSV path, and replay a `.REC` file with
OpenOMF's `-P` option. The probe also observes live arena matches and flushes
each complete fighter pair for the 3D follower. The normal build leaves the
probe disabled. The full
Windows build setup and local data location are recorded in
`omf3k/docs/OMF3K_BASELINE.md`.

## Capture still needed

Measure kick range and guard response; repeat punch range and jump behavior
against other pilots, HARs, poses, and settings before treating these
Jaguar–Shadow values as general rules. A complete source-driven Jaguar–Shadow
result and Stadium wall-response captures are now in the
[Stadium and full-match baseline](OMF3K_STADIUM_BASELINE.md); a fixed-input
recording and human visual review remain open.
Keep local replay outputs in the ignored build folder until asset rights are
resolved. Only then adapt Jaguar's full move set.
