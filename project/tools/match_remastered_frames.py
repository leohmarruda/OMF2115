"""Match indexed OpenOMF sprite PNGs to OMF Remastered's HD atlas.

Prints the exact Remastered atlas entry for each original sprite. Optional
local crops are reference material and should stay in the ignored build tree.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


MASK = 0xFFFFFFFF
PRIME = 0x01000193


def fnv1a(data: bytes, seed: int) -> int:
    value = seed
    for byte in data:
        value = ((value ^ byte) * PRIME) & MASK
    return value


def pixel_hash(image: Image.Image) -> str:
    if image.mode != "P":
        raise ValueError("Source sprites must be indexed PNGs (mode P)")
    width, height = image.size
    pixels = image.tobytes()
    header = bytes((width & 255, (width >> 8) & 255,
                    height & 255, (height >> 8) & 255))
    first = fnv1a(pixels, fnv1a(header, 0x811C9DC5))
    second = (0x9747B28C ^ ((width * 0x85EBCA6B) & MASK)
              ^ ((height * 0xC2B2AE35) & MASK)) & MASK
    for byte in reversed(pixels):
        second = ((second ^ byte) * PRIME) & MASK
    return f"{first:08x}{second:08x}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hd_root", type=Path, help="Remastered public/hd folder")
    parser.add_argument("source_sprites", type=Path, help="OpenOMF sprite PNG folder")
    parser.add_argument("--extract-dir", type=Path,
                        help="Write matched HD crops for local visual review")
    args = parser.parse_args()
    index = json.loads((args.hd_root / "index.json").read_text(encoding="utf-8"))
    by_hash = {}
    for entry in index["entries"]:
        if entry["kind"] == "fighter":
            by_hash.setdefault(entry["hash"], []).append(entry)
    if args.extract_dir:
        args.extract_dir.mkdir(parents=True, exist_ok=True)
    missing = 0
    for source in sorted(args.source_sprites.glob("sprite-*.png")):
        with Image.open(source) as image:
            fingerprint = pixel_hash(image)
        matches = by_hash.get(fingerprint, [])
        if not matches:
            print(f"{source.name}: no HD match ({fingerprint})")
            missing += 1
            continue
        for entry in matches:
            print(f"{source.name}: {entry['bundle']}/page_{entry['page']}.webp "
                  f"({entry['x']},{entry['y']},{entry['w']},{entry['h']}) {fingerprint}")
            if args.extract_dir:
                page = args.hd_root / entry["bundle"] / f"page_{entry['page']}.webp"
                with Image.open(page) as atlas:
                    bounds = (entry["x"], entry["y"],
                              entry["x"] + entry["w"], entry["y"] + entry["h"])
                    atlas.crop(bounds).save(args.extract_dir / source.name)
    if missing:
        raise SystemExit(f"{missing} source sprites have no matching HD frame")


if __name__ == "__main__":
    main()
