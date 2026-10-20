"""Build a local HTML editor for fitting poses to the original sprites.

Each sprite shows the auto-fitted skeleton (Jaguar: from the palette joint markers, see
fit_poses.py), the pose already authored in pose_catalog.csv, or a rest-pose default (Shadow,
which has no joint markers). Drag the joints to match the sprite, tick the parts the pose
overrides, mark the sprite reviewed, then export a CSV and merge it:

    python project/tools/generate_pose_editor.py        # writes project/build/pose-editor/index.html
    (edit in the browser, then "Download pose rows")
    python project/tools/merge_pose_rows.py ~/Downloads/pose-rows.csv

One entry is made per group of animations that share sprites (sprite_duplicates.py); an
exported row is applied to every player-triggered animation in the group, never to reaction
or state animations, which may only share frames by coincidence of the data.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402
import fit_poses as fp  # noqa: E402
import match_remastered_frames as mrf  # noqa: E402
import sprite_duplicates  # noqa: E402

ROOT = paths.ROOT
BUILD = paths.ARTIFACTS
OUT = BUILD / "pose-editor"
# Rig heights (main.c model_transform) and the head-bottom height used for the neck landmark.
REST = {0: dict(ankle=.23, knee=.75, hip=1.30, shoulder=2.24, neck=2.86, elbow=1.76, wrist=1.13),
        1: dict(ankle=.24, knee=.76, hip=1.27, shoulder=2.25, neck=2.62, elbow=1.77, wrist=1.11)}
HAR_NAMES = {0: "Jaguar", 1: "Shadow"}
# Starting skeletons for frames with no joint markers (Shadow): the first frame of an authored pose, one
# for poses low to the ground and one for the rest. A frame counts as down when its silhouette is shorter
# than DOWN_RATIO of the idle sprite's (down poses measure 0.62 to 0.80, standing ones 0.88 and up).
REFERENCE = {1: {"down": (15, 0), "standing": (16, 0)}}
DOWN_RATIO = 0.85
# OMF 2097 Remastered's HD atlas, a sibling checkout. Its frames match the original sprites exactly by
# fingerprint (match_remastered_frames.py) at 5x horizontal and 6x vertical scale. The crops are local
# reference material under project/build/ and are not part of the repository.
HD_ROOT = paths.REMASTERED_HD
HD_OUT = OUT / "hd"
_hd = {"index": None, "pages": {}}


def hd_reference(har, anim, sprite, path):
    """The remastered frame for an original sprite, placed in the original sprite's pixel units."""
    from PIL import Image
    if not HD_ROOT.exists():
        return None
    if _hd["index"] is None:
        index = json.loads((HD_ROOT / "index.json").read_text(encoding="utf-8"))
        by_hash = defaultdict(list)
        for entry in index["entries"]:
            if entry["kind"] == "fighter":
                by_hash[entry["hash"]].append(entry)
        _hd["index"] = (by_hash, index["scale"]["x"], index["scale"]["y"])
    by_hash, sx, sy = _hd["index"]
    with Image.open(path) as image:
        matches = by_hash.get(mrf.pixel_hash(image))
    if not matches:
        return None
    want = f"fighter-{HAR_NAMES[har].upper()}"
    entry = next((e for e in matches if e["bundle"] == want), matches[0])
    target = HD_OUT / f"h{har}_a{anim}_s{sprite}.webp"
    if not target.exists():
        key = (entry["bundle"], entry["page"])
        if key not in _hd["pages"]:
            _hd["pages"][key] = Image.open(HD_ROOT / entry["bundle"] / f"page_{entry['page']}.webp")
        HD_OUT.mkdir(parents=True, exist_ok=True)
        box = (entry["x"], entry["y"], entry["x"] + entry["w"], entry["y"] + entry["h"])
        _hd["pages"][key].crop(box).save(target, lossless=True, quality=100, method=4)
    pad = entry["pad"] / 2                      # the crop carries a small margin around the scaled sprite
    return {"img": os.path.relpath(target, OUT).replace("\\", "/"), "x": round(-pad / sx, 3),
            "y": round(-pad / sy, 3), "w": round(entry["w"] / sx, 3), "h": round(entry["h"] / sy, 3)}


