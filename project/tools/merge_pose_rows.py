"""Merge pose rows exported from the pose editor into pose_catalog.csv.

    python project/tools/merge_pose_rows.py path/to/pose-rows.csv [--dry-run] [--replace]

An exported row may carry only some parts of a pose (its flags). For a sprite already in the
catalog the parts are merged: the exported parts overwrite, the other existing parts (and their
values) are kept, so a partial export never erases an authored arm or leg. Pass --replace to
replace whole rows instead, which is also how to remove a part. New sprites are added. The
merged rows are validated by generate_pose_catalog.py, which also regenerates pose_catalog.c.
A backup of the previous catalog is kept as project/build/pose_catalog.backup.csv.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402

ROOT = paths.ROOT
CATALOG = paths.DATA / "pose_catalog.csv"


def read(path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames), list(reader)


FLAG_FIELDS = {"reach": ("reach",), "arm": ("elbow_y", "elbow_z", "wrist_y", "wrist_z"),
               "leg": ("knee_y", "knee_z", "ankle_y", "ankle_z"),
               "leg2": ("knee2_y", "knee2_z", "ankle2_y", "ankle2_z"), "body": ("body_z",), "lean": ("lean",), "fist": (),
               "arm2": ("elbow2_y", "elbow2_z", "wrist2_y", "wrist2_z"), "drop": ("body_y",)}
FLAG_ORDER = ("reach", "arm", "arm2", "leg", "leg2", "body", "drop", "lean", "fist")


def merge_row(old, new):
    """The old row with the parts named in the new row's flags replaced."""
    if old["side"] != new["side"]:        # the parts belong to different limbs: take the exported row whole
        return dict(new)
    merged = dict(old)
    flags = set(old["flags"].split("|")) | set(new["flags"].split("|"))
    for flag in new["flags"].split("|"):
        for field in FLAG_FIELDS[flag]:
            merged[field] = new[field]
    merged["flags"] = "|".join(f for f in FLAG_ORDER if f in flags)
    merged["side"] = new["side"]
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rows", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace", action="store_true", help="replace whole rows instead of merging parts")
    args = parser.parse_args()
    fields, current = read(CATALOG)
    new_fields, incoming = read(args.rows)
    if new_fields != fields:
        sys.exit(f"Header mismatch.\n  catalog: {fields}\n  export:  {new_fields}")
    key = lambda r: (int(r["har"]), int(r["animation"]), int(r["sprite"]))
    merged = {key(r): r for r in current}
    existing = sum(key(r) in merged for r in incoming)
    added_parts = 0
    for r in incoming:
        k = key(r)
        if k in merged and not args.replace:
            before = set(merged[k]["flags"].split("|"))
            merged[k] = merge_row(merged[k], r)
            added_parts += len(set(merged[k]["flags"].split("|")) - before)
        else:
            merged[k] = r
    verb = "replace" if args.replace else "merge into"
    print(f"{len(incoming)} incoming rows: {existing} {verb} existing rows"
          f"{'' if args.replace else f' ({added_parts} new parts added)'}, {len(incoming) - existing} new; "
          f"catalog {len(current)} -> {len(merged)} rows")
    if args.dry_run:
        return
    backup = paths.ARTIFACTS / "pose_catalog.backup.csv"
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(CATALOG, backup)
    with CATALOG.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(merged[k] for k in sorted(merged))
    result = subprocess.run([sys.executable, str(HERE / "generate_pose_catalog.py")], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.returncode:
        shutil.copy2(backup, CATALOG)
        sys.exit(f"Validation failed, catalog restored from backup:\n{result.stderr.strip()}")


if __name__ == "__main__":
    main()
