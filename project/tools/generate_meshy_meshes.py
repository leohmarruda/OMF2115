"""Convert the Meshy FBX meshes into rigged prototype mesh data.

Each FBX is one fused, unrigged mesh in a fixed pose. For every model this script
splits it into the prototype's rig groups by nearest bone, retargets the torso,
arms and legs to the blockout rest pose that main.c's rig_map expects, rescales it
to the blockout's joint heights, adds ball joints over the seams, decimates by
vertex clustering and writes meshy_meshes.h. Use --debug <dir> for group previews.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402
from fbx_reader import mesh  # noqa: E402

MESH_DIR = HERE.parent / "docs" / "mesh"
OUT = paths.PROTOTYPE / "meshy_meshes.h"
JOINT_COLOR = (62, 96, 150)
EYE_COLOR = (35, 229, 67)
FACE_COLOR = (30, 38, 45)
RIGID_COLORS = (JOINT_COLOR, EYE_COLOR, FACE_COLOR)     # parts that follow their rig group without joint blending


def blockout_groups(har):
    """Per rig group (min, max) box of the blockout model in model_meshes.h, the size to match."""
    text = (paths.PROTOTYPE / "model_meshes.h").read_text()
    i = text.index("model_positions[]"); j = text.index("};", i)
    pos = np.array(re.findall(r"\{(-?[\d.]+)f,(-?[\d.]+)f,(-?[\d.]+)f\}", text[i:j]), float)
    i = text.index("model_indices[]"); j = text.index("};", i)
    idx = np.array([int(x) for x in re.findall(r"\d+", text[i:j].split("{", 1)[1])])
    k = text.index("model_parts[]")
    boxes = {}
    for name, h, g, _, f, c in re.findall(
            r'\{"([^"]+)",\s*(\d+),\s*(-?\d+),\s*(-?\d+),\s*(\d+),\s*(\d+),', text[k:]):
        if int(h) == har and not (int(g) == 1 and name.startswith("neck_")):
            boxes.setdefault(int(g), []).append(pos[idx[int(f):int(f) + int(c)]])
    return {g: (np.vstack(p).min(0), np.vstack(p).max(0)) for g, p in boxes.items()}


def blockout_head_parts(har, prefixes):
    """Blockout parts named with one of `prefixes` as (positions, triangles, colour): the Meshy
    heads have no painted face, so the face features are borrowed from the blockout."""
    text = (paths.PROTOTYPE / "model_meshes.h").read_text()
    i = text.index("model_positions[]"); j = text.index("};", i)
    pos = np.array(re.findall(r"\{(-?[\d.]+)f,(-?[\d.]+)f,(-?[\d.]+)f\}", text[i:j]), float)
    i = text.index("model_indices[]"); j = text.index("};", i)
    idx = np.array([int(x) for x in re.findall(r"\d+", text[i:j].split("{", 1)[1])])
    k = text.index("model_parts[]")
    found = []
    for name, h, _, _, f, c, r, g, b in re.findall(
            r'\{"([^"]+)",\s*(\d+),\s*(-?\d+),\s*(-?\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)',
            text[k:]):
        if int(h) == har and name.startswith(prefixes):
            used = idx[int(f):int(f) + int(c)]
            u = np.unique(used)
            found.append((pos[u], np.searchsorted(u, used).reshape(-1, 3), (int(r), int(g), int(b))))
    return found


# group ids match main.c's model_transform: 0 torso, 1 head, 2 pelvis, 3 upper arm,
# 4 forearm, 5 hand, 6 thigh, 7 shin, 8 foot.
GROUP_NAMES = ("torso", "head", "pelvis", "upper_arm", "forearm", "hand", "thigh", "shin", "foot")
DEBUG_COLORS = [(200, 200, 200), (240, 200, 80), (120, 220, 120), (230, 90, 90), (90, 150, 240),
                (240, 140, 240), (90, 220, 220), (240, 160, 60), (160, 120, 240)]


@dataclass
class Model:
    prefix: str                    # C identifier prefix in the header
    fbx: str
    har: int                       # 0 Jaguar, 1 Shadow
    origin: tuple                  # preview pixel that is FBX X=0, Z=0
    pixels_per_unit: float
    landmarks: dict                # name -> preview pixel (x, y), image-left is the "l" side
    rest: dict                     # blockout joint heights in main.c for this HAR
    palette: tuple                 # RGB per rig group, see GROUP_NAMES
    front_sign: float = -1.0       # FBX front is -Y for both Meshy exports (see README)
    cell: float = 0.016            # vertex-cluster size in FBX units
    x_scale: float = 2.4           # lateral; the Meshy robots are slimmer than the blockouts
    z_scale: float = 2.0           # depth
    head_halfwidth: float = .22
    head_wedge: bool = False       # reshape the head to the blockout's wedge helmet
    head_features: tuple = ()      # blockout part-name prefixes copied onto the head (eyes, face void)
    head_push: float = 0.0         # move the copied face features this far forward (-z)
    head_collar: bool = False      # ring over the helmet's ragged lower rim
    head_cull_x: float | None = None   # drop head triangles with a vertex left of this FBX x (a stray horn)
    align_feet: bool = False       # turn each foot about the ankle so its longest spike points forward
    foot_by_z: bool = True         # feet are everything below the ankle (else past the shin's end)
    radius: dict = field(default_factory=lambda: {
        "torso": .30, "pelvis": .16, "upper": .10, "fore": .10, "thigh": .10, "shin": .10})

    def lm(self):
        ox, oy = self.origin
        return {k: np.array([(x - ox) / self.pixels_per_unit, 0.0, (oy - y) / self.pixels_per_unit])
                for k, (x, y) in self.landmarks.items()}


MODELS = [
    Model(prefix="meshy", fbx="Meshy_AI_Blue_Robot_Mascot_1014010749_generate.fbx", har=0,
          origin=(300, 308), pixels_per_unit=245.0,
          landmarks={
              "head_base": (335, 118), "neck": (335, 128),
              "spine_top": (335, 135), "spine_bottom": (335, 232),
              "hip_l": (303, 300), "knee_l": (299, 408), "ankle_l": (292, 505),
              "hip_r": (345, 300), "knee_r": (353, 408), "ankle_r": (378, 505),
              "sh_l": (282, 150), "el_l": (200, 133), "wr_l": (135, 85),
              "sh_r": (392, 170), "el_r": (408, 245), "wr_r": (468, 298)},
          rest={"sh": 2.24, "el": 1.76, "wr": 1.13, "hip": 1.30, "knee": .75, "ankle": .23},
          palette=((110, 160, 215), (160, 200, 240), (70, 110, 170), (110, 160, 215), (90, 140, 200),
                   (235, 205, 95), (100, 150, 205), (82, 128, 188), (58, 88, 138)),
          cell=0.02, head_wedge=True, head_features=("eye_",), head_push=.07, head_cull_x=-0.012),
    Model(prefix="jester", fbx="Meshy_AI_Blue_Rocket_Jester_1014011155_generate.fbx", har=1,
          origin=(400, 400), pixels_per_unit=370.0,
          landmarks={
              "head_base": (354, 160), "neck": (345, 190),
              "spine_top": (350, 212), "spine_bottom": (346, 388),
              "hip_l": (322, 422), "knee_l": (215, 540), "ankle_l": (135, 640),
              "hip_r": (385, 426), "knee_r": (505, 535), "ankle_r": (435, 655),
              "sh_l": (252, 215), "el_l": (170, 322), "wr_l": (125, 385),
              "sh_r": (470, 202), "el_r": (568, 192), "wr_r": (655, 180)},
          rest={"sh": 2.25, "el": 1.77, "wr": 1.11, "hip": 1.27, "knee": .76, "ankle": .24},
          palette=((96, 112, 200), (150, 156, 230), (62, 72, 140), (96, 112, 200), (78, 92, 176),
                   (90, 210, 235), (84, 98, 184), (70, 82, 160), (50, 58, 112)),
          cell=0.026, x_scale=1.9, z_scale=1.6,
          head_halfwidth=.20, foot_by_z=False, align_feet=True,
          head_features=("eye_", "face_void"), head_collar=True,
          radius={"torso": .34, "pelvis": .16, "upper": .12, "fore": .11, "thigh": .12, "shin": .11}),
]


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def classify(m: Model, v):
    """Return (group, side) per vertex; side is -1/+1 for limbs by image side."""
    p = np.stack([v[:, 0], v[:, 2]], axis=1)
    L = {k: np.array([x[0], x[2]]) for k, x in m.lm().items()}
    R = m.radius
    cands = [("torso", 0, 0, L["spine_top"], L["spine_bottom"], R["torso"]),
             ("pelvis", 2, 0, L["spine_bottom"], (L["hip_l"] + L["hip_r"]) / 2, R["pelvis"])]
    for s, n in ((-1, "l"), (1, "r")):
        cands += [("upper", 3, s, L["sh_" + n], L["el_" + n], R["upper"]),
                  ("fore", 4, s, L["el_" + n], L["wr_" + n], R["fore"]),
                  ("thigh", 6, s, L["hip_" + n], L["knee_" + n], R["thigh"]),
                  ("shin", 7, s, L["knee_" + n], L["ankle_" + n], R["shin"])]
    score = np.stack([seg_dist(p, c[3], c[4]) / c[5] for c in cands], axis=1)
    best = score.argmin(axis=1)
    group = np.array([cands[i][1] for i in best])
    side = np.array([cands[i][2] for i in best])
    z = v[:, 2]
    head = (z > L["head_base"][1]) & (abs(v[:, 0] - L["head_base"][0]) < m.head_halfwidth)
    group[head] = 1; side[head] = 0
    for s, n in ((-1, "l"), (1, "r")):
        # Beyond the end of a limb's last bone: wrist and below is the hand, ankle and below the foot.
        for bone, end, to_group, frac in (("fore", "wr", 5, .85), ("shin", "ankle", 8, .92)):
            a = L[("el_" if bone == "fore" else "knee_") + n]
            b = L[end + "_" + n]
            axis = (b - a) / np.linalg.norm(b - a)
            along = (p - a) @ axis
            src = 4 if bone == "fore" else 7
            sel = (group == src) & (side == s)
            if bone == "shin" and m.foot_by_z:
                sel &= z < b[1]
            else:
                sel &= along > np.linalg.norm(b - a) * frac
            group[sel] = to_group
    return group, side


def rotate_about(pts, pivot, rot):
    return (pts - pivot) @ rot.T + pivot


def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = a @ b
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else -np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def retarget(m: Model, v, group, side):
    """Stand the spine up and hang arms and legs straight down (the blockout rest pose).

    Returns the moved vertices and the landmarks at their new positions.
    """
    v = v.copy(); lm = m.lm()
    down, up = np.array([0, 0, -1.0]), np.array([0, 0, 1.0])

    def apply(mask, pivot, rot, names):
        pivot = pivot.copy()
        v[mask] = rotate_about(v[mask], pivot, rot)
        for n in names:
            lm[n] = rotate_about(lm[n], pivot, rot)

    upper = [k for k in lm if k.split("_")[0] in ("head", "neck", "spine", "sh", "el", "wr")]
    upper = [k for k in upper if k != "spine_bottom"]
    apply(np.isin(group, (0, 1, 2, 3, 4, 5)), lm["spine_bottom"],
          rot_between(lm["spine_top"] - lm["spine_bottom"], up), upper)
    for s, n in ((-1, "l"), (1, "r")):
        arm = np.isin(group, (3, 4, 5)) & (side == s)
        apply(arm, lm["sh_" + n], rot_between(lm["el_" + n] - lm["sh_" + n], down), ["el_" + n, "wr_" + n])
        apply(arm & np.isin(group, (4, 5)), lm["el_" + n],
              rot_between(lm["wr_" + n] - lm["el_" + n], down), ["wr_" + n])
        leg = np.isin(group, (6, 7, 8)) & (side == s)
        apply(leg, lm["hip_" + n], rot_between(lm["knee_" + n] - lm["hip_" + n], down),
              ["knee_" + n, "ankle_" + n])
        apply(leg & np.isin(group, (7, 8)), lm["knee_" + n],
              rot_between(lm["ankle_" + n] - lm["knee_" + n], down), ["ankle_" + n])
    if m.align_feet:
        for s, n in ((-1, "l"), (1, "r")):
            foot = (group == 8) & (side == s)
            if not foot.any():
                continue
            ankle = lm["ankle_" + n]
            flat = v[foot][:, :2] - ankle[:2]
            tip = flat[np.argmax(np.linalg.norm(flat, axis=1))]
            turn = np.arctan2(m.front_sign, 0.0) - np.arctan2(tip[1], tip[0])
            c, sn = np.cos(turn), np.sin(turn)
            rot = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]])
            v[foot] = rotate_about(v[foot], ankle, rot)
    return v, lm


def to_prototype(m: Model, v, group, side, lm):
    """FBX (X lateral, Y depth, Z up) -> prototype (x lateral, y up, z forward = -z)."""
    mean = lambda a, b: (lm[a][2] + lm[b][2]) / 2
    hip_z, knee_z, ankle_z = mean("hip_l", "hip_r"), mean("knee_l", "knee_r"), mean("ankle_l", "ankle_r")
    sh_z, head_z = mean("sh_l", "sh_r"), lm["head_base"][2]
    z = v[:, 2]
    floor_z = min(z[group == 8].min() if (group == 8).any() else ankle_z, ankle_z - .05)
    top_z = max(z[group == 1].max(), head_z + .05)
    body_x = (lm["hip_l"][0] + lm["hip_r"][0]) / 2
    r = m.rest
    boxes = blockout_groups(m.har)
    head_lo, head_hi = boxes[1]
    head = group == 1
    # The head keeps the mesh's own shape: one uniform scale sets its width to the blockout's
    # (2-98 percentile, ignoring stray spikes), with its bottom where the blockout's head starts.
    hx = v[head, 0]
    head_scale = (head_hi[0] - head_lo[0]) / (np.percentile(hx, 98) - np.percentile(hx, 2))
    head_bottom_y = head_lo[1]
    head_top_y = head_bottom_y + (top_z - head_z) * head_scale
    if m.head_wedge:
        head_top_y = head_hi[1]     # the mesh's cap is a thin slab; give it the blockout helmet's height
    out = np.empty_like(v)
    # Facing -Y (front_sign -1) needs x flipped to stay a proper rotation.
    out[:, 0] = m.front_sign * (v[:, 0] - body_x) * m.x_scale
    out[:, 2] = -m.front_sign * v[:, 1] * m.z_scale
    # Body: legs onto the blockout hip/knee/ankle heights, torso 1:1; the neck stretches up to
    # the head, which keeps its own proportions.
    y = np.interp(z, [floor_z, ankle_z, knee_z, hip_z, sh_z, head_z, top_z],
                  [0.0, r["ankle"], r["knee"], r["hip"], r["sh"], head_bottom_y, head_top_y])
    # Arms hang from the shoulder with a plain scale; rig_map restretches them per pose.
    arm = np.isin(group, (3, 4, 5))
    arm_scale = (r["sh"] - r["hip"]) / (sh_z - hip_z)
    arm_sh_z = np.where(side == -1, lm["sh_l"][2], lm["sh_r"][2])
    y[arm] = r["sh"] + (z[arm] - arm_sh_z[arm]) * arm_scale
    out[:, 1] = y
    fit_body_widths(out, group, boxes)
    # Feet: stretch the toe forward (negative z only, so the ankle end stays put) to the blockout's reach.
    foot = group == 8
    reach = np.percentile(out[foot, 2], 2)
    if reach < 0 and boxes[8][0][2] < reach:
        toe = foot & (out[:, 2] < 0)
        out[toe, 2] *= boxes[8][0][2] / reach
    # Head x/z: uniform scale about the head's own centre, placed at the blockout head's centre.
    for axis, raw_axis, sign in ((0, 0, m.front_sign), (2, 1, -m.front_sign)):
        c = np.mean(np.percentile(v[head, raw_axis], [2, 98]))   # mid-range, robust to spikes
        out[head, axis] = (head_lo[axis] + head_hi[axis]) / 2 + sign * (v[head, raw_axis] - c) * head_scale
    if m.head_wedge:
        # Canonical wedge: wide flat top, chin about half as wide and half as deep, centred on the
        # blockout head. h runs 0 at the chin to 1 at the crown.
        h = np.clip((out[head, 1] - head_bottom_y) / (head_top_y - head_bottom_y), 0, 1)
        taper = .5 + .5 * h
        cx = (head_lo[0] + head_hi[0]) / 2
        cz = (head_lo[2] + head_hi[2]) / 2
        out[head, 0] = cx + (out[head, 0] - cx) * taper
        out[head, 2] = cz + (out[head, 2] - cz) * taper
    print(f"   head: scale x{head_scale:.2f}, y {head_bottom_y:.2f}..{head_top_y:.2f}")
    return out, body_x


def robust_extent(p, axis):
    lo, hi = np.percentile(p[:, axis], [2, 98])
    return hi - lo


def fit_body_widths(out, group, boxes):
    """Scale lateral (x) and depth (z) about the body axis as a smooth function of height.

    Two measured factors, blockout width / mesh width: one for the legs (thighs; the shin boxes include spikes)
    and one for the torso level, set by the upper arms because Shadow's wedge armor is wider
    than its arm span. They are interpolated in y, so neighbouring groups stay joined at
    their seams. Depth is fitted the same way.
    """
    def ratio(groups, axis):
        r = []
        for g in groups:
            lo, hi = boxes[g]
            r.append((hi[axis] - lo[axis]) / robust_extent(out[group == g], axis))
        return float(np.mean(r))

    legs, torso = (6,), (3,)
    leg_y = float(out[np.isin(group, legs), 1].mean())
    torso_y = float(out[group == 0, 1].mean())
    fx = (ratio(legs, 0), ratio(torso, 0))
    fz = (ratio(legs, 2), ratio(torso, 2))
    out[:, 0] *= np.interp(out[:, 1], [leg_y, torso_y], fx)
    out[:, 2] *= np.interp(out[:, 1], [leg_y, torso_y], fz)
    print(f"   width fit: legs x{fx[0]:.2f} z{fz[0]:.2f} at y={leg_y:.2f}; torso x{fx[1]:.2f} z{fz[1]:.2f} at y={torso_y:.2f}")


def sphere(center, radius):
    """Octahedron subdivided once: a cheap ball that hides joint seams."""
    v = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    v = [np.array(p, float) for p in v]; out = []
    for a, b, c in f:
        mid = [(v[a] + v[b]), (v[b] + v[c]), (v[c] + v[a])]
        mid = [x / np.linalg.norm(x) for x in mid]
        base = len(v); v.extend(mid)
        out += [(a, base, base + 2), (b, base + 1, base), (c, base + 2, base + 1), (base, base + 1, base + 2)]
    return np.array(v) * radius + center, np.array(out)


def joint_caps(m: Model, moved, cg, cs):
    """Ball joints in rest pose, owned by the child limb so they rotate with it.

    Each is centred on the child limb's vertices next to the joint, so it follows the fitted widths.
    """
    caps = []
    for s in (-1, 1):
        for key, group, r in (("sh", 3, .13), ("el", 4, .13), ("wr", 5, .10),
                              ("hip", 6, .17), ("knee", 7, .17), ("ankle", 8, .15)):
            near = (cg == group) & (cs == s) & (abs(moved[:, 1] - m.rest[key]) < .12)
            if near.sum() < 6:
                near = (cg == group) & (cs == s)
            x, z = np.median(moved[near, 0]), np.median(moved[near, 2])
            pos, tris = sphere(np.array([x, m.rest[key], z]), r)
            caps.append((group, s * int(m.front_sign), pos, tris, JOINT_COLOR))
    return caps


def triangle_groups(group, side, tris):
    g = group[tris]; s = side[tris]
    pick = np.where(g[:, 1] == g[:, 2], 1, 0)     # corners 1,2 agree -> use them, otherwise corner 0
    pick = np.where(g[:, 0] == g[:, 2], 0, pick)
    idx = np.arange(len(tris))
    return g[idx, pick], s[idx, pick]


def cluster(m: Model, points, tris):
    """Vertex-clustering decimation; returns (positions, triangles)."""
    key = np.floor(points / (m.cell * 1.5)).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    sums = np.zeros((inv.max() + 1, 3)); np.add.at(sums, inv, points)
    pos = sums / np.bincount(inv).astype(float)[:, None]
    t = inv[tris]
    keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])
    return pos, t[keep]


def build(m: Model):
    v, tris = mesh(MESH_DIR / m.fbx)
    group, side = classify(m, v)
    tg, ts = triangle_groups(group, side, tris)
    if m.head_cull_x is not None:
        keep = ~((tg == 1) & (v[tris][:, :, 0].min(axis=1) < m.head_cull_x))
        print(f"   head: dropped {int((~keep).sum())} stray triangles")
        tris, tg, ts = tris[keep], tg[keep], ts[keep]
    # Retarget per corner so each triangle moves rigidly with the group that owns it.
    corners = v[tris].reshape(-1, 3)
    cg = np.repeat(tg, 3); cs = np.repeat(ts, 3)
    moved, lm = retarget(m, corners, cg, cs)
    moved, body_x = to_prototype(m, moved, cg, cs, lm)
    parts = []
    for g in sorted(set(tg)):
        for s in sorted(set(ts[tg == g])):
            sel = np.nonzero((tg == g) & (ts == s))[0]
            idx = (sel[:, None] * 3 + np.arange(3)).ravel()
            pos, t = cluster(m, moved[idx], np.arange(len(idx)).reshape(-1, 3))
            parts.append((int(g), int(s) * int(m.front_sign), pos, t, m.palette[int(g)]))
    features = [(1, 0, pos + [0, 0, -m.head_push], tris, color)
                for pos, tris, color in blockout_head_parts(m.har, m.head_features)]
    if m.head_collar:
        features.append((1, 0, *collar(moved[cg == 1]), FACE_COLOR))
    return parts + joint_caps(m, moved, cg, cs) + features


def collar(head, segments=16, band=.12):
    """Closed elliptical band around the head's lower rim, hiding the ragged cut where the
    helmet meets the neck. Returns (positions, triangles)."""
    rim = np.percentile(head[:, 1], 3)
    near = head[head[:, 1] < rim + .12]
    lo_x, hi_x = np.percentile(near[:, 0], [3, 97]); lo_z, hi_z = np.percentile(near[:, 2], [3, 97])
    cx, cz, rx, rz = (lo_x + hi_x) / 2, (lo_z + hi_z) / 2, (hi_x - lo_x) / 2 + .015, (hi_z - lo_z) / 2 + .015
    ang = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    ring = np.stack([cx + rx * np.cos(ang), np.zeros(segments), cz + rz * np.sin(ang)], axis=1)
    pos = np.vstack([ring + [0, rim - .04, 0], ring + [0, rim - .04 + band, 0]])
    tris = []
    for i in range(segments):
        j = (i + 1) % segments
        tris += [(i, j, segments + j), (i, segments + j, segments + i)]
    return pos, np.array(tris)


def compact(pos, tris):
    used = np.unique(tris)
    remap = np.full(len(pos), -1); remap[used] = np.arange(len(used))
    return pos[used], remap[tris]


def debug_render(parts, path, view):
    W, H = 600, 700
    img = Image.new("RGB", (W, H), (20, 26, 34)); d = ImageDraw.Draw(img)
    polys = []
    for g, s, pos, tris, _ in parts:
        for t in tris:
            p = pos[t]
            if view == "front":
                xy = [(300 + q[0] * 150, 660 - q[1] * 170) for q in p]; depth = p[:, 2].mean()
            else:
                xy = [(300 + q[2] * 150, 660 - q[1] * 170) for q in p]; depth = -p[:, 0].mean()
            n = np.cross(p[1] - p[0], p[2] - p[0]); n = n / (np.linalg.norm(n) + 1e-12)
            shade = .55 + .45 * abs(n[2] if view == "front" else n[0])
            polys.append((depth, xy, tuple(int(x * shade) for x in DEBUG_COLORS[g])))
    for depth, xy, c in sorted(polys, key=lambda x: -x[0]):
        d.polygon(xy, fill=c)
    img.save(path)


BLEND_BAND = .16
# child group -> (joint, parent group); the parent's vertices blend toward the child below the joint.
JOINTS = {3: ("sh", 0), 4: ("el", 3), 5: ("wr", 4), 6: ("hip", 2), 7: ("knee", 6), 8: ("ankle", 7)}


def blend_weights(m: Model, g, s, pos):
    """Per vertex (other_group, other_side, weight 0..255) for blending across the nearest joint.

    Vertices near a joint move partly with the neighbouring group, so the two parts
    meet without a crack when the limb rotates. Weight .5 at the joint, fading to 0.
    """
    n = len(pos)
    best = np.zeros(n); bg = np.zeros(n, int); bs = np.zeros(n, int)

    def offer(w, group, side, mask):
        better = mask & (w > best)
        best[better] = w[better]; bg[better] = group
        bs[better] = side[better] if hasattr(side, "__len__") else side

    y = pos[:, 1]
    if g in JOINTS:                       # toward the parent at this limb's own joint
        joint, parent = JOINTS[g]
        t = (m.rest[joint] - y) / BLEND_BAND
        w = np.clip(.5 - .5 * t, 0, 1)
        offer(w, parent, s if parent not in (0, 2) else 0, np.ones(n, bool))
    for child, (joint, parent) in JOINTS.items():
        if parent != g or child == 3:     # nothing blends a torso vertex toward an arm
            continue
        t = (m.rest[joint] - y) / BLEND_BAND
        w = np.clip(.5 + .5 * t, 0, 1)
        side = np.where(pos[:, 0] > 0, 1, -1) if s == 0 else np.full(n, s)
        offer(w, child, side, np.ones(n, bool))
    return bg, bs, np.round(best * 255).astype(int)


def array_lines(m: Model, parts):
    positions, indices, entries, blends = [], [], [], []
    for g, s, pos, tris, color in parts:
        pos, tris = compact(pos, tris)
        vo, io = len(positions), len(indices)
        positions.extend(pos.tolist()); indices.extend((tris + vo).ravel().tolist())
        entries.append((g, s, io, len(tris) * 3, color))
        if color in RIGID_COLORS:         # ball joints and eyes stay rigid
            blends.extend([(0, 0, 0)] * len(pos))
        else:
            blends.extend(zip(*[a.tolist() for a in blend_weights(m, g, s, pos)]))
    assert len(positions) < 65536, f"{m.prefix}: {len(positions)} vertices exceed uint16 indices"
    f = lambda x: f"{x:.5f}f"
    lines = [f"static const ModelPosition {m.prefix}_positions[] = {{"]
    lines += ["    {" + ",".join(f(c) for c in p) + "}," for p in positions]
    lines += ["};", f"static const ModelBlend {m.prefix}_blend[] = {{"]
    lines += [f"    {{{bg},{bs},{w}}}," for bg, bs, w in blends]
    lines += ["};", f"static const uint16_t {m.prefix}_indices[] = {{"]
    for i in range(0, len(indices), 24):
        lines.append("    " + ", ".join(map(str, indices[i:i + 24])) + ",")
    lines += ["};", f"static const ModelPart {m.prefix}_parts[] = {{"]
    for g, s, io, n, c in entries:
        lines.append(f'    {{"{m.prefix}_{GROUP_NAMES[g]}_{s:+d}", {m.har}, {g}, {s}, {io}, {n}, '
                     f'{c[0]}, {c[1]}, {c[2]}}},')
    lines.append("};")
    print(f"{m.prefix}: {len(entries)} parts, {len(positions)} vertices, {len(indices) // 3} triangles")
    return lines


def main():
    debug = Path(sys.argv[sys.argv.index("--debug") + 1]) if "--debug" in sys.argv else None
    lines = ["// Generated by generate_meshy_meshes.py from the Meshy FBX meshes.",
             "#ifndef OMF3K_MESHY_MESHES_H", "#define OMF3K_MESHY_MESHES_H", '#include "model_meshes.h"',
             "// Per vertex: the neighbouring rig group it also follows, and how much (0-255).",
             "typedef struct { signed char group, side; unsigned char weight; } ModelBlend;"]
    for m in MODELS:
        parts = build(m)
        if debug:
            debug_render(parts, debug / f"{m.prefix}_front.png", "front")
            debug_render(parts, debug / f"{m.prefix}_side.png", "side")
        lines += array_lines(m, parts)
    lines.append("#endif")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
