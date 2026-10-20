"""Generate the OMF3K move catalog for Jaguar and Shadow.

Joins the local animation inventory (omf3k/build/pose-inventory.csv, from pose_inventory.py),
the authored pose catalog (pose_catalog.csv), the recorded source traces in
build/omf_trace_z7, and the hand-kept move_names.csv. Writes
omf3k/docs/OMF3K_MOVE_CATALOG.md and omf3k/build/move-catalog.csv.

    python omf3k/tools/generate_move_catalog.py
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402
import sprite_duplicates  # noqa: E402

ROOT = paths.ROOT
INVENTORY = paths.ARTIFACTS / "pose-inventory.csv"
TRACES = paths.TRACE_DIR
DOC = paths.DOCS / "OMF3K_MOVE_CATALOG.md"
CSV_OUT = paths.ARTIFACTS / "move-catalog.csv"
HARS = {0: "Jaguar", 1: "Shadow"}
DIRECTIONS = {"1": "down-back", "2": "down", "3": "down-forward", "4": "back", "5": "neutral",
              "6": "forward", "7": "up-back", "8": "up", "9": "up-forward"}
BUTTONS = {"P": "punch", "K": "kick"}
SYSTEM_INPUTS = {"!": "triggered by the game (reaction, recovery, projectile)",
                 "n": "state animation", "0": "state animation"}


def decode_input(code: str) -> tuple[str, str]:
    """Return (kind, text). Codes are a button letter then numpad directions, or a flag."""
    match = re.fullmatch(r"([PK])(\d*)", code)
    if not match:
        return ("system", SYSTEM_INPUTS.get(code, code or "-"))
    button, dirs = BUTTONS[match.group(1)], match.group(2)
    if not dirs:
        return ("basic", button)
    if len(dirs) == 1:
        return ("basic", f"{DIRECTIONS[dirs]} + {button}")
    return ("special", f"{button} after directions {'-'.join(dirs)} (numpad order stored by the game)")


def load_inventory():
    if not INVENTORY.exists():
        subprocess.run([sys.executable, str(HERE / "pose_inventory.py")], check=True)
    with INVENTORY.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if int(r["har"]) in HARS]


def load_authored():
    count = defaultdict(int)
    with (paths.DATA / "pose_catalog.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            count[(int(r["har"]), int(r["animation"]))] += 1
    return count


def load_traces():
    """(har, animation) -> (frames, trace file, a mid-move tick) for the trace showing it longest."""
    found = defaultdict(lambda: defaultdict(list))
    for path in sorted(TRACES.glob("*.csv")):
        try:
            with path.open(newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    try:
                        if r.get("har") in ("0", "1"):
                            found[(int(r["har"]), int(r["animation"]))][path.name].append(int(r["tick"]))
                    except (TypeError, ValueError):      # truncated or malformed trace row
                        continue
        except (OSError, UnicodeDecodeError):
            continue
    best = {}
    for key, by_file in found.items():
        name = max(by_file, key=lambda n: len(by_file[n]))
        ticks = sorted(by_file[name])
        best[key] = (sum(len(t) for t in by_file.values()), name, ticks[len(ticks) // 2])
    return best


def load_names():
    with (paths.DATA / "move_names.csv").open(newline="", encoding="utf-8") as f:
        return {(int(r["har"]), int(r["animation"])): r for r in csv.DictReader(f)}


def build():
    inventory, authored, traces, names = load_inventory(), load_authored(), load_traces(), load_names()
    shared = defaultdict(list)                     # (har, animation) -> other animations with the same sprites
    for g in sprite_duplicates.groups(inventory):
        for m in g["members"]:
            shared[(g["har"], m["animation"])] = [(o["animation"], o["match"]) for o in g["members"]
                                                  if o["animation"] != m["animation"]]
    rows = []
    for r in inventory:
        har, anim, sprites = int(r["har"]), int(r["animation"]), int(r["sprites"])
        code = r["input"].strip('"')
        kind, text = decode_input(code)
        named = names.get((har, anim))
        done = authored.get((har, anim), 0)
        seen = traces.get((har, anim))
        rows.append({
            "har": har, "har_name": HARS[har], "animation": anim, "sprites": sprites,
            "input_code": code, "kind": kind, "input": text,
            "name": named["name"] if named else (text[0].upper() + text[1:] if kind == "basic" else ""),
            "name_confidence": named["confidence"] if named else ("decoded" if kind == "basic" else ""),
            "same_sprites_as": " ".join(f"{a}{'' if k == 'identical' else '~'}" for a, k in shared[(har, anim)]),
            "authored_sprites": done,
            "status": "authored" if done >= sprites else "partial" if done else "generic",
            "trace_frames": seen[0] if seen else 0, "trace": seen[1] if seen else "",
            "trace_tick": seen[2] if seen else "",
        })
    return rows


def replay_command(row):
    return (f"omf3d_prototype.exe --source-replay build/omf_trace_z7/{row['trace']} "
            f"--capture-tick {row['trace_tick']}")


def write_markdown(rows):
    out = ["# OMF3K move catalog", "",
           "Generated by `omf3k/prototype/generate_move_catalog.py` from the local animation inventory,",
           "`pose_catalog.csv`, the recorded source traces and `move_names.csv`. Do not edit by hand;",
           "add names to `move_names.csv` and regenerate.", "",
           "**Status.** *authored*: every sprite has a pose in `pose_catalog.csv`. *partial*: some do.",
           "*generic*: the viewer shows only the shared rough pose, so the move barely reads.",
           "**Trace** is a recorded fight containing the move (`--source-replay`); *none* means it can",
           "only be seen by performing it in a live fight. Input directions are numpad digits",
           "(4 back, 6 forward, 2 down, 8 up).", ""]
    for har, har_name in HARS.items():
        mine = [r for r in rows if r["har"] == har]
        player = [r for r in mine if r["kind"] in ("basic", "special")]
        out += [f"## {har_name}", "",
                f"{len(player)} player-triggered animations: "
                f"{sum(r['status'] == 'authored' for r in player)} authored, "
                f"{sum(r['status'] == 'partial' for r in player)} partial, "
                f"{sum(r['status'] == 'generic' for r in player)} generic; "
                f"{sum(r['trace_frames'] > 0 for r in player)} appear in a recorded trace.", "",
                "| Anim | Move | Input | Sprites | Status | Trace |", "| --- | --- | --- | --- | --- | --- |"]
        for r in player:
            label = r["name"] or "unnamed special"
            if r["name_confidence"] in ("likely", "decoded"):
                label += f" ({r['name_confidence']})"
            if r["same_sprites_as"]:
                label += f"; same sprites as {r['same_sprites_as'].replace(' ', ', ')}"
            trace = f"`{r['trace']}` tick {r['trace_tick']}" if r["trace_frames"] else "none"
            out.append(f"| {r['animation']} | {label} | `{r['input_code']}`: {r['input']} | {r['sprites']} | "
                       f"{r['status']} ({r['authored_sprites']}/{r['sprites']}) | {trace} |")
        todo = [r for r in player if r["status"] != "authored"]
        out += ["", f"### {har_name}: author next", "",
                "Player-triggered and not fully authored. Moves already in a trace come first, since they",
                "can be checked without playing a fight.", ""]
        for r in sorted(todo, key=lambda r: (r["trace_frames"] == 0, r["animation"])):
            how = f"replay `{replay_command(r)}`" if r["trace_frames"] else "perform it in a live fight"
            out.append(f"- anim {r['animation']} {r['name'] or '(unnamed)'}, {r['sprites']} sprites; {how}; "
                       f"sprites: `pose_inventory.py --har {har} --animation {r['animation']} --export-sprites`")
        system = [r for r in mine if r["kind"] == "system"]
        out += ["", f"### {har_name}: other animations", "",
                "Reactions, recoveries, projectiles and state animations "
                f"({len(system)}): " + ", ".join(
                    f"{r['animation']}{'' if r['status'] == 'generic' else '*'}" for r in system) + ".",
                "(* = authored or partial.)", ""]
    out += ["## Animations that share sprites", "",
            "Several animations draw exactly the same frames (different input, enhancement level or"
            " state). Author a sprite's pose once and reuse it for every animation in its group."
            " `~` marks a partial overlap. *Free wins* have an authored member and unauthored ones.", ""]
    for har, har_name in HARS.items():
        by_key = {(r["har"], r["animation"]): r for r in rows}
        groups = {}
        for r in rows:
            if r["har"] == har and r["same_sprites_as"]:
                members = sorted({r["animation"], *(int(x.rstrip("~")) for x in r["same_sprites_as"].split())})
                groups[tuple(members)] = members
        out += [f"### {har_name}", "", "| Animations | Sprites | Inputs | Status | Note |", "| --- | --- | --- | --- | --- |"]
        for members in sorted(groups.values()):
            rs = [by_key[(har, a)] for a in members]
            status = ", ".join(f"{r['animation']}: {r['status']}" for r in rs)
            done = [r for r in rs if r["status"] == "authored"]
            note = ("free win: reuse the authored poses" if done and len(done) < len(rs)
                    else "author once" if not done else "all authored")
            out.append(f"| {', '.join(map(str, members))} | {max(r['sprites'] for r in rs)} | "
                       f"{', '.join('`' + r['input_code'] + '`' for r in rs)} | {status} | {note} |")
        out.append("")
    out += ["## Seeing a move", "",
            "- **Browser:** `python omf3k/tools/generate_move_browser.py` builds `omf3k/build/move-browser/index.html`,"
            " which lines up each original sprite with the blockout and Meshy renders of the same frame"
            " (moves that appear in a trace only).",
            "- **Original sprites:** `python omf3k/tools/pose_inventory.py --har H --animation N --export-sprites`"
            " writes `omf3k/build/pose-reference/<har>/N/sprite-NN.png`.",
            "- **Blockout vs Meshy, from a trace:** run the replay command above once normally and once with"
            " `OMF3K_MESHY=1`.",
            "- **Live:** `omf3k/scripts/run-live.ps1` for blockouts, `run-meshy-fight-jaguar.ps1` and"
            " `run-meshy-fight-shadow.ps1` for the Meshy models.", ""]
    DOC.write_text("\n".join(out), encoding="utf-8")


def main():
    rows = build()
    CSV_OUT.parent.mkdir(exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    write_markdown(rows)
    print(f"{len(rows)} animations -> {DOC.relative_to(ROOT)}, {CSV_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
