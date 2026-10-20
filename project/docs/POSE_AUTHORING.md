# OMF2115 pose authoring workflow

The blockout renderer uses one shared joint rig. OpenOMF chooses each HAR's
animation, sprite, and completed tick. A catalog entry only overrides a pose
when a robot and source sprite need a distinct shape. Unauthored frames keep
the shared rough pose; they are not counted as finished animation fits.

The [move catalog](OMF2115_MOVE_CATALOG.md) lists every Jaguar and Shadow
animation with its input, authored status and a trace to check it against; regenerate it with
`python project/tools/generate_move_catalog.py` after editing `pose_catalog.csv` or
`move_names.csv`.

## 1. Inventory the local source data

From the repository root, with `aftool` built and the original game files in
the local `OMF2097` directory:

```text
python project/tools/pose_inventory.py
```

This writes `project/build/pose-inventory.csv` with HAR ID/name, animation ID, sprite
count, input, and animation script for every local `FIGHTR*.AF` file. The
current inventory contains 525 animations and 3,490 animation sprite keys
across 11 HARs. These counts describe source content, not completed 3D poses.

To export one move's original frames and collect its observed timing from a
source replay trace:

```text
python project/tools/pose_inventory.py --har 0 --animation 42 --export-sprites --trace build/omf_trace_z7/6p-trace.csv
```

The PNGs and their index go under `project/build/pose-reference/jaguar/42/`. The trace
produces `project/build/pose-timelines.csv`, with one row per consecutive sprite hold.
Pass `--trace` more than once to combine recordings. The `build` outputs remain
local and ignored; original artwork is not copied into the repository.

## 1b. Check for shared sprites before authoring

Different animations often draw exactly the same frames: Jaguar 15, 16 and 17, or 25, 26
and 28, and many Shadow pairs, differ only in input, enhancement level or state. Author a
sprite's pose once, not once per animation. Run this check **for every new HAR, and again
before starting any move**:

```text
python project/tools/sprite_duplicates.py
```

It exports the sprites of every Jaguar and Shadow animation if needed, hashes each sprite's
visible pixels (so a different canvas offset does not hide a match) and prints the groups,
also saved to `project/build/duplicate-sprites.json`. `~` marks animations that share only some
sprites. To cover a new HAR, add it to `HAR_DIRS` in `sprite_duplicates.py`.

