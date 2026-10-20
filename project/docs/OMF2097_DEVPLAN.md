# OMF2115 — development plan

**Version:** 0.3  
**Status:** Working implementation plan for the [game specification](OMF2097_3D_GAME_SPEC.md); current production focus is Jaguar and Shadow only.  
**Story basis:** [OMF2115 story treatment](OMF2115_LORE_v2.md)  
**Planning rule:** Each phase ends with a playable or inspectable artifact and a written decision. Dates and staffing are set after the vertical slice establishes actual production speed.

## 1. Intended outcome and execution order

Deliver OMF2115 as a 3D rendition of *One Must Fall 2097* with side-on combat,
separate pilot and HAR selection, recognizable original machines and arenas, a richer
Ganymede story, improved Tournament career, and anime-influenced character
sequences. OpenOMF remains the original-game baseline and the source for
mechanics that can be reused without losing fight fidelity.

**Critical path:** source baseline → Jaguar/Shadow model blockouts → two-HAR 3D match → polished combat/story slice →
mode systems → full roster and narrative content → release validation.
Rights research and art direction run alongside the early phases, but final
asset production depends on both the combat camera and distribution rights.

| Priority | Meaning in this plan |
| --- | --- |
| **P0** | Required for the next playable gate or for a safe production decision. |
| **P1** | Required for the complete game, after the core gate passes. |
| **P2** | Candidate enhancement that can wait without breaking the spec. |

No phase is complete merely because its code compiles. The exit gate requires
a demonstrated flow, comparison with the OMF baseline where relevant, and a
list of remaining defects.

## 2. Current state in this checkout

- `src/` is the OpenOMF C11 game. It contains the fight scene, HAR behavior,
  arena hazards, game state, original-data loaders, Tournament/Mechlab flow,
  and a 2D-oriented OpenGL renderer.
- `testing/` contains source tests, including parsers and a recording fixture.
- `project/prototype/main.c` is an SDL2/OpenGL side-on spike. Its basic
  opponent and provisional standalone combat values remain technical
  experiments, not production combat.
- The prototype now has a source-driven Jaguar–Shadow live view and replay
  path. OpenOMF supplies completed fight states while the 3D view renders
  editable Jaguar and Shadow blockout geometry. This demonstrates the
  presentation connection, not finished Jaguar or Shadow art.
- Jaguar's approved [front, back, and right-side references](../robots/jaguar/canonical/README.md)
  and Shadow's approved [front, back, and right-side references](../robots/shadow/canonical/README.md)
  are the visual source of truth for the first two meshes. Jaguar has three
  digits per hand; Shadow's green eyes sit in a featureless black face opening.
  Both editable blockouts were accepted for the prototype silhouette milestone
  on 2026-10-14; neither is a final surfaced or skinned model.
- Two user-supplied Meshy FBX [mesh candidates](mesh/README.md) are available
  for visual exploration. The Blue Robot Mascot is classified as a Jaguar
  concept and the Blue Rocket Jester as a Shadow concept. Both remain dense,
  unrigged single meshes and are not the approved playable models.
- `OMF2097/` contains local original game data; it is untracked and has
  separate rights from OpenOMF's MIT-licensed code. `vcpkg_installed/` and the
  current build outputs are local dependencies/artifacts, not game content.
  Keep these out of source commits and distributable packages.
- A reproducible Windows Debug and Release build, headless OpenOMF replays,
  and the prototype self-test are recorded in the [source baseline](OMF2115_BASELINE.md).
  The source unit suite and a visible human-played reference match remain
  open baseline work.

### Candidate source touchpoints

These are audit locations, not an instruction to rewrite them immediately.

| System | Existing code to inspect first | Reason |
| --- | --- | --- |
| Match rules and state | `src/game/game_state.c`, `src/game/scenes/arena.c`, `src/game/objects/har.c`, `src/game/protos/player.c` | Tick order, movement, hits, round flow, stun, player stats. |
| Arena hazards | `src/game/objects/hazard.c`, `src/game/objects/arena_constraints.h` | Hazard timing and stage boundaries. |
| Rendering | `src/video/renderers/opengl3/`, `src/video/video.c` | Existing sprite draw path and room for a 3D presentation boundary. |
| HAR data | `src/resources/af.c`, `src/resources/animation.c`, `src/resources/pilots.c` | Original move/animation data and pilot separation. |
| Tournament | `src/game/scenes/mechlab/`, `src/resources/trnmanager.c` | Economy, training, selection, and brackets. |
| Story scenes | `src/game/scenes/cutscene.c`, `src/game/scenes/newsroom.c` | Existing scene progression and text presentation. |
| Tests/replays | `testing/test_rec.c`, `testing/test_af.c`, `testing/test_trn.c` | Regression patterns and original-data fixtures. |

