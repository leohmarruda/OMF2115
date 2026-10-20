"""Inventory local OpenOMF HAR animations and export selected reference sprites.

The original .AF files and exported PNGs stay in the ignored local build tree.
Only animation metadata is written to the inventory CSV.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402

ROOT = paths.ROOT
HAR_NAMES = (
    "Jaguar", "Shadow", "Thorn", "Pyros", "Electra", "Katana",
    "Shredder", "Flail", "Gargoyle", "Chronos", "Nova",
)
MOVE_HEADER = re.compile(r"Move #(\d+) information:")


def run_aftool(tool: Path, *args: str) -> str:
    result = subprocess.run([str(tool), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or
                           f"aftool exited with {result.returncode}")
    return result.stdout


def field(block: str, name: str) -> str:
    match = re.search(r"^ \* " + re.escape(name) + r":\s*(.*)$", block, re.MULTILINE)
    if not match:
        raise ValueError(f"aftool output is missing {name}")
    return match.group(1).strip()


def moves_for_har(tool: Path, af_file: Path, har: int) -> list[dict[str, str | int]]:
    output = run_aftool(tool, "-f", str(af_file), "-A")
    pieces = MOVE_HEADER.split(output)
    rows: list[dict[str, str | int]] = []
    for i in range(1, len(pieces), 2):
        block = pieces[i + 1]
        rows.append({
            "har": har,
            "name": HAR_NAMES[har],
            "animation": int(pieces[i]),
            "sprites": int(field(block, "Sprites")),
            "input": field(block, "Move string"),
            "script": field(block, "Animation str"),
        })
    if not rows:
        raise ValueError(f"No animations found in {af_file}")
    return rows


def export_sprites(tool: Path, game_data: Path, har: int, animation: int,
                   count: int, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    af_file = game_data / f"FIGHTR{har}.AF"
    palette = game_data / "ARENA0.BK"
    if not palette.is_file():
        raise FileNotFoundError(palette)
    for sprite in range(count):
        target = destination / f"sprite-{sprite:02d}.png"
        run_aftool(tool, "-f", str(af_file), "-p", str(palette),
                   "-m", str(animation), "-s", str(sprite),
                   f"--export-png={target}")
        if not target.is_file():
            raise RuntimeError(f"aftool did not create {target}")
    lines = [f"# {HAR_NAMES[har]} animation {animation}", "",
             "Local original-game reference frames. Keep these in the ignored build directory.", ""]
    lines.extend(f"- Sprite {sprite}: ![Sprite {sprite}](sprite-{sprite:02d}.png)"
                 for sprite in range(count))
    (destination / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_timelines(traces: list[Path], destination: Path) -> int:
    segments: list[dict[str, str | int]] = []
    for trace in traces:
        last: dict[int, dict[str, str | int]] = {}
        with trace.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                player = int(row["player"])
                tick = int(row["tick"])
                har = int(row["har"])
                animation = int(row["animation"])
                sprite = int(row["sprite"])
                animation_tick = int(row["animation_tick"])
                segment = last.get(player)
                if (segment is not None and segment["har"] == har and
                    segment["animation"] == animation and segment["sprite"] == sprite and
                    segment["last_tick"] == tick - 1):
                    segment["last_tick"] = tick
                    segment["last_animation_tick"] = animation_tick
                else:
                    segment = {
                        "trace": trace.name, "player": player, "har": har,
                        "animation": animation, "sprite": sprite,
                        "first_tick": tick, "last_tick": tick,
                        "first_animation_tick": animation_tick,
                        "last_animation_tick": animation_tick,
                    }
                    segments.append(segment)
                    last[player] = segment
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("trace", "player", "har", "animation",
                                                   "sprite", "first_tick", "last_tick",
                                                   "first_animation_tick", "last_animation_tick"))
        writer.writeheader()
        writer.writerows(segments)
    return len(segments)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aftool", type=Path, default=paths.AFTOOL)
    parser.add_argument("--game-data", type=Path, default=paths.GAME_DATA)
    parser.add_argument("--output", type=Path, default=paths.ARTIFACTS / "pose-inventory.csv")
    parser.add_argument("--har", type=int, choices=range(len(HAR_NAMES)))
    parser.add_argument("--animation", type=int)
    parser.add_argument("--export-sprites", action="store_true")
    parser.add_argument("--trace", type=Path, action="append", default=[],
                        help="Add an OpenOMF CSV trace to extract observed sprite holds")
    parser.add_argument("--timeline-output", type=Path,
                        default=paths.ARTIFACTS / "pose-timelines.csv")
    args = parser.parse_args()
    if args.export_sprites and (args.har is None or args.animation is None):
        parser.error("--export-sprites requires --har and --animation")
    if not args.aftool.is_file():
        parser.error(f"aftool is missing: {args.aftool}")
    rows: list[dict[str, str | int]] = []
    for har in range(len(HAR_NAMES)):
        af_file = args.game_data / f"FIGHTR{har}.AF"
        if not af_file.is_file():
            raise FileNotFoundError(af_file)
        rows.extend(moves_for_har(args.aftool, af_file, har))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("har", "name", "animation", "sprites", "input", "script"))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Inventoried {len(rows)} animations across {len(HAR_NAMES)} HARs: {args.output}")
    if args.export_sprites:
        match = next((row for row in rows if row["har"] == args.har and
                      row["animation"] == args.animation), None)
        if match is None:
            parser.error(f"HAR {args.har} has no animation {args.animation}")
        destination = args.output.parent / "pose-reference" / HAR_NAMES[args.har].lower() / str(args.animation)
        export_sprites(args.aftool, args.game_data, args.har, args.animation,
                       int(match["sprites"]), destination)
        print(f"Exported {match['sprites']} sprites: {destination}")
    if args.trace:
        count = write_timelines(args.trace, args.timeline_output)
        print(f"Recorded {count} observed sprite holds: {args.timeline_output}")


if __name__ == "__main__":
    main()
