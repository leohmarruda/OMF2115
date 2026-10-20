"""Find animations that use the same sprites.

OpenOMF HARs reuse sprite sets: several animations (different inputs, enhancement levels or
states) draw the same frames. This exports every Jaguar and Shadow animation's sprites if
needed, hashes each sprite's visible pixels (cropped to its content, so differing canvas
offsets do not matter) and groups the animations that share sprites.

    python omf3k/tools/sprite_duplicates.py                  # prints the groups, writes omf3k/build/duplicate-sprites.json
    python omf3k/prototype/sprite_duplicates.py --write-groups   # also writes pose_sprite_groups.csv

pose_sprite_groups.csv lists, per group, the player-triggered animations that draw identical sprites.
generate_pose_catalog.py uses it so that an authored pose applies to every animation in its group.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402

ROOT = paths.ROOT
BUILD = paths.ARTIFACTS
SPRITES = BUILD / "pose-reference"
HAR_DIRS = {0: "jaguar", 1: "shadow"}


def export_all(inventory_rows):
    for r in inventory_rows:
        har, anim = int(r["har"]), int(r["animation"])
        folder = SPRITES / HAR_DIRS[har] / str(anim)
        if not any(folder.glob("sprite-*.png")):
            subprocess.run([sys.executable, str(HERE / "pose_inventory.py"), "--har", str(har),
                            "--animation", str(anim), "--export-sprites"], capture_output=True, cwd=ROOT)


def content_hash(path):
    import numpy as np
    from PIL import Image
    im = np.array(Image.open(path).convert("RGBA"))
    mask = (im[..., 3] > 0) & (im[..., :3].sum(-1) > 0)
    if mask.any():
        ys, xs = np.where(mask)
        im = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    else:
        im = im[:1, :1]
    return hashlib.md5(im.tobytes() + str(im.shape).encode()).hexdigest()[:10]


def sprite_sequences(inventory_rows):
    """(har, animation) -> list of content hashes in sprite order."""
    export_all(inventory_rows)
    seqs = {}
    for r in inventory_rows:
        har, anim = int(r["har"]), int(r["animation"])
        files = sorted((SPRITES / HAR_DIRS[har] / str(anim)).glob("sprite-*.png"))
        if files:
            seqs[(har, anim)] = [content_hash(f) for f in files]
    return seqs


def groups(inventory_rows):
    """Connected groups of animations sharing at least one identical sprite.

    Each member says whether its whole sprite sequence matches the group's first member.
    """
    seqs = sprite_sequences(inventory_rows)
    owners = defaultdict(list)
    for key, seq in seqs.items():
        for h in set(seq):
            owners[(key[0], h)].append(key)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for keys in owners.values():
        for other in keys[1:]:
            parent[find(keys[0])] = find(other)
    by_root = defaultdict(list)
    for key in seqs:
        if len(owners[(key[0], seqs[key][0])]) > 1 or any(len(owners[(key[0], h)]) > 1 for h in seqs[key]):
            by_root[find(key)].append(key)
    result = []
    for members in sorted(by_root.values(), key=lambda m: (m[0][0], min(a for _, a in m))):
        members.sort()
        base = seqs[members[0]]
        result.append({"har": members[0][0], "members": [
            {"animation": a, "sprites": len(seqs[(h, a)]),
             "match": "identical" if seqs[(h, a)] == base else "partial"} for h, a in members]})
    return result


def load_inventory():
    inventory = BUILD / "pose-inventory.csv"
    if not inventory.exists():
        subprocess.run([sys.executable, str(HERE / "pose_inventory.py")], check=True, cwd=ROOT)
    with inventory.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if int(r["har"]) in HAR_DIRS]


GROUPS_CSV = paths.DATA / "pose_sprite_groups.csv"


def player_animations():
    """(har, animation) of the player-triggered moves, from the move catalog."""
    catalog = BUILD / "move-catalog.csv"
    if not catalog.exists():
        subprocess.run([sys.executable, str(HERE / "generate_move_catalog.py")], check=True, cwd=ROOT)
    with catalog.open(newline="", encoding="utf-8") as f:
        return {(int(r["har"]), int(r["animation"])) for r in csv.DictReader(f) if r["kind"] in ("basic", "special")}


def write_groups(found):
    """Groups of player-triggered animations with identical sprites. Reaction and state animations are
    left out: a slide that reuses the idle frames must not receive the idle pose, or the reverse."""
    players = player_animations()
    rows = []
    for g in found:
        members = [m for m in g["members"] if m["match"] == "identical" and (g["har"], m["animation"]) in players]
        if len(members) >= 2:
            rows.append((g["har"], " ".join(str(m["animation"]) for m in members), min(m["sprites"] for m in members)))
    with GROUPS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("har", "animations", "sprites"))
        writer.writerows(rows)
    print(f"{len(rows)} player-triggered groups -> {GROUPS_CSV.name}")


def main():
    found = groups(load_inventory())
    (BUILD / "duplicate-sprites.json").write_text(json.dumps(found, indent=1), encoding="utf-8")
    for g in found:
        print(HAR_DIRS[g["har"]], ", ".join(f"{m['animation']}{'' if m['match'] == 'identical' else '~'}"
                                            for m in g["members"]))
    print(f"{len(found)} groups -> omf3k/build/duplicate-sprites.json (~ = only some sprites shared)")
    if "--write-groups" in sys.argv:
        write_groups(found)


if __name__ == "__main__":
    main()
