"""Propose 3D pose rows from the original sprites' palette-index joint markers.

The original sprites are paletted. For Jaguar, palette indices 8-15 are the small dark joint
cuffs (neck, wrists, waist, knees, ankles; elbows are sometimes hidden). This reads them as
blobs in floor-based pixel coordinates (using each sprite's offset from the fighter's origin),
labels the limbs with bone-length rules, estimates a missing elbow or knee by two-bone IK,
maps the joints into the rig's (y, z) plane, and writes proposed pose_catalog rows plus an
overlay image per sprite for checking by eye.

    python omf3k/prototype/fit_poses.py --har 0 --animation 42          # one move
    python omf3k/prototype/fit_poses.py --har 0 --all                    # every player-triggered move

Proposals go to omf3k/build/pose-fit/proposals.csv (same columns as pose_catalog.csv); nothing is
written to pose_catalog.csv. Review the overlays first.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402

ROOT = paths.ROOT
BUILD = paths.ARTIFACTS
AFTOOL = paths.AFTOOL
OUT = BUILD / "pose-fit"
HAR_DIRS = {0: "jaguar", 1: "shadow"}
JOINT_INDICES = {0: (8, 16)}           # Jaguar: joint cuffs. Shadow uses ribbed segments (not handled yet).
IDLE = {0: (11, 0)}                    # animation and sprite whose joints are the rest pose
REST_Y = {0: dict(ankle=.23, knee=.75, hip=1.30, shoulder=2.24, neck=2.86)}   # rig heights of the idle joints
SIDE_UNITS = 7.6 / 280.0               # world units per source pixel across (the viewer's x_scale)
FIELDS = ("har", "animation", "sprite", "side", "flags", "reach", "elbow_y", "elbow_z", "wrist_y",
          "wrist_z", "knee_y", "knee_z", "ankle_y", "ankle_z", "knee2_y", "knee2_z", "ankle2_y",
          "ankle2_z", "body_z")

_offsets: dict = {}


def sprite_offset(har, anim, sprite):
    key = (har, anim, sprite)
    if key not in _offsets:
        text = subprocess.run([str(AFTOOL), "-f", str(ROOT / "OMF2097" / f"FIGHTR{har}.AF"), "-m", str(anim),
                               "-s", str(sprite)], capture_output=True, text=True).stdout
        _offsets[key] = tuple(int(re.search(rf"\* {k}:\s+(-?\d+)", text).group(1)) for k in ("X", "Y"))
    return _offsets[key]


def load_sprite(har, anim, sprite):
    path = BUILD / "pose-reference" / HAR_DIRS[har] / str(anim) / f"sprite-{sprite:02d}.png"
    image = Image.open(path)
    return image, np.array(image)


def blobs(har, anim, sprite):
    """Joint-marker centroids as (x, y, size) in pixels right of the origin and up from the floor."""
    _, indices = load_sprite(har, anim, sprite)
    ox, oy = sprite_offset(har, anim, sprite)
    lo, hi = JOINT_INDICES[har]
    labels, n = ndimage.label((indices >= lo) & (indices < hi), structure=np.ones((3, 3)))
    found = []
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        found.append((ox + xs.mean() + .5, -(oy + ys.mean() + .5), len(xs)))
    return found


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def segment_distance(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / max(ab[0] ** 2 + ab[1] ** 2, 1e-9)))
    return dist(p, (a[0] + t * ab[0], a[1] + t * ab[1]))


def two_bone(root, target, l1, l2, bend_down=True):
    """Middle joint of a two-bone chain reaching toward target (clamped to the chain's reach)."""
    d = min(max(dist(root, target), abs(l1 - l2) + 1e-6), l1 + l2 - 1e-6)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = min(math.sqrt(max(l1 * l1 - a * a, 0)), .25 * d)   # a hidden elbow bends only slightly
    ux, uy = (target[0] - root[0]) / max(dist(root, target), 1e-6), (target[1] - root[1]) / max(dist(root, target), 1e-6)
    mx, my = root[0] + ux * a, root[1] + uy * a
    c1, c2 = (mx - uy * h, my + ux * h), (mx + uy * h, my - ux * h)
    return min(c1, c2, key=lambda c: c[1]) if bend_down else max(c1, c2, key=lambda c: c[1])


@dataclass
class Skeleton:
    neck: tuple
    pelvis: tuple
    shoulder: tuple
    legs: list           # [(hip, knee, ankle)] x2, each point (x, y); estimated points flagged in `guessed`
    arms: list           # [(shoulder, elbow, wrist)] x2
    guessed: set


@dataclass
class Rest:
    upper_arm: float
    forearm: float
    thigh: float
    shin: float
    ymap: tuple          # (px heights, rig heights)
    shoulder_offset: tuple
    pelvis_x: float = 0.0     # idle pelvis marker x: the rig's z = 0 line


def measure_rest(har):
    """Bone lengths in pixels and the pixel-to-rig height map, from the idle sprite."""
    anim, sprite = IDLE[har]
    found = blobs(har, anim, sprite)
    # Idle landmarks by height: ankles near the floor, knees about a quarter up, the waist near 41 px.
    ankles = sorted((b for b in found if b[1] < 12), key=lambda b: -b[2])[:2]
    knees = sorted((b for b in found if 16 < b[1] < 32), key=lambda b: -b[2])[:2]
    pelvis = min((b for b in found if 35 < b[1] < 47), key=lambda b: abs(b[1] - 41))
    neck = max((b for b in found if abs(b[0] - pelvis[0]) < 16), key=lambda b: b[1])
    shin = np.mean([min(dist(a, k) for k in knees) for a in ankles])
    thigh = np.mean([dist(pelvis, k) for k in knees])
    y = REST_Y[har]
    shoulder_drop = 9.3                      # idle: the shoulder cuffs sit this far below the neck marker
    ymap = ((np.mean([a[1] for a in ankles]), np.mean([k[1] for k in knees]), pelvis[1], neck[1] - shoulder_drop, neck[1]),
            (y["ankle"], y["knee"], y["hip"], y["shoulder"], y["neck"]))
    # Arm bones: the gauntlet (elbow to wrist) measures ~19 px and the upper arm ~24 px in the punch sprites.
    return Rest(upper_arm=24.0, forearm=19.0, thigh=thigh, shin=shin, ymap=ymap,
                shoulder_offset=(-5.0, -shoulder_drop), pelvis_x=float(pelvis[0]))


def label(found, rest):
    """Assign blobs to neck, pelvis, legs and arms."""
    hip_y = rest.ymap[0][2]
    waist = [b for b in found if abs(b[1] - hip_y) < 8]
    # The pelvis marker is the waist one nearest the median x of the torso-height markers.
    mid_x = float(np.median([b[0] for b in found if hip_y - 25 < b[1] < hip_y + 35]))
    pelvis = min(waist, key=lambda b: abs(b[0] - mid_x) + abs(b[1] - hip_y))[:2] if waist else (mid_x, hip_y)
    neck = max((b for b in found if abs(b[0] - pelvis[0]) < 16), key=lambda b: b[1])[:2]
    shoulder = (neck[0] + rest.shoulder_offset[0], neck[1] + rest.shoulder_offset[1])
    guessed = set()

    # Legs: markers below the pelvis form (knee, ankle) pairs.
    low = [b[:2] for b in found if b[1] < pelvis[1] - 6]
    legs = []
    best = None
    for knees in itertools.permutations(low, 2) if len(low) >= 2 else []:
        pass
    pairs = [(k, a) for k in low for a in low if k is not a]

    def pair_cost(k, a):
        return abs(dist(k, a) - rest.shin) / rest.shin + abs(dist(pelvis, k) - rest.thigh) / rest.thigh * .7 + \
            (4.0 if a[1] > k[1] + 6 else 0)          # an ankle should not sit well above its knee

    chains = []
    for (k1, a1), (k2, a2) in itertools.combinations(pairs, 2):
        if len({id(k1), id(a1), id(k2), id(a2)}) < 4:
            continue
        chains.append((pair_cost(k1, a1) + pair_cost(k2, a2), (k1, a1), (k2, a2)))
    if chains:
        _, c1, c2 = min(chains, key=lambda c: c[0])
        legs = [c1, c2]
    elif low:
        legs = [(low[0], low[-1])]
    while len(legs) < 2:                              # a hidden leg: copy the visible one, flagged as a guess
        legs.append(legs[0] if legs else ((pelvis[0], pelvis[1] - rest.thigh), (pelvis[0], pelvis[1] - rest.thigh - rest.shin)))
        guessed.add("leg")
    leg_out = [(pelvis, k, a) for k, a in legs]

    # Arms: far blobs at upper-body height are wrists; an elbow blob between shoulder and wrist is used,
    # otherwise two-bone IK places it.
    belt_x = pelvis[0]
    upper = [b[:2] for b in found if b[1] > pelvis[1] + 6 and b[:2] != neck]
    wrists = sorted((p for p in upper if dist(p, shoulder) > rest.forearm * .6 and abs(p[0] - belt_x) > 12),
                    key=lambda p: -dist(p, shoulder))[:2]
    arms = []
    for w in wrists:
        elbow = None
        for p in upper:
            if p == w:
                continue
            if abs(dist(shoulder, p) - rest.upper_arm) < rest.upper_arm * .45 and \
               abs(dist(p, w) - rest.forearm) < rest.forearm * .45 and abs(p[0] - belt_x) > 6:
                if elbow is None or abs(dist(shoulder, p) - rest.upper_arm) < abs(dist(shoulder, elbow) - rest.upper_arm):
                    elbow = p
        if elbow is None:
            elbow = two_bone(shoulder, w, rest.upper_arm, rest.forearm)
            guessed.add("elbow")
        arms.append((shoulder, elbow, w))
    while len(arms) < 2:
        arms.append((shoulder, (shoulder[0], shoulder[1] - rest.upper_arm),
                     (shoulder[0], shoulder[1] - rest.upper_arm - rest.forearm)))
        guessed.add("arm")
    return Skeleton(neck, pelvis, shoulder, leg_out, arms, guessed)


def to_rig(rest, axis_x, point):
    """Pixel point -> rig (y, z). Forward (right in the sprite) is negative z."""
    px, rig = rest.ymap
    y = float(np.interp(point[1], px, rig))
    if point[1] > px[-1]:
        y = rig[-1] + (point[1] - px[-1]) * (rig[-1] - rig[-2]) / (px[-1] - px[-2])
    elif point[1] < px[0]:
        y = rig[0] + (point[1] - px[0]) * (rig[1] - rig[0]) / (px[1] - px[0])
    return y, -(point[0] - axis_x) * SIDE_UNITS


def confidence(skel, rest):
    """Reasons a fit is unreliable, empty when it looks right.

    Checks that the torso is upright, both legs have plausible thigh and shin lengths, no limb
    was invented, and the pelvis marker is real.
    """
    problems = []
    if skel.guessed & {"leg", "arm"}:
        problems.append("hidden limb")
    if not 22 < skel.neck[1] - skel.pelvis[1] < 40 or abs(skel.neck[0] - skel.pelvis[0]) > 14:
        problems.append("torso not upright")
    for hip, knee, ankle in skel.legs:
        if abs(dist(hip, knee) - rest.thigh) > rest.thigh * .4 or abs(dist(knee, ankle) - rest.shin) > rest.shin * .4:
            problems.append("leg length")
            break
    if skel.legs[0][1:] == skel.legs[1][1:]:
        problems.append("legs coincide")
    return problems


def pose_row(har, anim, sprite, skel, rest):
    axis = (skel.neck[0] + skel.pelvis[0]) / 2
    # Active arm: the wrist reaching farthest forward. Active leg: the ankle farthest forward or highest.
    arm = max(skel.arms, key=lambda a: a[2][0])
    legs = sorted(skel.legs, key=lambda l: -(l[2][0] - skel.pelvis[0]) - max(l[2][1] - rest.ymap[0][0], 0) * .5)
    elbow, wrist = to_rig(rest, axis, arm[1]), to_rig(rest, axis, arm[2])
    leg = [(to_rig(rest, axis, l[1]), to_rig(rest, axis, l[2])) for l in legs]
    reach = max(0.0, min(1.0, -wrist[1] / 1.7))
    body_z = -(skel.pelvis[0] - axis) * SIDE_UNITS
    row = {f: "" for f in FIELDS}
    row.update(har=har, animation=anim, sprite=sprite, side=1, flags="arm|leg|leg2|body" + ("|reach" if reach > .35 else ""),
               elbow_y=f"{elbow[0]:.2f}", elbow_z=f"{elbow[1]:.2f}", wrist_y=f"{wrist[0]:.2f}", wrist_z=f"{wrist[1]:.2f}",
               knee_y=f"{leg[0][0][0]:.2f}", knee_z=f"{leg[0][0][1]:.2f}", ankle_y=f"{leg[0][1][0]:.2f}",
               ankle_z=f"{leg[0][1][1]:.2f}", knee2_y=f"{leg[1][0][0]:.2f}", knee2_z=f"{leg[1][0][1]:.2f}",
               ankle2_y=f"{leg[1][1][0]:.2f}", ankle2_z=f"{leg[1][1][1]:.2f}", body_z=f"{body_z:.2f}")
    if reach > .35:
        row["reach"] = f"{reach:.2f}"
    return row, arm, legs


def overlay(har, anim, sprite, skel, arm, legs, scale=6):
    image, indices = load_sprite(har, anim, sprite)
    ox, oy = sprite_offset(har, anim, sprite)
    palette = np.array(image.getpalette()).reshape(-1, 3)
    big = Image.fromarray(palette[indices].astype(np.uint8)).resize((image.width * scale, image.height * scale),
                                                                  Image.NEAREST)
    draw = ImageDraw.Draw(big)

    def px(p):
        return ((p[0] - ox) * scale, (-p[1] - oy) * scale)

    for chain, color in ((arm, (255, 80, 80)), *((l, c) for l, c in zip(legs, ((80, 255, 120), (80, 200, 255))))):
        pts = [px(p) for p in chain]
        draw.line(pts, fill=color, width=3)
        for p in pts:
            draw.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=(255, 255, 0), width=2)
    for b in blobs(har, anim, sprite):
        p = px(b)
        draw.rectangle([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=(255, 0, 255))
    return big


def inventory_moves(har):
    rows = list(csv.DictReader((BUILD / "move-catalog.csv").open(newline="", encoding="utf-8")))
    return [(int(r["animation"]), int(r["sprites"])) for r in rows
            if int(r["har"]) == har and r["kind"] in ("basic", "special")]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--har", type=int, default=0)
    parser.add_argument("--animation", type=int)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.har not in JOINT_INDICES:
        raise SystemExit(f"HAR {args.har} has no joint-marker range yet")
    rest = measure_rest(args.har)
    print(f"rest: thigh {rest.thigh:.1f}px shin {rest.shin:.1f}px")
    moves = inventory_moves(args.har) if args.all else [(args.animation, None)]
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for anim, count in moves:
        folder = BUILD / "pose-reference" / HAR_DIRS[args.har] / str(anim)
        sprites = sorted(int(re.search(r"(\d+)", f.stem).group(1)) for f in folder.glob("sprite-*.png"))
        for sprite in sprites:
            found = blobs(args.har, anim, sprite)
            if len(found) < 6:
                print(f"anim {anim} sprite {sprite}: only {len(found)} markers, skipped")
                continue
            skel = label(found, rest)
            row, arm, legs = pose_row(args.har, anim, sprite, skel, rest)
            problems = confidence(skel, rest)
            row["note"] = "; ".join(problems)
            rows.append(row)
            overlay(args.har, anim, sprite, skel, arm, legs).save(OUT / f"h{args.har}_a{anim}_s{sprite}.png")
    with (OUT / "proposals.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS + ("note",))
        writer.writeheader()
        writer.writerows(rows)
    good = [r for r in rows if not r["note"]]
    print(f"{len(rows)} proposed rows ({len(good)} confident, {len(rows) - len(good)} flagged) -> {OUT / 'proposals.csv'}")


if __name__ == "__main__":
    main()
