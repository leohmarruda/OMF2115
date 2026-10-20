# Importing a Meshy mesh as a playable HAR

How the Robot Mascot (Jaguar) and Rocket Jester (Shadow) were turned into rigged
prototype models, written so the next mesh goes faster. Everything is driven by
[`generate_meshy_meshes.py`](../../tools/generate_meshy_meshes.py); the result is
`project/prototype/meshy_meshes.h`, selected at runtime with `OMF3K_MESHY=1`.

## What the prototype expects

The prototype does not skin meshes. `main.c` draws **rigid parts**, each tagged with a
rig group and side, and `model_transform`/`rig_map` move each group between fixed rest
joints and the posed joints, in the (y, z) plane only. So an imported mesh must be:

- in **blockout rest pose**: spine upright, arms and legs hanging straight down;
- at the blockout's **joint heights** (per HAR, `rest` in the script, copied from
  `model_transform` in `main.c`): Jaguar shoulder 2.24 / elbow 1.76 / wrist 1.13 /
  hip 1.30 / knee .75 / ankle .23; Shadow 2.25 / 1.77 / 1.11 / 1.27 / .76 / .24;
- **x = lateral, y = up, forward = -z**, side = sign of x;
- split into groups: 0 torso, 1 head, 2 pelvis, 3 upper arm, 4 forearm, 5 hand,
  6 thigh, 7 shin, 8 foot (side -1/+1 for limbs);
- indexed with `uint16` (under 65,536 vertices per model) and a modest triangle
  count, because every triangle is projected on the CPU each frame.

## Steps

1. **Inspect the FBX.** The Meshy exports are binary FBX, one fused mesh, no skeleton,
   UVs or materials. `fbx_reader.py` reads vertices and triangles. Check the bounds
   to find the axes (both exports are **Z up, Y depth, X lateral**).
2. **Find the front.** The FBX does not say. Compare the feet to the shins: the toes
   extend toward the front. Both models face **-Y** (`front_sign = -1`). A front view
   cannot tell you; a chest emblem or studs rendered without culling cannot either.
3. **Add a `Model` entry** in `MODELS`: FBX name, HAR id, and **landmarks** read off a
   front preview image in pixels (head base, neck, spine top/bottom, both
   shoulder/elbow/wrist, hip/knee/ankle), plus the pixel-to-unit mapping (the pixel that
   is X=0, Z=0 and pixels per unit; the preview is fitted to the bounding box, so
   derive it from two known extremes). Render a debug view and adjust.
   `python generate_meshy_meshes.py --debug <dir>` writes `<prefix>_front.png` and
   `_side.png` coloured by rig group.
4. **Tune the classification.** Vertices go to the nearest bone, distance divided by a
   per-bone radius (`radius`). Hands and feet are "past the end of the last bone"
   (`foot_by_z` for near-vertical legs); the head is above `head_base` and within
   `head_halfwidth` of it. Set the head cut just above any collar or shoulder spikes,
   or they land in the head group.
5. **Retarget.** `retarget()` stands the spine up and hangs arms and legs, rotating
   each chain about its joint and carrying the landmarks with it. A model already
   in a neutral pose changes little; the Jester's lunge needed all of it.
6. **Fit to the blockout.** `to_prototype()` maps heights piecewise onto the rest joint
   heights, then fits size from **measurements of the blockout** read out of
   `model_meshes.h` (`blockout_groups`):
   - legs and torso-level width and depth: ratio of blockout to mesh size, thighs for
     the legs and upper arms for the torso level, interpolated by height so groups
     stay joined (per-group fits open cracks at the seams);
   - head: one uniform scale sets its width to the blockout head's; its bottom sits
     where the blockout head starts. Do not box-fit the head, it distorts the shape.
7. **Decimate** with vertex clustering (`cell`). Aim for roughly 20-35k triangles per
   model and stay under the `uint16` limit. Triangles are assigned to a group by
   majority and moved rigidly, so seams stay intact.
8. **Cover and blend joints.** Ball joints (`joint_caps`) are added at each joint,
   centred on the fitted limb. Vertices within `BLEND_BAND` of a joint also follow the
   neighbouring group (`ModelBlend`, weight .5 at the joint fading to 0); `main.c`
   interpolates the two transforms.
9. **Colour** per rig group with `palette`.
10. **Wire it in `main.c`:** include the arrays and add the HAR to the selection in
    `robot_loaded_model`. `OMF3K_MESHY=1` switches all Meshy meshes on.
