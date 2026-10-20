"""Estimate both legs' joint positions from OMF 2097 Remastered HD frames.

The AF files hold only 2D sprites, so joints are measured, not read: each
sprite is fingerprinted to its HD frame, the lower-body silhouette is found
below the red belt, and the two feet become ankle targets. Knees are the middle
of the brass thigh/shin pixels between hip and ankle. The torso's forward shift
comes from the waist band, relative to the idle stance. Coordinates are the
catalog's absolute side-view units. Output is a draft; check it with --overlay
before --write merges it into pose_catalog.csv. Original art and crops stay in
the ignored build tree.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from match_remastered_frames import pixel_hash

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402
ROOT = paths.ROOT
HAR_SLUGS = ("jaguar", "shadow", "thorn", "pyros", "electra", "katana", "shredder", "flail", "gargoyle", "chronos", "nova")
KZ, KY = 7.6 / 280.0, 12.0 / 280.0       # sprite pixel -> blockout units (main.c apply_source_fighter)
HIP = (1.27, 0.02)                        # (y, z) of the rig hip for Shadow (main.c model_transform)
THIGH, SHIN = 0.52, 0.53                  # rig knee-hip and ankle-knee lengths
BELT_TO_HIP = 0.33                        # waist band to hip joint; calibrated so idle gives HIP[0]
FOOT_RADIUS = 0.55                        # the foot's pixels within this of its tip average to the ankle


def sprite_box(tool: Path, af: Path, move: int, sprite: int) -> tuple[int, int, int, int]:
    text = subprocess.run([str(tool), "-f", str(af), "-m", str(move), "-s", str(sprite)],
                          capture_output=True, text=True, check=True).stdout
    v = {k: int(m) for k, m in re.findall(r"\* (X|Y|W|H):\s+(-?\d+)", text)}
    return v["X"], v["Y"], v["W"], v["H"]


def find_belt(a: np.ndarray) -> tuple[int, float]:
    """Row of the red waist band: the red-heaviest row in the middle of the body."""
    r, g, b, al = (a[..., i].astype(int) for i in range(4))
    red = (al > 128) & (r > 90) & (r > 1.7 * g) & (r > 1.7 * b)
    rows = np.nonzero((al > 128).any(axis=1))[0]
    top, bottom = rows[0], rows[-1]
    lo, hi = int(top + 0.30 * (bottom - top)), int(top + 0.70 * (bottom - top))
    counts = ndi.uniform_filter1d(red.sum(axis=1).astype(float), 9)
    row = lo + int(np.argmax(counts[lo:hi]))
    band = np.nonzero(red[max(row - 6, 0):row + 7].any(axis=0))[0]
    return row, float((band.min() + band.max()) / 2.0)


def brass_mask(a: np.ndarray) -> np.ndarray:
    """The gold thigh and shin segments: warm hue, strong saturation."""
    r, g, b, al = (a[..., i].astype(float) for i in range(4))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    return (al > 128) & (mx > 90) & (mx - mn > 0.35 * mx) & (r >= g) & (g > 1.25 * b) & (g > 0.55 * r)


def pick_knee(hip, ankle, brass, hip_px_x, box, shape):
    """Knee (y, z): the middle of the brass pixels lying between the hip and the ankle."""
    X, Y, W, H = box
    ys, xs = np.nonzero(brass)
    sy = -(Y + ys * H / shape[0]) * KY
    sz = -(X + xs * W / shape[1]) * KZ
    seg = np.array([ankle[0] - hip[0], ankle[1] - hip[1]])
    length = float(np.hypot(*seg))
    if length < 1e-3:
        return hip[0] - THIGH, hip[1]
    t = ((sy - hip[0]) * seg[0] + (sz - hip[1]) * seg[1]) / length ** 2
    perp = np.abs((sy - hip[0]) * seg[1] - (sz - hip[1]) * seg[0]) / length
    keep = (t > 0.15) & (t < 0.85) & (perp < 0.55)
    if keep.sum() < 40:
        t0 = THIGH / (THIGH + SHIN)
        return hip[0] + seg[0] * t0, hip[1] + seg[1] * t0
    return float(sy[keep].mean()), float(sz[keep].mean())


def measure(hd: Image.Image, box):
    """Return belt row, planted ankle and free ankle in model (y, z) and in pixels."""
    X, Y, W, H = box
    a = np.array(hd.convert("RGBA"))
    belt, belt_x = find_belt(a)
    ys, xs = np.nonzero((a[..., 3] > 128) & (np.arange(a.shape[0])[:, None] > belt + 0.05 * a.shape[0]))
    if len(xs) == 0:
        raise ValueError("no lower-body pixels")
    px_x, px_y = a.shape[1] / W, a.shape[0] / H          # HD pixels per sprite pixel
    # Planted foot: the sole. Its ankle is the middle of the toe-to-heel spread.
    floor = ys.max()
    near = (ys >= floor - 10 * px_y) & (np.abs(xs - xs[np.argmax(ys)]) < 18 * px_x)
    planted_px = ((xs[near].min() + xs[near].max()) / 2.0, floor - 3.5 * px_y)
    # Free foot: the lower-body pixel farthest from the planted foot.
    dist = np.hypot((xs - planted_px[0]) / px_x, (ys - planted_px[1]) / px_y)
    far = int(np.argmax(dist))
    tip_px = (float(xs[far]), float(ys[far]))
    hip_px = (a.shape[1] / 2.0, float(belt))
    if dist[far] < 14:                                    # feet together: no free foot
        free_px = planted_px
    else:                                                 # centroid of the foot around its tip
        close = np.hypot((xs - tip_px[0]) / px_x, (ys - tip_px[1]) / px_y) < FOOT_RADIUS / KZ
        free_px = (float(xs[close].mean()), float(ys[close].mean()))
    hip_sx = X + belt_x / px_x

    def model(p):
        return -(Y + p[1] / px_y) * KY, -(X + p[0] / px_x) * KZ

    hip_y = -(Y + belt / px_y) * KY - BELT_TO_HIP
    return belt, model(planted_px), model(free_px), planted_px, free_px, (hip_y, -hip_sx * KZ), a, belt_x


def hd_frame(index, hd_root: Path, png: Path) -> Image.Image | None:
    with Image.open(png) as src:
        entry = index.get(pixel_hash(src))
    if entry is None:
        return None
    with Image.open(hd_root / entry["bundle"] / f"page_{entry['page']}.webp") as atlas:
        return atlas.crop((entry["x"], entry["y"], entry["x"] + entry["w"],
                           entry["y"] + entry["h"])).convert("RGBA")


def sprite_folder(har: int, animation: int) -> Path:
    return paths.ARTIFACTS / "pose-reference" / HAR_SLUGS[har] / str(animation)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hd_root", type=Path)
    ap.add_argument("--har", type=int, default=1)
    ap.add_argument("--animation", type=int, nargs="+", required=True)
    ap.add_argument("--tool", type=Path, default=paths.AFTOOL)
    ap.add_argument("--overlay-dir", type=Path, help="write one annotated PNG strip per animation")
    ap.add_argument("--no-leg2", nargs="*", default=[], metavar="ANIM/SPRITE",
                    help="frames whose planted-leg measurement failed review; the support leg stays generic")
    ap.add_argument("--write", action="store_true", help="merge the rows into pose_catalog.csv")
    args = ap.parse_args()

    af = ROOT / f"OMF2097/FIGHTR{args.har}.AF"
    index_json = json.loads((args.hd_root / "index.json").read_text(encoding="utf-8"))
    index = {e["hash"]: e for e in index_json["entries"] if e["kind"] == "fighter"}

    # The idle stance defines a torso shift of zero.
    idle = hd_frame(index, args.hd_root, sprite_folder(args.har, 11) / "sprite-00.png")
    if idle is None:
        raise SystemExit("export the idle sprites first: pose_inventory.py --har N --animation 11 --export-sprites")
    idle_z = measure(idle, sprite_box(args.tool, af, 11, 0))[5][1]

    new_rows: dict[tuple[int, int, int], dict[str, str]] = {}
    for animation in args.animation:
        strips = []
        for png in sorted(sprite_folder(args.har, animation).glob("sprite-*.png")):
            sprite = int(png.stem.split("-")[1])
            hd = hd_frame(index, args.hd_root, png)
            if hd is None:
                print(f"# {animation}/{sprite}: no HD match; left unauthored")
                continue
            box = sprite_box(args.tool, af, animation, sprite)
            belt, planted, free, planted_px, free_px, hip, rgba, belt_x = measure(hd, box)
            brass = brass_mask(rgba)
            body_z = hip[1] - idle_z
            legs = [(free, pick_knee(hip, free, brass, belt_x, box, brass.shape)),
                    (planted, pick_knee(hip, planted, brass, belt_x, box, brass.shape))]
            (fa, fk), (pa, pk) = legs
            fmt = lambda v: f"{v:.2f}"
            skip_leg2 = f"{animation}/{sprite}" in args.no_leg2
            new_rows[(args.har, animation, sprite)] = {
                "side": "1", "flags": "leg|body" if skip_leg2 else "leg|leg2|body",
                "knee_y": fmt(fk[0]), "knee_z": fmt(fk[1]), "ankle_y": fmt(fa[0]), "ankle_z": fmt(fa[1]),
                "knee2_y": "" if skip_leg2 else fmt(pk[0]), "knee2_z": "" if skip_leg2 else fmt(pk[1]),
                "ankle2_y": "" if skip_leg2 else fmt(pa[0]), "ankle2_z": "" if skip_leg2 else fmt(pa[1]),
                "body_z": fmt(body_z)}
            print(f"{animation}/{sprite}: free ankle ({fa[0]:.2f},{fa[1]:.2f}) knee ({fk[0]:.2f},{fk[1]:.2f}); "
                  f"planted ankle ({pa[0]:.2f},{pa[1]:.2f}) knee ({pk[0]:.2f},{pk[1]:.2f}); body_z {body_z:.2f}")
            if args.overlay_dir:
                X, Y, W, H = box
                d = ImageDraw.Draw(hd)
                d.line([(0, belt), (hd.width, belt)], fill=(255, 255, 0, 255), width=2)
                for (ky, kz) in (fk, pk):
                    cx, cy = (-kz / KZ - X) * hd.width / W, (-ky / KY - Y) * hd.height / H
                    d.rectangle([cx - 9, cy - 9, cx + 9, cy + 9], outline=(0, 255, 255, 255), width=4)
                for (px, py), col in ((free_px, (255, 0, 255, 255)), (planted_px, (0, 255, 0, 255))):
                    d.ellipse([px - 9, py - 9, px + 9, py + 9], outline=col, width=4)
                strips.append(hd)
        if args.overlay_dir and strips:
            w, h = sum(i.width for i in strips), max(i.height for i in strips)
            sheet, x = Image.new("RGBA", (w, h), (60, 60, 60, 255)), 0
            for i in strips:
                sheet.alpha_composite(i, (x, h - i.height))
                x += i.width
            args.overlay_dir.mkdir(parents=True, exist_ok=True)
            sheet.convert("RGB").save(args.overlay_dir / f"har{args.har}-anim{animation}.png")

    if args.write:
        merge_catalog(new_rows)


def merge_catalog(new_rows: dict[tuple[int, int, int], dict[str, str]]) -> None:
    path = paths.DATA / "pose_catalog.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields, rows = list(reader.fieldnames), list(reader)
    by_key = {(int(r["har"]), int(r["animation"]), int(r["sprite"])): r for r in rows}
    for key, new in new_rows.items():
        row = by_key.get(key)
        if row is None:
            row = dict.fromkeys(fields, "")
            row.update(har=key[0], animation=key[1], sprite=key[2], side=new["side"])
            rows.append(row)
            by_key[key] = row
            flags = []
        else:
            flags = row["flags"].split("|")
        for flag in new["flags"].split("|"):
            if flag not in flags:
                flags.append(flag)
        row["flags"] = "|".join(flags)
        for name, value in new.items():
            if name not in ("side", "flags"):
                row[name] = value
    rows.sort(key=lambda r: (int(r["har"]), int(r["animation"]), int(r["sprite"])))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"merged {len(new_rows)} rows into {path.name}")


if __name__ == "__main__":
    main()
