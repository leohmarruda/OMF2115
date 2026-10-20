# OMF2115 — roadmap

Status: revised after comparing the prototype with the [original game
reference](OMF2097/OMF2097_REFERENCE.md). This is a milestone plan, not a date
commitment.

## Target

Make **OMF2115** a faithful 3D rendition of One Must Fall 2097. Fighters and arenas
gain 3D models, animation, lighting, and camera work while the match remains
readable as a side-view fighter. Preserve the game's pilot-plus-HAR selection,
directional punch/kick controls, specials, blocking, stun, combos, hazards,
WAR's contest for Ganymede, pilot rivalries and endings, and Tournament mode.
The `project/prototype` spike now uses a side-on plane and the accepted Jaguar
and Shadow silhouette blockouts. Its standalone combat values and arena remain
technical placeholders rather than the combat or story template.

The story pass should expand OMF's own neural-link, WAR, Kreissack, and Nova
themes. The [story treatment](OMF2115_LORE_v2.md) develops the
government conspiracy, relationships, and physical cost of an experimental
link while keeping the setting, cast, and central tournament.
The [game specification](OMF2097_3D_GAME_SPEC.md) defines the target modes,
combat rules, presentation, production architecture, and acceptance gates.
The [development plan](OMF2097_DEVPLAN.md) breaks these into tasks,
dependencies, and phase exit checks.

## Technical approach

Keep OpenOMF as the mechanical reference and working baseline. It already
parses the original data and implements fights, story scenes, Tournament,
recordings, and tests. Before choosing how much to port or replace, make one
side-by-side match study: movement speed, facing, jump arc, hit timing, stun,
guard, and one HAR's specials. A production 3D engine may handle models and
animation, but gameplay parity is the measure of success. Do not commit to a
full engine migration until that study and a 3D match spike are complete.

**Fight engine decision (2026-10-15):** OMF2115 does not get a new combat engine.
Every fight runs on OpenOMF's reverse-engineered rules with the original AF/BK
data; the 3D view only renders the per-tick state it publishes. The prototype's
built-in combat loop is now a `--sandbox`-only placeholder and is no longer the
default. Gameplay must not be changed to make an effect visible: for example,
Shadow's shadow attacks (Shadow Punch, AF move 23) only have a script at
enhancement level 3, exactly as in the original Tournament, so the live
launchers expose that as an explicit `-ShadowEnhancement 3` option instead of
forcing it.

[OMF 2097 Remastered](https://github.com/Jared-woodruff/OMF-2097-Remastered)
(local sibling `../OMF-2097-Remastered`) was reviewed as an alternative. Its
MIT-licensed TypeScript fight code is a function-by-function port of OpenOMF,
runs headless in Node, parses the same original files, and has tick-for-tick
determinism tests. It is not adopted now because it has no parity tests
against OpenOMF, no per-tick state export, and no 3D renderer, and because the
OpenOMF trace, shared-memory live link, REC fixtures, and baselines already
exist. Revisit it at B08 if the production client moves to a web/TypeScript
stack; it would then need the same state exporter and REC parity checks.

## Milestones

| Stage | Deliverable | Completion check |
| --- | --- | --- |
| 0. Source baseline | Catalog pilot/HAR/arena/story data and rights; capture reference matches | Reference sheet includes controls, move timing, HUD, hazards, selection flow, and images from OMF. |
| 1. 3D fidelity spike | Jaguar and one rival, Stadium, side-on camera, 3D models, original-style movement | Players recognize the match as OMF: spacing, jumps, facing, punch/kick, and block behave like the source baseline. |
| 2. Combat vertical slice | Pilot-plus-HAR selection, one complete HAR move set, stun, combos, round flow, second arena hazard | A recorded source match and 3D match can be compared move by move; victory and defeat work. |
| 3. Visual and audio direction | Approved HAR silhouettes, arena material and lighting language, HUD, impacts, music approach | Fight remains readable at normal speed; original machines and arenas are recognizable in 3D. |
| 4. One-player story | WAR/Ganymede setup, pre-fight exchanges, Kreissack/Nova arc, pilot-specific outcome | One pilot's entire story route can be played from selection to ending. |
| 5. Tournament foundation | Custom pilot, winnings, upgrades, training, repair/economy, tournament progression | A pilot can enter, earn money, improve a HAR, and advance through a short bracket. |
| 6. Roster and release | Remaining pilots/HARs/arenas, local versus, controller support, options, packaging | Content and playtests meet agreed parity targets; every distributed asset has recorded provenance and permission. |

## Immediate next work

1. Finish the **original-game baseline** with isolated range and guard/stun
   checks for the remaining Jaguar and Shadow moves, then validate full-match
   readability with a human playtest. Signature traces, Stadium wall response,
   and a replayable source-driven match are now recorded.
2. Human-review the updated close-contact punch/kick spacing and signature
   poses at normal speed; source-replay captures now verify the sampled contact
   positions without changing OpenOMF timing or results.
3. Stadium staging now has an enclosed bowl, stepped crowd stands, and a
   central board. The live launcher now opens an in-game selection screen that
   connects ten playable pilots to Jaguar or Shadow, using their OpenOMF stats.
   Human-test the full Stadium match while OpenOMF owns combat timing/results.
4. Compare that playable match against the [recorded model match review](OMF2115_MODEL_MATCH_REVIEW.md)
   before expanding the roster or adding story scenes.

## Scope boundaries

- **First playable:** one faithful match with pilot and HAR choice, source-like
  controls, and one recognizable arena.
- **First story slice:** one existing pilot route in WAR's Ganymede contest,
  including original-style banter and an ending.
- **First Tournament slice:** custom pilot, prize money, an upgrade, and a
  short bracket.
- **Later decisions:** full roster, advanced cinematics, network play, and
  modes beyond the original. These follow a successful match and rights review.

## Rights checkpoint

OpenOMF's code is MIT licensed, but the original game's artwork, audio, text,
character designs, and name need their own distribution assessment. The local
`OMF2097` folder is useful as a development reference; its presence is not a
release license. Maintain an asset provenance list throughout production.

## References

- [Original game reference](OMF2097/OMF2097_REFERENCE.md)
- [Story treatment](OMF2115_LORE_v2.md)
- [Game specification](OMF2097_3D_GAME_SPEC.md)
- [Development plan](OMF2097_DEVPLAN.md)
- [OpenOMF repository](https://github.com/omf2097/openomf)
- [Original manual story](https://www.omf2097.com/wiki/doku.php?id=omf2097:story)
- [Decoded in-game help and text](https://www.omf2097.com/wiki/doku.php?id=omf2097:english.dat)
