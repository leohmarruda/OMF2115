"""Build an HD copy of the local 16-pose robot reference gallery.

Each original indexed PNG is fingerprinted and replaced with its exact
OMF 2097 Remastered atlas frame. Both generated galleries stay in locally
ignored documentation folders.
"""

from __future__ import annotations

import argparse
import csv
from io import BytesIO
import json
from pathlib import Path
import zipfile

from PIL import Image

from match_remastered_frames import pixel_hash


ROOT = Path(__file__).resolve().parents[2]
EXTRA_ROBOTS = ("glacier", "tempest", "helix", "spectre")
EXTRA_POSES = (
    ("01-idle", "Idle stance", 11, 0),
    ("02-walk", "Walking", 10, 3),
    ("03-jump", "Jumping", 1, 3),
    ("04-crouch", "Crouching", 4, 0),
    ("05-block-high", "Standing guard", 5, 0),
    ("06-block-low", "Crouching guard", 6, 0),
    ("07-punch", "Standing punch", 42, 3),
    ("08-kick", "Standing kick", 41, 3),
    ("09-low-punch", "Low punch", 30, 3),
    ("10-throw", "Close throw", 20, 3),
    ("11-hit", "Taking a hit", 9, 5),
    ("12-victory", "Victory", 48, 6),
    ("13-defeat", "Defeat", 49, 1),
    ("14-special", "Special move", 15, 2),
    ("15-low-kick", "Low kick", 31, 2),
    ("16-air-attack", "Second special move", 16, 2),
)


