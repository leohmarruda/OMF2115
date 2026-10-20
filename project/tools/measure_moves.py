"""Measure Jaguar and Shadow moves with OpenOMF (original rules and AF data).

Every fixture is derived from the unchanged rectests/6P.REC (Crystal/Jaguar vs
Shirro/Shadow, Stadium). The harness only edits a *copy* of that recording with
rectool: it sets the fighters' starting X positions, adds the attacker's input
sequence taken verbatim from the AF move string, and optionally makes the
defender hold standing or low guard. OpenOMF (built with OMF3K_SOURCE_TRACE=ON)
replays each fixture headlessly and writes a per-tick trace; all timing,
reach, damage and guard results below come from that trace.

Outputs (local, in build/omf_trace_z7/moves/): one .REC/.csv per run plus
summary.csv and summary.md.

Usage (repository root):
    py -3 project/prototype/measure_moves.py            # all moves
    py -3 project/prototype/measure_moves.py --har jaguar --move 41
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "build" / "omf_trace_z7"
OPENOMF = SOURCE_DIR / "openomf.exe"
RECTOOL = ROOT / "build" / "omf_debug_z7" / "rectool.exe"
BASE_REC = ROOT / "rectests" / "6P.REC"
OUT = SOURCE_DIR / "moves"

INPUT_TICK = 126          # tick of the final (button) input, as in the existing fixtures
POSITION_TICK = 123       # tick at which fighter X positions are set
END_TICK = 300            # keep-alive assertion so playback continues past recovery
PUNCH, KICK = 0x01, 0x02
# REC direction nibbles (screen directions).
SCREEN = {"U": 0x10, "UR": 0x20, "R": 0x30, "DR": 0x40, "D": 0x50, "DL": 0x60, "L": 0x70, "UL": 0x80}
# Numpad directions relative to facing; 6 = forward.
NUMPAD_RIGHT = {"1": "DL", "2": "D", "3": "DR", "4": "L", "6": "R", "7": "UL", "8": "U", "9": "UR"}
NUMPAD_LEFT = {"1": "DR", "2": "D", "3": "DL", "4": "R", "6": "L", "7": "UR", "8": "U", "9": "UL"}

STATE_NAMES = {1: "standing", 2: "walk-to", 3: "walk-from", 4: "crouch", 5: "crouch-block", 6: "jump",
               7: "recoil", 8: "standing-up", 9: "stunned", 10: "blockstun", 11: "victory", 12: "defeat",
               15: "wall-damage"}


@dataclass
class Move:
    har: str           # "jaguar" (player 0, faces right) or "shadow" (player 1, faces left)
    move_id: int       # AF move / animation id
    string: str        # AF move string, e.g. "P6321"
    name: str
    jump: bool = False  # air attack: neutral jump first, button at the apex window
    gaps: list[int] = field(default_factory=lambda: [30, 40, 55, 70, 85, 100, 120, 140, 170, 200])


# Ground and air attacks that have a selectable input in the original AF data.
MOVES = [
    Move("jaguar", 42, "P", "standing punch"),
    Move("jaguar", 41, "K", "standing kick"),
    Move("jaguar", 23, "P3", "down-forward punch"),
    Move("jaguar", 30, "P2", "down punch"),
    Move("jaguar", 32, "P1", "down-back punch"),
    Move("jaguar", 27, "P4", "back punch"),
    Move("jaguar", 18, "K3", "down-forward kick"),
    Move("jaguar", 19, "K2", "down kick"),
    Move("jaguar", 33, "K1", "down-back kick"),
    Move("jaguar", 24, "K4", "back kick"),
    Move("jaguar", 20, "P6", "close throw", gaps=[25, 30, 35, 40, 45, 50, 60]),
    Move("jaguar", 17, "P63", "leap (grounded P63)"),
    Move("jaguar", 16, "P6321", "overhead throw special (P6321)"),
    Move("jaguar", 21, "P41", "concussion cannon", gaps=[40, 100, 190]),
    Move("jaguar", 44, "P", "jump punch", jump=True, gaps=[20, 30, 40, 55, 70, 85]),
    Move("jaguar", 43, "K", "jump kick", jump=True, gaps=[20, 30, 40, 55, 70, 85]),
    Move("shadow", 43, "P", "standing punch"),
    Move("shadow", 42, "K", "standing kick"),
    Move("shadow", 41, "P6", "forward punch"),
    Move("shadow", 15, "P3", "down-forward punch"),
    Move("shadow", 36, "P2", "down punch"),
    Move("shadow", 31, "P1", "down-back punch"),
    Move("shadow", 30, "P4", "back punch"),
    Move("shadow", 17, "K3", "down-forward kick"),
    Move("shadow", 18, "K2", "down kick"),
    Move("shadow", 19, "K1", "down-back kick"),
    Move("shadow", 32, "K6", "forward kick"),
    Move("shadow", 33, "K4", "back kick"),
    Move("shadow", 20, "P6", "close throw", gaps=[25, 30, 35, 40, 45, 50, 60]),
    Move("shadow", 16, "P252", "P252 special"),
    Move("shadow", 24, "P41", "P41 special (unenhanced)"),
    Move("shadow", 21, "K41", "K41 special"),
    Move("shadow", 46, "P", "jump punch", jump=True, gaps=[20, 30, 40, 55, 70, 85]),
    Move("shadow", 68, "K", "jump kick", jump=True, gaps=[20, 30, 40, 55, 70, 85]),
]


def rectool(*args: str) -> str:
    r = subprocess.run([str(RECTOOL), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rectool {' '.join(args)} failed: {r.stdout}{r.stderr}")
    return r.stdout


def move_count(rec: Path) -> int:
    lines = [l for l in rectool("-f", str(rec)).splitlines() if l[:6].strip().isdigit()]
    return int(lines[-1].split()[0]) + 1 if lines else 0


def append_action(rec: Path, tick: int, player: int, action: int) -> None:
    slot = move_count(rec)
    # rectool's "-i" is ambiguous (--inplace / --insert); always use long options.
    rectool("-f", str(rec), "--inplace", f"--insert={slot}")
    for key, value in (("tick", tick), ("lookup_id", 2), ("player_id", player), ("action", action)):
        rectool("-f", str(rec), "--inplace", "-k", "entry", "-k", str(slot), "-k", key, "-s", str(value))


def assert_set_x(rec: Path, har: int, x: int) -> None:
    rectool("-f", str(rec), "--inplace", "--assert", "--assertion_tick", str(POSITION_TICK),
            "--operator", "set", "--operand1", f"har{har + 1}", "--operand1_value", "xpos",
            "--operand2", "literal", "--operand2_value", str(x))


def input_schedule(move: Move) -> list[tuple[int, int]]:
    """Inputs (tick, action) for the attacker, derived from the AF move string."""
    facing = NUMPAD_RIGHT if move.har == "jaguar" else NUMPAD_LEFT
    button = PUNCH if move.string[0] == "P" else KICK
    dirs = [SCREEN[facing[c]] for c in reversed(move.string[1:])]  # AF strings list newest input first
    if move.jump:
        # Neutral jump, then the button a few ticks later while airborne.
        return [(INPUT_TICK - 6, SCREEN["U"]), (INPUT_TICK - 5, 0x00), (INPUT_TICK, button), (INPUT_TICK + 1, 0x00)]
    schedule = []
    for i, d in enumerate(dirs):
        schedule.append((INPUT_TICK - 2 * (len(dirs) - i), d))
    schedule.append((INPUT_TICK, (dirs[-1] if dirs else 0) | button))
    schedule.append((INPUT_TICK + 1, 0x00))
    return schedule


def build_fixture(path: Path, move: Move, gap: int, guard: str) -> None:
    shutil.copyfile(BASE_REC, path)
    rectool("-f", str(path), "--inplace", "--truncate", "115")
    attacker = 0 if move.har == "jaguar" else 1
    defender = 1 - attacker
    ax = 100 if attacker == 0 else 220
    dx = ax + gap if attacker == 0 else ax - gap
    assert_set_x(path, attacker, ax)
    assert_set_x(path, defender, dx)
    events = [(t, attacker, a) for t, a in input_schedule(move)]
    if guard != "none":
        back = "R" if defender == 1 else "L"          # defender faces the attacker
        hold = SCREEN[back] if guard == "high" else SCREEN["DR" if defender == 1 else "DL"]
        events.append((POSITION_TICK + 1, defender, hold))
    for tick, player, action in sorted(events):
        append_action(path, tick, player, action)
    rectool("-f", str(path), "--inplace", "--assert", "--assertion_tick", str(END_TICK),
            "--operator", "gt", "--operand1", "har1", "--operand1_value", "xpos",
            "--operand2", "literal", "--operand2_value", "0")


def run_fixture(rec: Path, trace: Path) -> list[dict]:
    with tempfile.TemporaryDirectory() as state:
        env = os.environ.copy()
        env.update({"OPENOMF_RESOURCE_PATH": str(SOURCE_DIR), "OPENOMF_STATE_PATH": state,
                    "OPENOMF_CONFIG_PATH": state, "OMF3K_TRACE_PATH": str(trace)})
        for k in ("OMF3K_INPUT_PATH", "OMF3K_INPUT_MAP", "OMF3K_STATE_MAP"):
            env.pop(k, None)
        subprocess.run([str(OPENOMF), "--force-renderer=NULL", "--force-audio-backend=NULL", "--warp",
                        "--log-level=ERROR", "-P", str(rec)], cwd=state, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    with trace.open(newline="") as f:
        return list(csv.DictReader(f))


def analyse(rows: list[dict], move: Move) -> dict:
    attacker = "0" if move.har == "jaguar" else "1"
    defender = "1" if attacker == "0" else "0"
    a = {int(r["tick"]): r for r in rows if r["player"] == attacker}
    d = {int(r["tick"]): r for r in rows if r["player"] == defender}
    gap = abs(float(a[INPUT_TICK - 1]["x"]) - float(d[INPUT_TICK - 1]["x"]))
    anim = [t for t, r in a.items() if t >= INPUT_TICK - 8 and int(r["animation"]) == move.move_id]
    res = {"gap": round(gap, 1), "performed": bool(anim)}
    if anim:
        start, end = min(anim), max(anim)
        res.update(anim_start=start, anim_ticks=end - start + 1)
        # First tick the attacker is back to a neutral standing/crouching state after the move.
        rec = next((t for t in sorted(a) if t > end and int(a[t]["state"]) in (1, 4) and
                    int(a[t]["animation"]) in (11, 4, 2, 3, 10)), None)
        res["attacker_free"] = rec
    hp0 = int(d[INPUT_TICK - 1]["health"])
    hit_tick = next((t for t in sorted(d) if t >= INPUT_TICK and int(d[t]["health"]) < hp0), None)
    block_tick = next((t for t in sorted(d) if t >= INPUT_TICK and
                       int(d[t].get("block_mask", 0) or 0) & (1 << int(defender))), None)
    if hit_tick is None and block_tick is None:
        block_tick = next((t for t in sorted(d) if t >= INPUT_TICK and int(d[t]["state"]) == 10), None)
    contact = hit_tick if hit_tick is not None else block_tick
    res["result"] = "hit" if hit_tick is not None else ("block" if block_tick is not None else "miss")
    if contact is not None:
        res["contact_tick"] = contact
        if res.get("anim_start") is not None:
            res["startup"] = contact - res["anim_start"]
        if hit_tick is not None:
            res["damage"] = hp0 - int(d[hit_tick]["health"])
        states = []
        free = None
        for t in sorted(d):
            if t < contact:
                continue
            s = int(d[t]["state"])
            if not states or states[-1] != s:
                states.append(s)
            if t > contact and s in (1, 4, 5) and int(d[t]["animation"]) in (11, 4, 5, 6):
                free = t
                break
        res["reaction"] = ">".join(STATE_NAMES.get(s, str(s)) for s in states)
        res["defender_free"] = free
        if free is not None and res.get("attacker_free") is not None:
            res["advantage"] = free - res["attacker_free"]  # >0 means the attacker recovers first
    return res


def job(move: Move, gap: int, guard: str) -> tuple[Move, int, str, dict]:
    stem = f"{move.har}-{move.move_id}-{guard}-{gap}"
    rec, trace = OUT / f"{stem}.REC", OUT / f"{stem}.csv"
    if trace.exists() and trace.stat().st_size > 0:
        # Reuse a finished trace so interrupted batches can resume.
        with trace.open(newline="") as f:
            rows = list(csv.DictReader(f))
        if rows and int(rows[-1]["tick"]) >= END_TICK - 1:
            return move, gap, guard, analyse(rows, move)
    build_fixture(rec, move, gap, guard)
    return move, gap, guard, analyse(run_fixture(rec, trace), move)


def measure(move: Move, pool: cf.Executor) -> dict:
    sweep = {gap: r for _, gap, _, r in pool.map(lambda g: job(move, g, "none"), move.gaps)}
    hits = sorted(g for g, r in sweep.items() if r["result"] == "hit")
    out = {"move": move, "sweep": sweep, "performed": any(r["performed"] for r in sweep.values())}
    if not hits:
        return out
    # Refine the far edge of the hit range to one source unit.
    lo = max(hits)
    misses = sorted(g for g, r in sweep.items() if g > lo and r["result"] != "hit")
    if misses:
        hi = misses[0]
        while hi - lo > 1:
            mid = (lo + hi) // 2
            r = job(move, mid, "none")[3]
            sweep[mid] = r
            if r["result"] == "hit":
                lo = mid
            else:
                hi = mid
        out["max_gap_hit"], out["min_gap_miss"] = sweep[lo]["gap"], sweep[hi]["gap"]
    else:
        out["max_gap_hit"], out["min_gap_miss"] = sweep[lo]["gap"], None
    out["hit"] = sweep[min(hits)]
    ref_gap = min(hits)
    guards = list(pool.map(lambda g: job(move, ref_gap, g), ["high", "low"]))
    out["guard"] = {g: r for _, _, g, r in guards}
    return out


def fmt(v) -> str:
    return "–" if v is None else str(v)


def write_summary(results: list[dict]) -> None:
    fields = ["har", "move", "input", "name", "performed", "anim_ticks", "startup", "damage", "max_gap_hit",
              "min_gap_miss", "hit_reaction", "hit_advantage", "high_guard", "high_advantage", "low_guard",
              "low_advantage"]
    rows = []
    for res in results:
        m, hit, guard = res["move"], res.get("hit", {}), res.get("guard", {})
        rows.append({
            "har": m.har, "move": m.move_id, "input": m.string, "name": m.name,
            "performed": res["performed"], "anim_ticks": hit.get("anim_ticks"), "startup": hit.get("startup"),
            "damage": hit.get("damage"), "max_gap_hit": res.get("max_gap_hit"),
            "min_gap_miss": res.get("min_gap_miss"), "hit_reaction": hit.get("reaction"),
            "hit_advantage": hit.get("advantage"),
            "high_guard": guard.get("high", {}).get("result"), "high_advantage": guard.get("high", {}).get("advantage"),
            "low_guard": guard.get("low", {}).get("result"), "low_advantage": guard.get("low", {}).get("advantage"),
        })
    with (OUT / "summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    lines = ["| HAR | Move | Input | Name | Anim ticks | Startup | Damage | Max hit gap | Hit reaction | "
             "Adv. on hit | High guard (adv.) | Low guard (adv.) |",
             "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |"]
    for r in rows:
        if not r["performed"]:
            lines.append(f"| {r['har']} | {r['move']} | `{r['input']}` | {r['name']} | not performed | | | | | | | |")
            continue
        lines.append(
            f"| {r['har']} | {r['move']} | `{r['input']}` | {r['name']} | {fmt(r['anim_ticks'])} | "
            f"{fmt(r['startup'])} | {fmt(r['damage'])} | {fmt(r['max_gap_hit'])} | {fmt(r['hit_reaction'])} | "
            f"{fmt(r['hit_advantage'])} | {fmt(r['high_guard'])} ({fmt(r['high_advantage'])}) | "
            f"{fmt(r['low_guard'])} ({fmt(r['low_advantage'])}) |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--har", choices=["jaguar", "shadow"])
    ap.add_argument("--move", type=int)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    for exe in (OPENOMF, RECTOOL, BASE_REC):
        if not exe.exists():
            raise SystemExit(f"Missing {exe}")
    OUT.mkdir(parents=True, exist_ok=True)
    moves = [m for m in MOVES if (not args.har or m.har == args.har) and (args.move is None or m.move_id == args.move)]
    results = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for m in moves:
            r = measure(m, pool)
            results.append(r)
            hit = r.get("hit", {})
            print(f"{m.har:6} {m.move_id:3} {m.string:6} performed={r['performed']} startup={hit.get('startup')} "
                  f"dmg={hit.get('damage')} max_gap={r.get('max_gap_hit')} guard="
                  f"{ {k: v['result'] for k, v in r.get('guard', {}).items()} }", flush=True)
    write_summary(results)
    print(f"Wrote {OUT / 'summary.md'}")


if __name__ == "__main__":
    main()
