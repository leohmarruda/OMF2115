# Shadow standing attacks — source replay and pose pass

The local `build/omf_trace_z7/result-v2-live.csv` recording shows Shadow
using animation 42 for its standing kick and animation 43 for its standing
punch. The local `omf3k/build/pose-inventory.csv` confirms their AF inputs are `K`
and `P`, respectively. Jaguar uses different animation numbers, so the 3D
adapter now classifies these moves by both HAR and animation ID.

| Move | Completed ticks | Source sprite sequence | Observed contact |
| --- | --- | --- | --- |
| Kick, animation 42 | 92–106 | 1 (92–93), 2 (94–95), 3 (96–98), 2 (99–101), 1 (102–104), 0 (105–106) | Jaguar health fell from 213 to 183 at tick 97. |
| Punch, animation 43 | 163–175 | 0 (163), 1 (164–166), 2 (167–170), 1 (171–173), 0 (174–175) | Jaguar health fell from 142 to 112 at tick 170. |

The 3D blockout now selects four kick poses for the front leg and arm, and
three punch poses for the active arm. OpenOMF still controls contact, damage,
and timing. The fit was checked in local fight-camera captures:
`omf3k/build/omf3d_shadow_kick_92.bmp`, `_96.bmp`, `_105.bmp`, and
`omf3k/build/omf3d_shadow_punch_163.bmp`, `_167.bmp`, `_174.bmp`.

These are live-source observations, not isolated move fixtures. In the
recorded match, Shadow's animation 42 kick occupies ticks 92–106 and Jaguar's
HP falls 213→183 at tick 97. Shadow's animation 43 punch occupies ticks
163–175 and Jaguar's HP falls 142→112 at tick 170. The corresponding source
frames are in `build/omf_trace_z7/result-v2-live.csv`; the match result and
Stadium wall response are documented in the
[Stadium and full-match baseline](OMF3K_STADIUM_BASELINE.md). The recording
establishes timing for this match only; its spacing and input history are not
controlled enough to infer general range or startup values.

The original indexed sprites in `omf3k/build/pose-reference/shadow/42/` and `/43/`
were matched by pixel fingerprint to the exact higher-resolution frames in
[OMF 2097 Remastered](https://github.com/Jared-woodruff/OMF-2097-Remastered).
The HD kick frames show a longer knee chamber and a downward full extension;
the HD punch frames show an arm already extended on sprite 0. Those details
informed the revised joint positions. The Remastered blue armor, red details,
and palette differ from the approved OMF3K Shadow design, so this comparison
guides pose only. The fit remains a blockout pending live readability review.
Keep reference artwork out of distributable OMF3K assets until its terms are
verified.