11. **Check the moves for the new HAR** (the mesh is only half of it: a move shows only if
    its poses are authored, see `project/docs/POSE_AUTHORING.md`):
    ```
    python project/tools/pose_inventory.py            # animations, inputs, sprite counts
    python project/tools/sprite_duplicates.py --write-groups   # which animations share sprites; poses are shared
    python project/tools/generate_move_catalog.py     # status, traces, free wins
    python project/tools/generate_move_browser.py     # original sprite | blockout | Meshy
    python project/tools/generate_pose_editor.py      # fit poses to the sprites, then merge_pose_rows.py
    ```
    Add the HAR to `HAR_DIRS` in `sprite_duplicates.py` and `HARS` in
    `generate_move_catalog.py`. **Run the duplicate check before authoring or judging any
    move**: many animations draw the same sprites, so one authored pose covers several, and
    two that look different in the catalog may be the same frames.

## Run and check

```
py -3 project/tools/generate_meshy_meshes.py [--debug <dir>]   # regenerate the header
project\prototype\run-meshy.ps1 [-Capture]        # regenerate, build, model preview
project\prototype\run-meshy-fight-jaguar.ps1      # live fight as Jaguar
project\prototype\run-meshy-fight-shadow.ps1      # live fight as Shadow
```

`-Capture` writes `project/build/omf3d_model_{side,front,back,punch,kick,guard,...}.bmp`.
Check idle, punch, kick and guard from front and side, **and the live fight** (the
preview and the fight are different windows).

## Measure, do not eyeball

Several fixes here were redone because sizes were guessed from screenshots. Compare
numbers instead: read the blockout's per-group boxes from `model_meshes.h` and the
Meshy output from `meshy_meshes.h` (width, height, depth per group and the head's
aspect ratio), and only then look at renders. The script prints the width and head
fits it applied.

## Pitfalls hit

- **Shared sprites.** Different animations (other inputs, enhancement levels, states) often
  use identical frames; Shadow's slide (21) uses the same sprites as its idle (11). Compare
  sprite content with `sprite_duplicates.py` before authoring, and before concluding that a
  move is missing or wrong.
- **Draw cap.** `VERT_CAP` in `main.c` limits vertices per frame. Two Meshy models
  exceeded the old 120,000, and the legs, drawn last, silently disappeared. It is now
  400,000; raise it again if triangle counts grow.
- **PowerShell.** `$args` is an automatic variable: do not assign it, and splat
  `@runArgs`. Python on Windows needs Windows paths; Git Bash paths fail.
- **Building.** `cmake` is not on `PATH`; `run-meshy.ps1` calls it from the Visual
  Studio Build Tools after `VsDevCmd.bat`. The `vswhere.exe` message it prints is
  harmless.
- **Group boxes lie.** Spikes inflate blockout and mesh boxes (Shadow's shin box is
  1.56 wide because of spikes), and joint balls add height to the feet. Use
  percentile extents and pick groups that are not spiky (thighs, upper arms).
- **Per-group fitting** (own scale per group) breaks seams; fit as a function of height.
- **Feet.** The Jester's foot spikes pointed sideways, so kicks showed no foot from the
  side. `align_feet` turns each foot about the ankle so its longest spike points
  forward, and the toe is stretched to the blockout foot's forward reach. Its lateral
  spikes still make the feet wider than the blockout's.
- **Stale builds.** `run-meshy.ps1` throws on a failed build, but piping it through
  `tail` hides that and old captures get reused. Check for "build failed" before
  trusting a capture.
- **Replay check.** Preview poses are not the live poses. Compare recorded fights with
  `omf3d_prototype.exe --source-replay build/omf_trace_z7/<trace>.csv --capture-tick N`
  with and without `OMF3K_MESHY=1` (e.g. `shadow-assets-live-enhanced.csv` tick 304 is a
  Shadow kick, `shadow-special-far-v4.csv` tick 138 a Shadow projectile).

## Open items

- Jester torso depth (.55 against Shadow's 1.17) and pelvis width are not fitted.
- Both feet are taller than the blockouts' (.38 against .26).
- The Meshy heads have no face features; the blockouts have Shadow's face opening and
  eyes. The Jaguar Meshy head (`head_wedge`) is stretched to the blockout helmet's height,
  tapered to the canonical wedge, and given the blockout's green eye slabs; `head_cull_x` drops the horn that was fused to its upper corner. The Shadow Meshy head takes the blockout's dark face void and eyes (`head_features`) and a dark collar (`head_collar`) over its ragged lower rim, and is fitted to the blockout helmet rather than the helmet plus neck ribs.
- Record Meshy asset terms and provenance before shipping an adapted mesh (see
  [README.md](README.md)).