## 3. Phase A — baseline and feasibility evidence (P0)

**Purpose:** know exactly what the original does, restore a repeatable build,
and find the boundaries between rules, data, and 2D display.

| ID | Task | Output and acceptance check | Depends on |
| --- | --- | --- | --- |
| A01 | Establish a clean Windows build in a new build directory using the documented toolchain; run OpenOMF with local data. Record compiler, dependencies, configuration, and commands. | A reproducible build note and one successful original match. Existing caches are not reused as evidence. | — |
| A02 | Enable and run available source tests; record failures separately from 3D work. | Test baseline with pass/fail counts and exact environment. | A01 |
| A03 | Capture reference fights: Jaguar versus Shadow in Stadium and one hazard arena, with fixed pilots, settings, and inputs. | Videos or frame captures plus replay/input files where available; settings documented. | A01 |
| A04 | Create a move and timing sheet for Jaguar and Shadow: walk, jump, guard, hit, stun, throws, specials, collision reach, round transitions, hazard cues. | Numbers or frame-by-frame observations with source and confidence noted; no invented values. | A03 |
| A05 | Trace ownership of the fight result from input through game state, HAR logic, animation, and renderer. Identify rules tied to 2D sprite frames. | Short architecture map and an adapter/extraction recommendation for each subsystem. | A01 |
| A06 | Inventory every source asset required by the first spike and its rights/provenance. Use locally authored placeholders where rights are unresolved. | Asset ledger with origin, intended use, replacement status, and distribution status. | — |
| A07 | Agree on a small human playtest protocol with OMF-familiar players: recognition, directional clarity, move feel, and camera readability. | A reusable score sheet and capture format. | A03 |

**Exit gate A:** a clean source build, reference captures, two-HAR move sheet,
initial rights ledger, and architecture map exist. The next team member can
reproduce the baseline from the written instructions.

## 4. Phase B — side-on 3D fidelity spike (P0)

**Purpose:** answer whether the original fight can be presented convincingly
in 3D with the current stack, before committing to a full renderer or art
pipeline.

| ID | Task | Output and acceptance check | Depends on |
| --- | --- | --- | --- |
| B01 | Define a match-state/presentation contract: input frame, fighter pose, hit/stun/guard state, arena event, and result event. Identify which side owns each value. | Interface sketch plus one event trace from an OpenOMF match. | A05 |
| B02 | Implement a fixed side-on fight plane and explicit facing rule in a separate spike target or isolated code path. Remove free arena-axis movement from the new match. | Two fighters remain on one gameplay plane; crossing sides never reverses an input unexpectedly. | B01 |
| B03 | Adapt the source Jaguar and Shadow move sets. Use the approved mesh blockouts for the first recognizable silhouette pass. | Walk, jump, punch/kick, guard, throw, and signature moves behave according to the A04 sheet. | A04, B02, B09 |
| B04 | Add fixed-tick hit/push shapes and animation sampling independent of rendered mesh contact. | Same input trace produces the same winner and hit sequence across replay runs. | B02, B03 |
| B05 | Build Stadium staging: floor bounds, depth layers, lighting, camera framing, readable HUD. | Full match can be played at fight-camera distance without losing either HAR or critical HUD data. | B02 |
| B06 | Add keyboard and gamepad mapping for two local players, pause/rematch, and a debug overlay for positions, facing, hit shapes, and tick count. | Two people can complete and rematch a set; controls can be tested without AI. | B03, B04 |
| B07 | Compare captured 3D footage and input traces with A03/A04. Record every meaningful timing/spacing difference and whether it is intentional. | Fidelity report, OMF-familiar playtest notes, and a prioritized defect list. | B03–B06, A07 |
| B08 | Decide the production presentation toolchain. Compare continuing with C/SDL/OpenGL, a dedicated 3D content layer using the same match contract, and adopting the published OMF 2097 Remastered codebase. | Decision record covering animation workflow, rendering quality, tooling, build risk, compatibility with core rules, migration cost, and asset rights. | B07 |
| B09 | Build simple Jaguar and Shadow 3D blockout meshes from their canonical front, back, and right-side views. Match overall height, joint centers, armor masses, hand/spike silhouettes, and side depth before detailed surfacing. | Editable source meshes and neutral-pose front/back/side renders for both HARs; written differences from the approved views. No rig or texture detail is required for this gate. | Approved three-view references |
| B10 | Load the two blockouts into the source-driven 3D view and compare them at the actual side-on fight camera distance. | Captured Jaguar–Shadow frames show both silhouettes, facing directions, hands, and attack reach clearly; defects are recorded before rigging. | B01, B02, B09 |