Then regenerate the [move catalog](OMF2115_MOVE_CATALOG.md), whose "Animations that
share sprites" section lists each group with its members' status and a note: *author once*,
*free win* (a member is authored, so the others receive its poses), or *all authored*. The
[move browser](OMF2115_MOVE_CATALOG.md#seeing-a-move) shows a "same sprites as" badge
and a "hide duplicates" filter. Match animations by **sprite content**, not by number or
input: do not assume that animations with similar inputs or neighbouring ids share frames,
and do not assume that unrelated ones do not. Two animations that share sprites may still
differ in timing and travel, which the replay trace gives, not the sprite.

Authored poses are shared automatically. `python project/tools/sprite_duplicates.py
--write-groups` writes `pose_sprite_groups.csv`, which lists for each group the **player-triggered**
animations that draw identical sprites (reaction and state animations are left out, so a slide that
reuses the idle frames cannot receive the idle pose or the reverse). `generate_pose_catalog.py`
copies each authored row to the other animations of its group that have no row of their own, and
prints how many it added. An explicit row always wins over a shared one, and only authored rows
are shared, never defaults. Regenerate the groups file once per HAR or when the inventory
changes; it is committed, because it holds only animation ids. The generator also warns when
explicit rows for the same sprites disagree. The editor's export still writes explicit rows for
the group, which is harmless.

## 1c. Fast path: the pose editor

Fitting poses by typing numbers is slow, so use the editor:

```text
python project/tools/generate_pose_editor.py      # writes project/build/pose-editor/index.html
```

Open that file in a browser. It lists one entry per group of animations that share sprites
(section 1b). Each sprite shows the original frame with a skeleton: the pose already in
`pose_catalog.csv` if there is one, otherwise a fit from the sprite's joint markers (Jaguar),
otherwise, for Shadow (no markers), a starting pose copied from authored reference frames: Shadow
15 frame 0 for frames low to the ground (silhouette under 85% of the idle sprite's height) and
Shadow 16 frame 0 for the others, or a plain rest pose if those are not authored (change `REFERENCE`
in `generate_pose_editor.py` to use other frames). Drag the joints onto the sprite's elbow, wrist, knees and
ankles, tick the parts the pose overrides (`arm`, `arm2`, `leg`, `leg2`, `body`, `drop`, `lean`,
`reach`), tick *reviewed*, and press **Download all reviewed** (or **Download this
move**). Hover a joint for its name. The skeleton is a single chain: the pelvis is the root, the
spine runs from the pelvis to the neck joint, the legs hang from the pelvis
and the arms from a shoulder on the spine. Dragging the pelvis moves the whole body: sideways
sets `body` (z) and vertically sets `drop` (body height; dragging ticks `drop`). Dragging the
neck tilts the spine, and `lean` (forward shift per unit of height above the hip) exports that
tilt; dragging the neck ticks it. The dotted vertical line is rig z = 0, the idle torso line, so
every depth is measured from it. The head is a separate outline (top, back edge and front edge,
joined together; front and back follow the way the fighter faces, not the screen) that does not move with the neck, only with the pelvis; it only
helps you place the head and is not exported because the rig has no head parameter. Each arm also has an optional fingertip point (tick *R fingertip* or *L fingertip*) that follows its wrist; like the head and the optional three-point tail from the pelvis, it is a reference and is not exported. Optional *R shoulder*, *L shoulder*, *R head edge* and *L head edge* points (the character's anatomical right and left, for frames where the body turns toward the camera) work the same way; once a shoulder point is on, the matching arm is drawn from it. Arm heights are exported relative to `drop`, leg heights absolutely, as the renderer
expects. R and L are the character's right
(side +1, the +x side of the rig) and left (side -1), meaning anatomy, not screen position; for
a fighter facing right in the sprite, the right limb is the one nearer the camera. *Active side*
chooses which side the `arm` and `leg` parts override (`leg2` is the other leg). Joints and
handles can be dragged into the dark margin around the sprite, so limbs that are hidden or
extend past the sprite stay reachable. The *reference* menu switches the picture under the skeleton between the original sprite, the
remastered HD frame of the same pose and a blend; the HD frames come from a sibling
`OMF-2097-Remastered/public/hd` checkout, matched to the original sprites by fingerprint at 5x
horizontal and 6x vertical scale (so joint positions stay in the original sprite's coordinates),
and are saved under `project/build/pose-editor/hd/`. They are local reference material: check the
Remastered asset terms before copying any into a shareable artifact. Edits are kept in the
browser between visits. Exports can be partial: only
reviewed frames are written, and only the parts ticked on each. Then:

```text
python project/tools/merge_pose_rows.py ~/Downloads/pose-rows.csv --dry-run
python project/tools/merge_pose_rows.py ~/Downloads/pose-rows.csv
```

The merge combines rows with the same key part by part: exported parts overwrite and parts
that were not exported keep their values, so exporting only the legs never erases an authored
arm (`--replace` swaps whole rows, which is how to remove a part). It validates them with
`generate_pose_catalog.py`,
regenerates `pose_catalog.c`, and restores the previous catalog (kept at
`project/build/pose_catalog.backup.csv`) if validation fails. An exported row is applied to every
**player-triggered** animation in the sprite group, never to reaction or state animations, so
a slide that reuses the idle frames cannot overwrite the idle pose. Rebuild
`omf3d_prototype`, regenerate the move browser, and compare the render with the sprite.

**Joint markers in the sprites.** The original sprites are paletted, and the palette indices
carry body-part information. For Jaguar, indices 8-15 are the small dark joint cuffs: neck,
wrists, waist, knees, ankles and sometimes shoulders (elbows are often hidden). Each sprite
also has an offset from the fighter's origin (`aftool -m <anim> -s <sprite>`), which gives
absolute positions. `fit_poses.py` reads these and proposes rows; it is reliable on upright
poses (standing punch, kicks) and weak on crouched, airborne and rolling frames, which is why
the editor exists. Shadow has no joint markers: its indices 8-15 are the ribbed forearm and
shin segments, so its starting skeletons are rest poses to be dragged. The editor's height map
reuses Jaguar's pixel landmarks with each HAR's rest joint heights (an approximation for
Shadow), and the torso axis for Shadow comes from the silhouette.

## 2. Author a pose override

Edit [pose_catalog.csv](../data/pose_catalog.csv), adding one row for each distinct
sprite that needs a 3D joint fit. Keys are `(har, animation, sprite)`; `side`
selects the active limb (`1` or `-1`). Choose flags separated by `|`:

| Flag | Values used | Effect |
| --- | --- | --- |
| `reach` | `reach` | How far a strike is extended at this sprite, 0 to 1 (about 1 is fully extended). Replaces the generic reach curve, which drives the arm or leg for moves that have no joints authored. Also decides when the striking limb folds back to stop at an opponent standing close (above 0.5, for Jaguar's and Shadow's standing punch and kick and Jaguar animation 30), sets the lean and leg stance of Jaguar animation 30, and the spacing for close-contact attacks. The editor's default is the wrist's forward distance over 1.7. |
| `arm` | `elbow_y`, `elbow_z`, `wrist_y`, `wrist_z` | Places the active arm joints. |
| `leg` | `knee_y`, `knee_z`, `ankle_y`, `ankle_z` | Places the active leg joints. |
| `leg2` | `knee2_y`, `knee2_z`, `ankle2_y`, `ankle2_z` | Places the other leg. |
| `body` | `body_z` | Shifts the torso along the fight plane (negative faces the opponent). |
| `lean` | `lean` | Tilts the torso about the hip pivot (height 1.38) by atan(lean): lean is the forward shift per unit of height, so 1.0 is 45 degrees. It rotates the torso, head, pelvis and the arm's shoulder anchor without stretching them, so dives and rolls with tilts of 50 degrees or more work. Positive leans toward the opponent. Overrides the built-in lean of Jaguar animation 30 and Shadow's punch lunge. |
| `arm2` | `elbow2_y`, `elbow2_z`, `wrist2_y`, `wrist2_z` | Places the other arm. |
| `drop` | `body_y` | Body height relative to standing (negative is lower). Replaces the crouch drop derived from the fighter's state; arm joint heights are relative to it, leg joint heights are absolute. |
| `fist` | None | Legacy: stored in the catalog (four Jaguar rows have it) but the viewer never read it, so it changes nothing on screen. The editor no longer offers it, though an authored row that has it keeps it on export. It is replaced there by the optional fingertip points. |

Coordinates are in the blockout's local side-view plane: `y` rises from the
floor and negative `z` points toward the opponent. Leave fields outside the
chosen flags empty. The generator rejects duplicate keys, invalid flags,
missing values, and nonfinite coordinates.

```text
python project/tools/generate_pose_catalog.py
python project/tools/generate_pose_catalog.py --check
```

The generated [pose_catalog.c](../prototype/pose_catalog.c) is kept alongside the CSV so building the
prototype does not require Python. Edit the CSV and regenerate the C file;
do not edit generated C directly. The generator prints catalog coverage against
the latest local inventory.

## 3. Verify against source frames

Build `omf3d_prototype`, use `--model-preview-capture` for close views, then
capture selected ticks from a source replay with `--source-replay ...
--capture-tick N`. Compare the blockout with the exported source sprites and
record the observed sequence in the robot baseline. Jaguar's standing punch
is the first completed example in the [Jaguar baseline](OMF2115_JAGUAR_BASELINE.md).

Use the higher-resolution robot and character sprites in
[OMF 2097 Remastered](https://github.com/Jared-woodruff/OMF-2097-Remastered)
for visual pose and detail comparisons when they are available. Match frames
by robot and move before comparing;
do not assume its frame numbering or timing matches OpenOMF. The approved
three-view sheets still define the OMF2115 mesh, and the source trace still
defines combat timing. Record which remastered image informed a pose or detail
and check its asset terms before copying it into a shareable artifact. If the
matching Remastered frame is unavailable, label the pose fit provisional.
The Remastered `public/hd/index.json` maps original indexed sprite fingerprints
to HD atlas pages. Match exported OpenOMF sprites exactly with:

```text
python project/tools/match_remastered_frames.py ../OMF-2097-Remastered/public/hd project/build/pose-reference/shadow/42 --extract-dir project/build/hd-shadow-kick
```

The sibling `OMF-2097-Remastered` project is the local HD source. Its atlas
index and the Jaguar and Shadow atlas pages used in this pass were checked
against the earlier reference checkout and are byte-identical. Extracted
crops belong in the ignored `project/build/` folder. The HD artwork has different
colors and armor styling; use its pose and joint visibility, while the approved OMF2115 three-view sheets
continue to define the robot design.

Sprite order and holds can be extracted automatically. The 2D sprites do not
specify hidden depth, all joint centers, or a new 3D mesh. Those values still
need a visual fit, and each HAR needs its own recognizable model before its
catalog entries can be judged in game.