def render_extra_robots(mod_path: Path, output: Path) -> tuple[list[dict[str, object]], list[str]]:
    manifest: list[dict[str, object]] = []
    master_rows: list[str] = []
    with zipfile.ZipFile(mod_path) as bundle:
        for slug in EXTRA_ROBOTS:
            base = f"robots/{slug}/"
            info = json.loads(bundle.read(base + "robot.json"))
            hd = json.loads(bundle.read(base + "hd.json"))
            frames = {(entry["anim"], entry["sprite"]): entry for entry in hd["sprites"]}
            folder = output / slug
            folder.mkdir(parents=True, exist_ok=True)
            lines = [f"# {slug.title()} HD pose references", "",
                     "Frames from the optional Remastered *New robots and arenas* mod. "
                     "These robots have no original 1994 sprite counterparts.", "",
                     "| Pose | Remastered frame | Picture |", "| --- | --- | --- |"]
            for stem, label, animation, wanted_sprite in EXTRA_POSES:
                available = [sprite for move, sprite in frames
                             if move == animation and sprite <= wanted_sprite]
                if not available:
                    raise ValueError(f"No HD frame for {slug} animation {animation}")
                sprite = max(available)
                entry = frames[(animation, sprite)]
                source = base + entry["file"]
                target = folder / f"{stem}.png"
                with Image.open(BytesIO(bundle.read(source))) as image:
                    image.save(target)
                    width, height = image.size
                if animation in (15, 16):
                    label = info.get("moves", {}).get(str(animation), label).title()
                lines.append(f"| {label} | Animation {animation}, sprite {sprite} | "
                             f"![{slug.title()} {label}]({stem}.png) |")
                manifest.append({
                    "robot": slug, "pose": stem,
                    "original_width": "", "original_height": "",
                    "hd_width": width, "hd_height": height,
                    "fingerprint": entry["hash"],
                    "atlas_page": f"{mod_path.name}:{source}",
                    "atlas_x": "", "atlas_y": "",
                })
            lines.extend(["", "The approved OMF3K robot designs remain separate from these Remastered references."])
            (folder / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            master_rows.append(
                f"| {slug.title()} (Remastered) | ![{slug} idle]({slug}/01-idle.png) | "
                f"![{slug} punch]({slug}/07-punch.png) | "
                f"![{slug} special]({slug}/14-special.png) | [16 poses]({slug}/index.md) |"
            )
    return manifest, master_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "omf3k/docs/OMF2097/poses")
    parser.add_argument("--output", type=Path, default=ROOT / "omf3k/docs/Remastered/poses")
    parser.add_argument("--hd-root", type=Path,
                        default=ROOT.parent / "OMF-2097-Remastered/public/hd")
    parser.add_argument("--extras-mod", type=Path,
                        default=ROOT.parent / "OMF-2097-Remastered/public/mods/omf2097r.extras.omfmod")
    args = parser.parse_args()

    index = json.loads((args.hd_root / "index.json").read_text(encoding="utf-8"))
    by_hash: dict[str, list[dict]] = {}
    for entry in index["entries"]:
        if entry["kind"] == "fighter":
            by_hash.setdefault(entry["hash"], []).append(entry)

    sources = sorted(args.source.glob("*/*.png"))
    if not sources:
        parser.error(f"No original pose PNGs found in {args.source}")

    resolved: list[tuple[Path, dict, str, tuple[int, int]]] = []
    missing: list[str] = []
    for source in sources:
        with Image.open(source) as original:
            fingerprint = pixel_hash(original)
            original_size = original.size
        bundle = f"fighter-{source.parent.name.upper()}"
        matches = [entry for entry in by_hash.get(fingerprint, [])
                   if entry["bundle"] == bundle]
        if len(matches) != 1:
            missing.append(f"{source.relative_to(args.source)}: {len(matches)} exact HD matches")
            continue
        resolved.append((source, matches[0], fingerprint, original_size))
    if missing:
        raise SystemExit("Cannot build a complete HD gallery:\n" + "\n".join(missing))

    args.output.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    pages: dict[Path, list[tuple[Path, dict, str, tuple[int, int]]]] = {}
    for source, entry, fingerprint, original_size in resolved:
        page = args.hd_root / entry["bundle"] / f"page_{entry['page']}.webp"
        pages.setdefault(page, []).append((source, entry, fingerprint, original_size))
    for page, frames in pages.items():
        with Image.open(page) as atlas:
            for source, entry, fingerprint, original_size in frames:
                destination = args.output / source.relative_to(args.source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                bounds = (entry["x"], entry["y"], entry["x"] + entry["w"],
                          entry["y"] + entry["h"])
                if bounds[2] > atlas.width or bounds[3] > atlas.height:
                    raise ValueError(f"Atlas bounds exceed {page}: {bounds}")
                atlas.crop(bounds).save(destination)
                manifest.append({
                    "robot": source.parent.name,
                    "pose": source.stem,
                    "original_width": original_size[0],
                    "original_height": original_size[1],
                    "hd_width": entry["w"],
                    "hd_height": entry["h"],
                    "fingerprint": fingerprint,
                    "atlas_page": f"{entry['bundle']}/page_{entry['page']}.webp",
                    "atlas_x": entry["x"],
                    "atlas_y": entry["y"],
                })

    extra_manifest, extra_rows = render_extra_robots(args.extras_mod, args.output)
    manifest.extend(extra_manifest)
    for source in [args.source / "index.md", *sorted(args.source.glob("*/index.md"))]:
        if not source.is_file():
            raise FileNotFoundError(source)
        body = source.read_text(encoding="utf-8")
        if source.parent == args.source:
            body = body.replace("# Original robot pose references",
                                "# Remastered HD robot pose references")
            lines = body.splitlines()
            lines[2] = ("Higher-resolution side-view frames from the local OMF 2097 Remastered assets. "
                        "The original eleven robots were matched by pixel fingerprint; "
                        "Glacier, Tempest, Helix, and Spectre come from Remastered's optional "
                        "new-robots mod. These are pose and detail references; their colors and "
                        "armor styling may differ from the approved OMF3K designs. The images "
                        "stay in this locally ignored documentation folder.")
            body = "\n".join(lines) + "\n"
            body = body.replace("\n\nA full 3D turnaround requires",
                                "\n" + "\n".join(extra_rows) + "\n\nA full 3D turnaround requires")
            body = body.replace("beyond these original side-view frames",
                                "beyond these HD side-view references")
        else:
            body = body.replace(" pose references\n", " HD pose references\n", 1)
            body = body.replace("Original side-view frames", "Matched Remastered HD side-view frames")
            body = body.replace("Exact original side-view sprite frames", "Exact matching Remastered HD side-view frames")
            body = body.replace("HD side-view frames from `FIGHTR",
                                "HD side-view frames matched to `FIGHTR")
            body = body.replace("Matched Remastered HD side-view frames matched to",
                                "Remastered HD side-view frames matched to")
            body = body.replace("These are reference images for redesign, not improved artwork.",
                                "These are pose and detail references, not approved OMF3K designs.")
            body = body.replace("Original game data stays local in the ignored build folder.",
                                "The images stay local in the ignored build folder.")
            body = body.replace("Original game data stays local in this ignored documentation folder.",
                                "The images stay in this locally ignored documentation folder.")
        destination = args.output / source.relative_to(args.source)
        destination.write_text(body, encoding="utf-8")

    manifest_path = args.output / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=manifest[0].keys())
        writer.writeheader()
        writer.writerows(manifest)
    print(f"Saved {len(manifest)} HD poses across 15 robots "
          f"({len(resolved)} exact original matches, {len(extra_manifest)} new-robot frames): {args.output}")
    print(f"Atlas provenance: {manifest_path}")


if __name__ == "__main__":
    main()
