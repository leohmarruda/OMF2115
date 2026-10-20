# Jaguar and Shadow blockout review — 2026-10-11

**Historical review:** this documents the earlier procedural silhouettes.
Editable Jaguar and Shadow blockouts later replaced them and were accepted for
the prototype milestone on 2026-10-14. See the
[current model match review](OMF3K_MODEL_MATCH_REVIEW.md) for the present
status and recorded-match findings.

This is a visual review of the then-current procedural blockouts, not approval of final
meshes or animation. The [Jaguar](../robots/jaguar/canonical/README.md) and
[Shadow](../robots/shadow/canonical/README.md) three-view sets are the approved
shape references. The source replay is `build/omf_trace_z7/6p-trace.csv`.

## Captures

Run `build/omf_debug_z7/omf3d_prototype.exe --model-preview-capture` from the
repository root to recreate the [front](../build/omf3d_model_front.bmp),
[back](../build/omf3d_model_back.bmp), and
[right-side](../build/omf3d_model_side.bmp) views. These captures show both
robots at the same display scale. The fight-camera captures are
[neutral, tick 125](../build/omf3d_review_tick_125_updated.bmp),
[Jaguar punch, tick 128](../build/omf3d_review_tick_128_updated.bmp), and
[recovery, tick 131](../build/omf3d_review_tick_131_updated.bmp). The match images
come from `--source-replay ... --capture-tick N`; they do not change source
combat. Generated captures stay in the ignored local `omf3k/build/` folder.

## Initial findings and corrections

| Priority | Robot / view | Observed difference | Correction and acceptance check |
| --- | --- | --- | --- |
| 1 | Both, fight camera | The models occupy a small part of the frame. Jaguar's head and torso become a rectangular column; Shadow's face, ribbing, and hand spikes are nearly lost. | Strengthen the profile silhouettes at the existing camera distance before adding detail. Compare neutral and punch frames at native 960×600; each robot must remain recognizable without the name label. |
| 1 | Jaguar, front and side | The helmet is a tall flat trapezoid with tiny rectangular eyes. The approved head is wider, lower, and faceted, with a forward visor-like side profile. | Widen and lower the helmet, shape the brow and front wedge, and retain two narrow green eyes. Check front and right-side captures together. |
| 1 | Shadow, front and side | The black face reads as a small rectangular inset; the approved opening fills the lower helmet and has a tapered, hollow profile. | Enlarge and recess the opening, taper it below the eyes, and keep the back of the head solid silver. Verify that the eye and opening remain visible in the fight camera. |
| 1 | Shadow, front and back | The triangular upper plate reads as a broad horizontal bar with small tips. The approved plate has a deep center point and long, sharp outer tips. | Deepen the inverted center and extend the pointed silhouette without hiding the arm joints. Review both front and back at equal scale. |
| 2 | Shadow, front, back, and side | Most of the arms and legs are smooth gray bars; the approved dark ribbed structure and framing armor are not distinct. The elbow and knee spikes are visible but small at fight distance. | Expose ribbed sections between silver armor pieces and increase the side silhouette of the spikes. Check that articulation remains clear in guard and crouch. |
| 2 | Jaguar, front and back | The chest emblem is a tiny mark and the upper body lacks the approved layered wedge. The back is a single flat panel; the rear helmet's required two-panel seam is absent. | Make the front chest wedge and small head emblem readable in close view; give the back its own panel construction and the head one central seam. Keep face details and emblem off the back. |
| 2 | Jaguar and Shadow, side | Hands and feet collapse into thin vertical shapes. Jaguar's two fingers and thumb, Shadow's three tapered spikes, and both robots' angular feet need more depth. | Separate the hand forms and build a clear toe/heel profile. Verify neutral and attack poses at fight distance. |

The punch capture confirms that Jaguar's arm extends and recovers on the
recorded source ticks. This review assesses its visible silhouette only; it
does not establish hit range or approve the pose fit. The back and side views
also reveal shape differences that a single fight-camera image would miss.

## First correction pass

The procedural model now gives Jaguar a wider, lower helmet, projecting brow,
and narrower lower face. Shadow has a larger tapered black opening under a
silver brow and a deeper triangular plate on both sides of the torso. The
fresh captures show these forms in all three views. The black opening is now
visible in profile, and the plate's lower point is visible from front and back.
The source-driven punch still extends and recovers on the same captured ticks;
this was a presentation-only change.

At the actual fight camera, the new head shapes are only a few pixels wide.
Shadow's ribbing and Jaguar's chest emblem remain hard to read in this first
fight capture. The next pass addresses those details and the camera scale.

## Second correction and framing pass

Jaguar now has a larger front chest wedge and emblem, a seam between the two
rear helmet panels, three staggered hand digits, and longer angular feet.
Shadow now has visible rib bands on the forearms and shins, three separated
hand spikes in profile, and longer feet. These are blockout shapes, not final
surface detail or source-frame pose fits.

The source-driven fight camera uses a closer presentation scale while fighter
positions, collision, inputs, and attack reach stay with OpenOMF. The updated
[punch at tick 128](../build/omf3d_review_tick_128_updated.bmp),
[guard at tick 128](../build/omf3d_review_guard_128.bmp), and
[kick at tick 129](../build/omf3d_review_kick_129.bmp) fit on screen.
The [jump apex at tick 136](../build/omf3d_review_jump_136.bmp) exposed a
HUD overlap in the first framing attempt; a higher camera follow position
cleared it while keeping the grounded fighter above the lower controls.
The [guard](../build/omf3d_model_guard.bmp),
[crouch](../build/omf3d_model_crouch.bmp), and
[kick](../build/omf3d_model_kick.bmp) close views show connected joints and
readable hand/foot silhouettes. The close crouch is a pose preview; a source
crouch trace has not yet been compared frame by frame.

## Gate decision

**Visual blockout review: candidate for human playtest.** Jaguar and Shadow
are distinguishable at the fight camera in the captured poses, and the HUD no
longer overlaps the sampled jump apex. B09–B10 remain open until the editable
model sources and a live playtest confirm the shapes through motion. The
remaining art gaps are the rear Jaguar armor construction, finer Shadow limb
framing, and source-matched poses beyond Jaguar's punch. Those details should
be checked before rigging or detailed surfacing.