def load_authored():
    rows = {}
    with (paths.DATA / "pose_catalog.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[(int(r["har"]), int(r["animation"]), int(r["sprite"]))] = r
    return rows


def ymap_for(har, jaguar_rest):
    px = [float(v) for v in jaguar_rest.ymap[0]]
    r = REST[har]
    return {"px": px, "rig": [r["ankle"], r["knee"], r["hip"], r["shoulder"], r["neck"]]}


def to_rig_y(ymap, y):
    px, rig = ymap["px"], ymap["rig"]
    if y > px[-1]:
        return rig[-1] + (y - px[-1]) * (rig[-1] - rig[-2]) / (px[-1] - px[-2])
    if y < px[0]:
        return rig[0] + (y - px[0]) * (rig[1] - rig[0]) / (px[1] - px[0])
    return float(np.interp(y, px, rig))


def to_px_y(ymap, y):
    px, rig = ymap["px"], ymap["rig"]
    if y > rig[-1]:
        return px[-1] + (y - rig[-1]) * (px[-1] - px[-2]) / (rig[-1] - rig[-2])
    if y < rig[0]:
        return px[0] + (y - rig[0]) * (px[1] - px[0]) / (rig[1] - rig[0])
    return float(np.interp(y, rig, px))


def silhouette_axis(har, anim, sprite, ymap):
    """Torso axis for sprites without markers: mean x of the silhouette between hip and shoulder height."""
    image, indices = fp.load_sprite(har, anim, sprite)
    ox, oy = fp.sprite_offset(har, anim, sprite)
    rows = np.arange(indices.shape[0])
    y_up = -(oy + rows + .5)
    band = (y_up >= ymap["px"][2]) & (y_up <= ymap["px"][3])
    cols = np.where((indices[band] > 0).any(axis=0))[0]
    if band.any() and (indices[band] > 0).any():
        xs = np.where(indices[band] > 0)[1]
        return float(ox + np.mean(xs) + .5)
    return float(ox + indices.shape[1] / 2)


def content_height(path):
    """Height in pixels of the sprite's visible part."""
    from PIL import Image
    rows = np.where((np.array(Image.open(path)) > 0).any(axis=1))[0]
    return int(rows.max() - rows.min() + 1)


def spine_neck(skel, row, ymap):
    """The neck: a standing spine's length above the pelvis, tilted by the row's lean if it has one."""
    neck = [skel["pelvis"][0], round(skel["pelvis"][1] + ymap["px"][4] - ymap["px"][2], 1)]
    if row and row.get("lean"):
        rise = to_rig_y(ymap, neck[1]) - to_rig_y(ymap, skel["pelvis"][1])
        neck[0] = round(skel["pelvis"][0] + float(row["lean"]) * rise / fp.SIDE_UNITS, 1)
    return neck


def default_skeleton(har, axis, ymap):
    """Rest pose in sprite pixels: arm hanging from the shoulder, legs standing."""
    r = REST[har]
    k = fp.SIDE_UNITS

    def px(y, z):
        return [round(axis - z / k, 1), round(to_px_y(ymap, y), 1)]

    return dict(pelvis=px(r["hip"], 0), shoulder=px(r["shoulder"], 0),
                elbow=px(r["elbow"], -.02), wrist=px(r["wrist"], -.08),
                elbow2=px(r["elbow"], -.02), wrist2=px(r["wrist"], -.08),
                legs=[dict(knee=px(r["knee"], 0), ankle=px(r["ankle"], -.02)),
                      dict(knee=px(r["knee"], 0), ankle=px(r["ankle"], -.02))])


def authored_skeleton(har, row, axis, ymap, base):
    """Pose row -> sprite pixels (inverse of the export mapping)."""
    k = fp.SIDE_UNITS

    def px(y, z):
        return [round(axis - float(z) / k, 1), round(to_px_y(ymap, float(y)), 1)]

    flags = row["flags"].split("|")
    skel = json.loads(json.dumps(base))
    drop = float(row["body_y"]) if "drop" in flags and row.get("body_y") else 0.0   # arm heights are relative to it
    if "arm" in flags:
        skel["elbow"] = px(float(row["elbow_y"]) + drop, row["elbow_z"])
        skel["wrist"] = px(float(row["wrist_y"]) + drop, row["wrist_z"])
    if "arm2" in flags:
        skel["elbow2"] = px(float(row["elbow2_y"]) + drop, row["elbow2_z"])
        skel["wrist2"] = px(float(row["wrist2_y"]) + drop, row["wrist2_z"])
    if "drop" in flags:
        skel["pelvis"][1] = round(to_px_y(ymap, REST[har]["hip"] + drop), 1)
    if "leg" in flags:
        skel["legs"][0] = dict(knee=px(row["knee_y"], row["knee_z"]), ankle=px(row["ankle_y"], row["ankle_z"]))
    if "leg2" in flags:
        skel["legs"][1] = dict(knee=px(row["knee2_y"], row["knee2_z"]), ankle=px(row["ankle2_y"], row["ankle2_z"]))
    if "body" in flags:
        skel["pelvis"][0] = round(axis - float(row["body_z"]) / k, 1)
    return skel, flags


def auto_skeleton(har, anim, sprite, rest, axis_fallback):
    """Jaguar: markers -> skeleton in sprite pixels, plus the torso axis. None if too few markers."""
    found = fp.blobs(har, anim, sprite)
    if len(found) < 6:
        return None
    skel = fp.label(found, rest)
    arm = max(skel.arms, key=lambda a: a[2][0])
    other_arm = next(a for a in skel.arms if a is not arm)
    legs = sorted(skel.legs, key=lambda l: -(l[2][0] - skel.pelvis[0]) - max(l[2][1] - rest.ymap[0][0], 0) * .5)
    axis = (skel.neck[0] + skel.pelvis[0]) / 2
    r = lambda p: [round(float(p[0]), 1), round(float(p[1]), 1)]
    return axis, dict(pelvis=r(skel.pelvis), shoulder=r(skel.shoulder), elbow=r(arm[1]), wrist=r(arm[2]),
                      elbow2=r(other_arm[1]), wrist2=r(other_arm[2]),
                      legs=[dict(knee=r(l[1]), ankle=r(l[2])) for l in legs]), fp.confidence(skel, rest), r(skel.neck)


def build():
    inventory = sprite_duplicates.load_inventory()
    catalog = list(csv.DictReader((BUILD / "move-catalog.csv").open(newline="", encoding="utf-8")))
    player = {(int(r["har"]), int(r["animation"])): r for r in catalog if r["kind"] in ("basic", "special")}
    names = {k: (r["name"] or "unnamed special") for k, r in player.items()}
    authored = load_authored()
    rest = fp.measure_rest(0)
    ymaps = {har: ymap_for(har, rest) for har in HAR_NAMES}
    sprite_duplicates.export_all(inventory)
    # rig z = 0 is the idle torso line: Jaguar's idle pelvis marker, Shadow's idle silhouette
    axis_x = {0: float(rest.pelvis_x), 1: float(silhouette_axis(1, 11, 0, ymaps[1]))}

    idle_height = {har: content_height(BUILD / "pose-reference" / fp.HAR_DIRS[har] / "11" / "sprite-00.png")
                   for har in HAR_NAMES}
    shared = defaultdict(set)                        # canonical player animation -> other player animations
    system_shared = defaultdict(list)
    covered = set()
    for g in sprite_duplicates.groups(inventory):
        members = [m["animation"] for m in g["members"] if m["match"] == "identical"]
        players = sorted(a for a in members if (g["har"], a) in player)
        if players:
            shared[(g["har"], players[0])] = set(players[1:])
            covered.update((g["har"], a) for a in players)
            system_shared[(g["har"], players[0])] = [a for a in members if (g["har"], a) not in player]
    entries = []
    for (har, anim), r in sorted(player.items()):
        if (har, anim) in covered and (har, anim) not in shared:
            continue                                    # a non-canonical member of a group
        sprites = []
        for sprite in range(int(r["sprites"])):
            path = BUILD / "pose-reference" / fp.HAR_DIRS[har] / str(anim) / f"sprite-{sprite:02d}.png"
            if not path.exists():
                continue
            from PIL import Image
            width, height = Image.open(path).size
            ox, oy = fp.sprite_offset(har, anim, sprite)
            ymap = ymaps[har]
            auto = auto_skeleton(har, anim, sprite, rest, None) if har == 0 else None
            note = ""
            axis = axis_x[har]
            if auto:
                _, skel, problems, neck = auto           # the markers' neck sets the spine
                source, note = "auto", "; ".join(problems)
                rise = to_rig_y(ymap, neck[1]) - to_rig_y(ymap, skel["pelvis"][1])
                tilt = (neck[0] - skel["pelvis"][0]) * fp.SIDE_UNITS / rise if rise > .6 else 99
                if abs(tilt) > .8:                      # an unreliable neck marker: start from a vertical spine
                    neck = [skel["pelvis"][0], round(skel["pelvis"][1] + ymap["px"][4] - ymap["px"][2], 1)]   # a standing spine above the pelvis
            else:
                skel, source = default_skeleton(har, axis, ymap), "default"
                neck = spine_neck(skel, None, ymap)
            flags = ["arm", "arm2", "leg", "leg2", "body"]
            row = authored.get((har, anim, sprite))
            if not auto and not row:                  # no markers and nothing authored: start from a reference pose
                kind = "down" if content_height(path) < DOWN_RATIO * idle_height[har] else "standing"
                ref_key = REFERENCE.get(har, {}).get(kind)
                ref = authored.get((har,) + ref_key) if ref_key else None
                if ref:
                    skel, flags = authored_skeleton(har, ref, axis, ymap, skel)
                    neck = spine_neck(skel, ref, ymap)
                    source, note = "reference", f"starts from {HAR_NAMES[har]} {ref_key[0]} frame {ref_key[1]} ({kind} pose)"
            if row:
                skel, flags = authored_skeleton(har, row, axis, ymap, skel)
                source, note = "authored", ""
                neck = spine_neck(skel, row, ymap)
            neck = [round(float(neck[0]), 1), round(float(neck[1]), 1)]
            skel["neck"] = neck             # one skeleton: pelvis - neck - head, with the limbs hanging off it
            skel["head"] = {"top": [neck[0], round(neck[1] + 11, 1)], "left": [round(neck[0] - 9, 1), round(neck[1] + 6, 1)],
                            "right": [round(neck[0] + 9, 1), round(neck[1] + 6, 1)]}
            sprites.append({"sprite": sprite, "img": os.path.relpath(path, OUT).replace("\\", "/"),
                            "w": width, "h": height, "ox": ox, "oy": oy, "axis": round(float(axis), 1),
                            "hd": hd_reference(har, anim, sprite, path),
                            "skel": skel, "flags": flags, "source": source, "note": note,
                            "side": int(row["side"]) if row else 1,
                            "reach": float(row["reach"]) if row and row.get("reach") else None,
                            "fist": bool(row and "fist" in flags)})
        entries.append({"har": har, "harName": HAR_NAMES[har], "animation": anim, "name": names[(har, anim)],
                        "input": r["input_code"], "alsoApplies": sorted(shared.get((har, anim), [])),
                        "sharedWithSystem": system_shared.get((har, anim), []), "sprites": sprites})
    return {"entries": entries, "ymaps": {str(k): v for k, v in ymaps.items()}, "unit": fp.SIDE_UNITS}


PAGE = (paths.WEB / "pose_editor_page.html").read_text(encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = build()
    payload = json.dumps(data).replace("</", "<\\/")
    (OUT / "index.html").write_text(PAGE.replace("__DATA__", payload), encoding="utf-8")
    sprites = sum(len(e["sprites"]) for e in data["entries"])
    print(f"{len(data['entries'])} moves, {sprites} sprites -> {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