**Exit gate B:** Jaguar and Shadow complete a legible 3D local match in
Stadium. The camera respects the fighting plane; known deviations from OMF
are documented. The renderer/toolchain decision is recorded before large art
or cinematic production begins.

### Published remaster reconsideration at B08

[OMF 2097 Remastered](https://github.com/Jared-woodruff/OMF-2097-Remastered)
is a playable TypeScript/WebGL2 reimplementation with original-game data,
HD presentation, replay and training tools, and tests. Use it as a second
combat and presentation reference during A03/A04 and B07. Its current fight
presentation uses sprites and HD frames, including frames rendered from 3D
models; parallax depth and lighting do not by themselves provide live 3D HARs.
OpenOMF remains the working combat baseline while the Jaguar–Shadow 3D spike
is measured.

Its higher-resolution robot and character sprites are also useful when the
original sprites cannot resolve a silhouette, costume, face, or pose detail.
Consult the matching remastered image during visual review, record its
provenance, and assess its terms separately before copying artwork into OMF2115.

At B08, make a short side-by-side prototype or integration estimate for each
candidate using the same Jaguar–Shadow match contract and reference traces.
Record the work needed for live 3D meshes and animation, deterministic combat,
local input and replay, Stadium presentation, and the planned story/Tournament
systems. Choose the remaster as the foundation only if it demonstrates a clear
net advantage for the 3D target after accounting for migration of the existing
OpenOMF-to-3D connection. Otherwise, keep it as a reference and adopt specific
ideas or MIT-licensed code where useful. Review each proposed asset separately:
the remaster's [NOTICE](https://github.com/Jared-woodruff/OMF-2097-Remastered/blob/main/NOTICE.md)
distinguishes its MIT-licensed source from original game files and derivative
artwork distributed on different terms.

**Current visual scope:** validate Jaguar and Shadow's accepted prototype
blockouts and source-driven motion. Other HAR model work waits until their
fight-view motion and match readability have been assessed.
The side-view geometry is a design interpretation, so resolve any depth or
joint mismatch against the approved front/back views before adding detail.

## 5. Phase C — vertical slice (P0)

**Purpose:** prove that combat, art, sound, narrative, and saving form one
coherent experience. Crystal versus Christian is the reference story segment.

| ID | Task | Output and acceptance check | Depends on |
| --- | --- | --- | --- |
| C01 | Finish combat behaviors for Jaguar and Shadow: complete move lists, stun, combos, knockdowns, rounds, timeouts, and scrap finish. | Both HARs are playable from selection through result, with input and state checks for key moves. | B07 |
| C02 | Add the Power Plant or another original hazard arena, including a visible hazard cue and collision/timing test. | Hazard can be anticipated, avoided, triggered, and reproduced from a saved input trace. | C01 |
| C03 | Refine the approved Jaguar and Shadow blockouts into slice-quality 3D models, rigs, animations, effects, HUD, and one arena treatment under the approved art guide. | OMF-familiar players identify the machines and arena without labels; attacks remain readable at speed. | B08, B10 |
| C04 | Add pilot selection independent of HAR selection, with Crystal and Christian portraits, stats, and route context. | Any supported pilot/HAR pairing works in the slice; the story recommends but does not hard-lock a pairing. | C01 |
| C05 | Implement a data-driven scene runner for portraits, dialogue, choices, animations, and skip/log behavior. | A writer can add or edit a scene without changing combat code; invalid references are reported. | B08 |
| C06 | Author the Crystal/Christian sequence: pre-fight exchange, match, recovery scene, evidence choice, and consequence. | Choices persist through save/load and affect a visible later beat; the fight remains required. | C04, C05 |
| C07 | Produce one polished anime-style character sequence and one short in-engine HAR sequence. | Both can be watched, skipped, and replayed from a scene gallery/debug entry; subtitles remain readable. | C03, C05 |
| C08 | Add combat sound cues, music placeholder or licensed track, dialogue timing, and audio controls. | Block, hit, stun, hazard, and victory are distinguishable without looking at the HUD. | C01, C03 |
| C09 | Conduct end-to-end playtests and profile frame pacing/input latency on an actual target PC. Fix high-priority readability and stability issues. | A new player completes the slice without developer guidance; known defects and performance figures are recorded. | C01–C08 |

**Exit gate C:** the player selects a pilot and HAR, sees a character exchange,
fights, sees a recovery scene, makes a choice, and sees its consequence. The
slice is stable enough to estimate cost per HAR, arena, and story sequence.

### Post-slice scope review

Measure actual time spent on one finished HAR, one arena, one character
sequence, and one route segment. Use those measurements to forecast the ten
HARs, five arenas, ten endings, and Tournament event set. Reconcile the
forecast with available team capacity before authoring the full roster.

## 6. Phase D — shared game systems (P1)

This phase builds the reusable structures that make the rest of the content
affordable. Work can overlap once the C-phase contracts are stable.

| ID | Task | Output and acceptance check | Depends on |
| --- | --- | --- | --- |
| D01 | Formalize content schemas for HAR moves/animation hooks, pilot stats, arena hazards, dialogue, scene timing, and ending flags. | Every slice asset loads through a versioned schema; malformed entries fail with useful errors. | C01, C05 |
| D02 | Build versioned save data for story progress, Tournament career, controls, and settings; add migration tests. | An older test save loads after a schema change, or fails safely with an explicit message. | C06, D01 |
| D03 | Implement Training mode: move list, input history, dummy settings, hitbox/stun display, and recording playback. | A player can practice one special and diagnose why it missed. | C01 |
| D04 | Implement Arcade/One Player ladder and local Versus menu with round/time/arena options. | Multiple matches can be played without entering Story or Tournament. | C01, C04 |
| D05 | Implement Tournament pilot creation, starting budget, owned HARs, ranked events, payouts, repairs, training, upgrades, and ranking. | One short bracket can be won, spent, saved, loaded, and continued; all price/stat changes are displayed before purchase. | C01, D02 |
| D06 | Add named Tournament rivals, three event templates (ranked bracket, challenge, contract), and short illustrated rivalry beats. | Rival state changes after repeat fights; core rank progress does not require farming easy events. | D05, D01 |
| D07 | Add settings and accessibility: input remap, text scale, subtitles/log, reduced flashes/shake, audio mix, graphics scale, scene skip. | Settings persist and are usable from keyboard and gamepad; all story information remains available as text. | D02, C05 |
| D08 | Create automated content checks and a smoke suite for every mode entry/exit, save/load, and a representative fight. | Invalid content is caught before a build is shared; critical flows run on CI or a repeatable local command. | D01–D07 |

**Exit gate D:** all target modes have a working loop, even if much content is
placeholder. One saved Tournament career and one story route can survive a
normal build update. Designers can create content without editing fight code.

## 7. Phase E — full content production (P1)

### Combat and arena content

1. Produce the remaining eight standard HARs in small batches, not all models
   before any moves. For each HAR: silhouette sheet → gameplay move data →
   placeholder implementation → local balance test → rig/animation → effects
   and sound → opponent AI tuning → final review.
2. Produce the remaining original arenas with the same order: gameplay bounds
   and hazard → readable blockout → art and lighting → cue/audio → playtest.
3. Add color variants and selection previews once the base silhouette reads
   clearly. Track every move and hazard in a coverage matrix.
4. Implement Nova as a boss encounter after the normal roster works. Its
   spectacle can be greater, but it must use explicit, learnable rules.

**Per-HAR completion:** all source-defining moves are represented, every move
has documented inputs and timings, training display and AI can use it, two
local players can fight with it, and no major camera/hitbox ambiguity remains.

### Story and anime content

1. Lock the shared 2097 event timeline from the story treatment, including
   when the deep-link symptoms, cover-up, Nova evidence, and final match become
   known. Mark which details are proposed additions versus original canon.
2. Create a route grid for all ten pilots: intro, primary rival, distinctive
   mid-route scene, choice points, Nova perspective, ending, and optional
   relationship beats. Keep the original personality and motivation of each.
3. Script and implement routes in batches. Each route gets a full fight ladder
   and pilot-specific ending; shared scenes are reframed where necessary rather
   than copied verbatim ten times.
4. Build reusable portrait poses and expressions before commissioning many
   unique shots. Reserve fully animated sequences for the shared opening, key
   revelations, Nova, and a limited set of ending moments; use motion graphics
   and illustrated dialogue for routine scenes.
5. Review every sequence for skip behavior, subtitles, dialogue log, branching
   continuity, pilot/HAR pairing flexibility, and consistency with the
   original tournament premise. Keep romantic/fanservice material limited to
   established adult characters and voluntary scenes.

**Per-route completion:** the chosen pilot can finish the campaign, every
required scene and match has a fallback for any legal HAR choice, choices are
saved and reflected later, and an ending distinct to that pilot plays.

### Tournament and audio content

- Populate ranks, opponent builds, event rewards, repairs, parts, training
  costs, and rival encounters. Check that several viable spending strategies
  can reach the top rank without repeated low-level fights.
- Compose or license arena music and complete HAR-specific sound sets with
  documented rights. Add voice lines only after the text and scene timing are
  stable, to avoid rerecording story revisions.
- Keep the Tournament's upgrades confined to its ruleset unless both local
  Versus players opt into them.

**Exit gate E:** ten selectable pilots, ten standard HARs, five original
arenas, pilot-specific story endings, an improved Tournament career, and all
target mode content are complete and traceable in the coverage matrix.

## 8. Phase F — release candidate and handoff (P1)

| ID | Task | Release evidence |
| --- | --- | --- |
| F01 | Full combat regression: input traces, representative replays, all moves, all hazards, all pilot stat combinations. | No reproducible winner/health desync or major unreadable move remains. |
| F02 | Story and Tournament walkthroughs on clean profiles and upgraded saves. | Every route ends; purchases, repairs, rank, and choices persist correctly. |
| F03 | Performance and hardware sweep on the chosen minimum and recommended PC profiles. | Stable target frame pacing with documented settings; input latency and loading times measured. |
| F04 | Accessibility, controller, and UX pass with players new to OMF and OMF veterans. | Critical actions are discoverable; subtitles, remaps, skip/log, and reduced effects work throughout. |
| F05 | Content/legal audit and packaging. | Asset provenance ledger is complete; only approved data and licensed material enter release packages. |
| F06 | Crash/telemetry policy, bug triage, release notes, and post-release support plan. | A shippable build and a prioritized known-issues list exist. |

**Exit gate F:** the complete target can be installed, played, saved, and
finished on supported platforms, with all shipped content cleared for use.

## 9. Cross-phase quality system

| Evidence | When created | Purpose |
| --- | --- | --- |
| Clean build record | A and each release build | Avoid machine-specific setup masking project failures. |
| Original-match reference captures | A, updated only when source settings change | Anchor movement, moves, camera, and hazards. |
| Input/replay fixtures | B onward | Reproduce combat changes and regressions. |
| Human playtest notes | Each playable gate | Catch feel and readability problems that headless tests miss. |
| Coverage matrix | C onward | Track each pilot, HAR, arena, mode, route, move, and scene. |
| Asset provenance ledger | A onward | Separate local reference data from distributable content. |
| Decision records | B and scope reviews | Preserve reasons for engine, art, input, and balance choices. |

Automated tests should target rules that can regress silently: move legality,
collision and damage order, hazard timing, save migration, content references,
and replay reproduction. Visual review should use captured frames and live
play; a passing self-test alone does not prove a good fighting game.

## 10. Main risks and responses

| Risk | Early signal | Response |
| --- | --- | --- |
| OpenOMF rules are too tied to sprite frames for a direct 3D renderer swap. | B01/A05 trace shows animation frames deciding combat in many places. | Keep source as reference; isolate a compact combat simulation that preserves measured behavior and can feed either presentation path. Decide at B08. |
| Free camera or 3D rotation makes inputs feel wrong. | Crossovers and corner fights confuse playtesters. | Lock the fight plane and facing rule; restrict cinematic camera motion to noninteractive moments. |
| Art looks generic despite higher fidelity. | Veterans fail to identify HARs or arenas in an unlabeled clip. | Review silhouette, color blocking, and arena framing before detail passes. |
| Ten HARs and ten routes exceed production capacity. | C-phase throughput forecast exceeds available team time. | Re-plan content batches from actual slice costs; keep shared systems reusable and make any scope reduction explicit. |
| Tournament becomes grindy or upgrades overpower skill. | Testers repeat easy matches or one purchase dominates builds. | Simulate payouts, cap upgrade effects, and test multiple viable career paths. |
| Story scenes interrupt match rhythm. | Frequent skipping or abandonment between fights. | Keep routine scenes short, make all scenes skippable, use a log, and reserve animation for major turns. |
| Original assets or name cannot be distributed. | Rights ledger has unresolved entries at C/E gates. | Use authored placeholders during development; commission replacement content or obtain permission before packaging. |
| Local build works only on one machine. | A01 cannot be reproduced cleanly. | Stabilize the toolchain and build script before expanding features; test a second environment at each major gate. |

## 11. People, estimates, and task tracking

The work needs gameplay/engine programming, 3D modeling and animation,
character illustration and cinematics, fight and economy design, narrative
writing, audio, QA, and rights/production review. One person may cover several
roles, but the plan should show that person's available capacity rather than
counting the same time twice. Early A/B work is mostly engineering and design;
E is dominated by art, animation, writing, integration, and balance.

Create one work item per task ID. Each item records an owner, dependencies,
source files or assets touched, acceptance evidence, review notes, and actual
effort. At Gate C, use the measured throughput for a completed HAR, arena,
route segment, and cinematic to estimate the remaining content. Add integration
and QA capacity separately. The resulting forecast, plus team size and rights
status, becomes the first credible schedule for the full target.

## 12. Next work package to execute

**B09's blockout review is accepted for the prototype milestone.** The
[Jaguar](../robots/jaguar/blockout/README.md) and
[Shadow](../robots/shadow/blockout/README.md) folders contain editable glTF
meshes, reproducible generators, and front, back, side, and fight-distance
renders derived from their approved three-view references. The user accepted
both silhouettes on 2026-10-14. The earlier
[procedural blockout review](OMF2115_BLOCKOUT_REVIEW.md) is historical; its
pending editable-mesh decision is superseded by these assets.

**B10 has a recorded fight-camera comparison, with live readability still
open.** Both meshes run in the source-driven Jaguar–Shadow view. The
[model match review](OMF2115_MODEL_MATCH_REVIEW.md) compares a 356-tick OpenOMF
recording and local punch/kick variants for reach, timing, facing, and
readability. Source combat owns hits and timing. The prototype has rigid-joint
glTF previews for idle, walk, jump, guard, punch, kick, hit, and each HAR's
signature pose. These are blockout clips, not final skinned rigs or a complete
source-timed move set.

Sampled close-range Jaguar standing punch, down punch, and kick contacts now
fold the striking limb toward Shadow while preserving the long-range pose and
source hit result. The actual down-punch trace confirms animation 30 hits at
tick 129 (19 HP); its recovery tail still needs a longer fixture.
The [signature move trace](OMF2115_SIGNATURE_MOVE_TRACE.md) now captures both
moves at near and distant spacing. Their fighter poses and health changes
replay. Version 4 of the source trace now includes active projectile objects;
the 3D view uses their recorded positions for a cyan shot and a purple
projection blockout in CSV replay and shared-state live play. An initial
visual pass refines the projectile shapes and near Shadow Punch contact.
Shadow Punch now keys its full-body lunge and hand flash from the source sprite;
source trace positions and hit results remain authoritative. The next work is
to validate the animation in live play and review a complete live match at
normal camera distance.
B03, B07, and the Phase B exit gate remain open; they also
require the broader move list, Stadium presentation, and a human readability
playtest. Keep A02's source unit tests, A03/A04's broader reference and timing
sheet, and A06's asset ledger open in parallel.

## Related documents

- [Game specification](OMF2097_3D_GAME_SPEC.md)
- [Story treatment](OMF2115_LORE_v2.md)
- [Original game reference](OMF2097/OMF2097_REFERENCE.md)
- [Milestone roadmap](ROADMAP.md)
- [Existing prototype notes](../prototype/README.md)
