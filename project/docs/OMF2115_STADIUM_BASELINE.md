# Stadium and full-match source baseline

These measurements extend the Jaguar–Shadow source baseline with Stadium wall
response and one complete source-driven match. They come from OpenOMF's
end-of-dynamic-tick trace, not from prototype collision rules. CSVs and images
remain in the ignored local `build/` and `project/build/` directories; the original `.REC` fixtures
were not changed.

## Stadium wall response

Both fixtures use Crystal/Jaguar against Shirro/Electra, arena 0 (Stadium),
hazards enabled, and the source's default match settings. They were replayed
with the null renderer and audio backend at speed 10 (28 ms per source tick).
Player 1 in the trace is Electra. State 15 is `STATE_WALLDAMAGE` in
`src/game/objects/har.h`.

| Fixture | Source observation | Result |
| --- | --- | --- |
| `STADIUM-WALL-SPLAT.REC` | Electra reaches x=300 at tick 133. A later hit at tick 204 reduces HP 196→166 while the x position remains clamped at 300; Electra enters recoil (state 7) with vx=4.8, vy=-7.2. | The right edge constrains fighter position during knockback. |
| Same fixture | At tick 356 another hit reduces Electra HP 165→123 at x=287.4, y=135, with vx=8, vy=-4. At tick 359 Electra stops at x=298, y=127 and enters state 15 / animation 9 / sprite 16. State 15 persists through tick 364 with no further HP change in this sample. | The `.REC` assertion for state 15 passes; the trace records the wall-damage response after the hit. |
| `POWERPLANT-WALL-SPLAT.REC` | The comparison fixture reaches x=300; a hit at tick 435 reduces HP 189→159. At tick 437 Electra stops at x=298, y=175 in state 15 / animation 9 / sprite 16. | The same wall-damage state is observed in arena 2, at a different vertical position. |

The Stadium fixture was repeated. The wall-contact positions, HP changes, and
state transitions above matched; one run continued one additional source tick
after the final assertion (tick 365 rather than 364), so the complete CSVs are
not byte-identical.

Local trace files are `build/omf_trace_z7/stadium-wall-splat-trace.csv` and
`build/omf_trace_z7/powerplant-wall-splat-trace.csv`. The 3D source-replay
captures are [Stadium wall damage at tick 359](../build/mesh-match-ticks/stadium-walldamage-359.png)
and [Power Plant wall damage at tick 437](../build/mesh-match-ticks/powerplant-walldamage-437.png).

## Prototype Stadium blockout

The source-based reference describes Stadium as an enclosed, hazard-free
testing arena with spectators. The prototype now represents those cues with a
roofed bowl, four stepped seating tiers, abstract custom-geometry spectators,
a central arena board, perimeter lights, and a quiet hazard-free fighting
floor. This is newly authored blockout geometry, not a copy of the original
arena art. The [current fight-camera capture](../build/mesh-match-ticks/stadium-crowd-blockout.bmp)
shows the layout behind both accepted HAR silhouettes.

## Complete Jaguar–Shadow source match

The generated `build/omf_trace_z7/jaguar-shadow-baseline-live.csv` contains a
complete live-source match on Stadium: ticks 0–471, with player 1 declared the
winner at tick 376. Player 0 was Crystal/Jaguar (213 starting HP); player 1 was
Shirro/Shadow (196 starting HP). The recorded test fed Jaguar alternating
punch (`0x04`) and stop (`0x01`) input pulses at speed 10. This is a driven
source sample, not a human-playtest result or a reusable input recording.

The source reports Jaguar's HP changing 213→172 at tick 114, 172→131 at 166,
131→70 at 239, 70→40 at 331, then 40→−21 on the winning tick 376. Shadow
remains at 196 HP. The final negative value is OpenOMF's raw overkill state;
the 3D replay adapter now accepts it and displays health as zero. The full
trace passes `omf3d_prototype --source-replay-check` and is replayable through
the prototype. A local result capture is available at
[the declared match result](../build/mesh-match-ticks/source-live-result-376.png).

## Reproduction

From the repository root, in the documented Visual Studio x64 developer
environment, build `openomf` from `build/omf_trace_z7` with
`OMF3K_SOURCE_TRACE=ON`. Set `OPENOMF_RESOURCE_PATH`, `OPENOMF_STATE_PATH`,
and `OPENOMF_CONFIG_PATH` to `.` in the build directory, then run:

```powershell
$env:OPENOMF_RESOURCE_PATH='.'
$env:OPENOMF_STATE_PATH='.'
$env:OPENOMF_CONFIG_PATH='.'
$env:OMF3K_TRACE_PATH='stadium-wall-splat-trace.csv'
.\openomf.exe --force-renderer=NULL --force-audio-backend=NULL --speed=10 -P ..\..\rectests\STADIUM-WALL-SPLAT.REC
```

Use `POWERPLANT-WALL-SPLAT.REC` and a different `OMF3K_TRACE_PATH` for the
comparison. The fixtures assert the expected wall-response states and exit
normally. The full match trace was produced through `--omf3k-live` with a
timestamped input file; its state replay is preserved locally as the CSV.

## Still required

The source baselines now cover signature moves, selected grounded attacks,
Stadium wall response, and a complete source-driven result. Jaguar and Shadow
still need isolated range and guard/stun checks for the remaining moves, plus a
human-played visual review of a complete match and the Stadium presentation.
