"""Build a local HTML browser for comparing moves: original sprite | blockout | Meshy.

For every player-triggered Jaguar and Shadow animation it exports the original sprites,
and for moves that appear in a recorded trace it captures the viewer at the first tick of
each sprite, once with the blockout and once with OMF3K_MESHY=1. Output goes to
project/build/move-browser/ (ignored by git; it contains original game art). Open
project/build/move-browser/index.html in a browser.

    python project/tools/generate_move_browser.py            # new captures only
    python project/prototype/generate_move_browser.py --refresh  # redo every capture
    python project/prototype/generate_move_browser.py --html-only
    python project/prototype/generate_move_browser.py --har 1 --animation 33   # one move
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # noqa: E402

ROOT = paths.ROOT
BUILD = paths.ARTIFACTS
OUT = BUILD / "move-browser"
CAPTURES = OUT / "captures"
EXE = paths.EXE
TRACES = paths.TRACE_DIR
SPRITES = BUILD / "pose-reference"
CAPTURE_FILE = BUILD / "omf3d_source_replay_capture.bmp"
HAR_DIRS = {0: "jaguar", 1: "shadow"}


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, cwd=ROOT, capture_output=True)


def load_moves():
    run(HERE / "generate_move_catalog.py")
    with (BUILD / "move-catalog.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["kind"] in ("basic", "special")]


def sprite_dir(har, anim):
    return SPRITES / HAR_DIRS[har] / str(anim)


def export_sprites(har, anim):
    if not any(sprite_dir(har, anim).glob("sprite-*.png")):
        run(HERE / "pose_inventory.py", "--har", har, "--animation", anim, "--export-sprites")


SYNTHETIC = OUT / "synthetic"
HEADER = ("tick,player,har,health,max_health,x,y,vx,vy,facing,state,move,animation,sprite,animation_tick,"
          "match_winner,hit_mask,block_mask,round_winner")


def synthetic_trace(har, anim, count):
    """A trace that holds one sprite of the move per tick, so the viewer can render it.

    The fighter stands at the middle of the arena facing a idle opponent of the other HAR. This
    shows each sprite's pose, not the move's travel, timing or contact.
    """
    SYNTHETIC.mkdir(parents=True, exist_ok=True)
    path = SYNTHETIC / f"h{har}_a{anim}.csv"
    rows = [HEADER]
    for tick in range(count):
        for player, h, x, facing in ((0, 0, 130.0, 1), (1, 1, 210.0, -1)):
            acting = h == har
            rows.append(",".join(str(v) for v in (
                tick, player, h, 213 if h == 0 else 196, 213 if h == 0 else 196, f"{x:.3f}", "190.000",
                "0.000", "0.000", facing, 1, 1 if acting else 0, anim if acting else 11,
                tick if acting else 0, 3 if acting else 2, -1, 0, 0, -1)))
    path.write_text(chr(10).join(rows) + chr(10), encoding="utf-8")
    return path, {s: s for s in range(count)}


def sprite_ticks(har, anim, trace_name):
    """First tick of each sprite in the longest run of this animation in the trace."""
    runs, current, last = [], [], None
    with (TRACES / trace_name).open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                if int(r["har"]) != har:          # the trace interleaves both fighters' rows
                    continue
                playing = int(r["animation"]) == anim
                tick, sprite = int(r["tick"]), int(r["sprite"])
            except (TypeError, ValueError):
                continue
            if playing and (last is None or tick <= last + 1):
                current.append((tick, sprite))
            elif playing:
                runs.append(current); current = [(tick, sprite)]
            elif current:
                runs.append(current); current = []
            last = tick if playing else None
    if current:
        runs.append(current)
    if not runs:
        return {}
    best = max(runs, key=len)
    first = {}
    for tick, sprite in best:
        first.setdefault(sprite, tick)
    return first


_positions = {}


def fighter_screen_x(trace_path, tick):
    """Screen x (pixels of the 960 wide frame) of both fighters at a tick, from the trace.

    The replay camera is fixed at world x=0 and world x = (source x - 160) * 7.6 / 280, so
    NDC x is world x * .96 / (3.0 * aspect) with aspect 1.6.
    """
    trace_name = str(trace_path)
    if trace_name not in _positions:
        table = defaultdict(list)
        with Path(trace_path).open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    table[int(r["tick"])].append(float(r["x"]))
                except (TypeError, ValueError):
                    continue
        _positions[trace_name] = table
    xs = _positions[trace_name].get(tick) or [160.0]
    return [480 + ((x - 160) * 7.6 / 280) * .96 / (3.0 * 1.6) * 480 for x in xs]


def crop_box(trace_path, tick):
    """A box around both fighters, widened when they are far apart.

    The top is fixed below the HUD (names and health end near y=112) and the bottom is the floor,
    so no captions end up in the picture.
    """
    xs = fighter_screen_x(trace_path, tick)
    centre, spread = sum(xs) / len(xs), max(xs) - min(xs)
    width = min(max(448, spread * 1.3 + 220), 960)
    left = min(max(centre - width / 2, 0), 960 - width)
    return (int(left), 112, int(left + width), 420)


def capture(trace_path, tick, dest, meshy):
    env = dict(os.environ)
    env.pop("OMF3K_MESHY", None)
    if meshy:
        env["OMF3K_MESHY"] = "1"
    CAPTURE_FILE.unlink(missing_ok=True)
    subprocess.run([str(EXE), "--source-replay", str(trace_path), "--capture-tick", str(tick)],
                   env=env, cwd=ROOT, capture_output=True, timeout=180)
    if not CAPTURE_FILE.exists():
        return False
    from PIL import Image
    frame = Image.open(CAPTURE_FILE).convert("RGB")
    left, top, right, bottom = crop_box(trace_path, tick)
    frame.crop((left, top, right, bottom)).save(dest, optimize=True)
    return True


def build_data(moves, args):
    CAPTURES.mkdir(parents=True, exist_ok=True)
    data = []
    for i, m in enumerate(moves, 1):
        har, anim, count = int(m["har"]), int(m["animation"]), int(m["sprites"])
        # --har/--animation limit which moves are recaptured; the page always lists every move.
        selected = ((args.har is None or har == args.har) and
                    (args.animation is None or anim == args.animation))
        export_sprites(har, anim)
        recorded = sprite_ticks(har, anim, m["trace"]) if m["trace"] else {}
        synthetic = synthetic_trace(har, anim, count)
        frames = []
        for s in range(count):
            original = sprite_dir(har, anim) / f"sprite-{s:02d}.png"
            if s in recorded:
                trace_path, tick, source = TRACES / m["trace"], recorded[s], "recorded"
            else:
                trace_path, tick, source = synthetic[0], synthetic[1][s], "synthetic"
            entry = {"sprite": s, "original": os.path.relpath(original, OUT).replace("\\", "/")
                     if original.exists() else "", "tick": tick, "source": source, "blk": "", "meshy": ""}
            for key, meshy in (("blk", False), ("meshy", True)):
                dest = CAPTURES / f"h{har}_a{anim}_s{s}_{key}.png"
                if selected and not args.html_only and (args.refresh or not dest.exists()):
                    print(f"[{i}/{len(moves)}] {HAR_DIRS[har]} anim {anim} sprite {s} {key} ({source})", flush=True)
                    capture(trace_path, tick, dest, meshy)
                if dest.exists():
                    entry[key] = os.path.relpath(dest, OUT).replace("\\", "/")
            frames.append(entry)
        data.append({**{k: m[k] for k in ("har_name", "name", "name_confidence", "input_code", "input",
                                          "status", "trace", "trace_tick")},
                     "har": har, "animation": anim, "sprites": count, "same": m["same_sprites_as"],
                     "authored": int(m["authored_sprites"]), "frames": frames})
    return data


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OMF2115 move browser</title>
<style>
:root{--bg:#0e1319;--panel:#171e27;--line:#2a3441;--text:#dbe4ee;--dim:#8b9bad;--accent:#58b6e8;
--ok:#4fbf7a;--warn:#e0b341;--bad:#e0675c}
@media (prefers-color-scheme:light){:root{--bg:#f3f5f8;--panel:#fff;--line:#d5dce5;--text:#1b2430;--dim:#5b6b7d;
--accent:#1a78b3;--ok:#1f8f4e;--warn:#a87a00;--bad:#c0392b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:17px;margin:0 0 8px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
select,input[type=search]{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font:inherit}
input[type=search]{min-width:200px}label{color:var(--dim);display:flex;gap:4px;align-items:center}
#count{color:var(--dim);margin-left:auto}
main{padding:16px;display:grid;gap:16px;max-width:1500px;margin:auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.head{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline;padding:10px 14px;border-bottom:1px solid var(--line)}
.head h2{font-size:15px;margin:0}.meta{color:var(--dim);font-size:13px}
.badge{font-size:12px;border-radius:99px;padding:1px 9px;border:1px solid currentColor}
.badge.dup{color:var(--accent)}.authored{color:var(--ok)}.partial{color:var(--warn)}.generic{color:var(--bad)}
.grid{display:grid;grid-template-columns:90px repeat(3,minmax(0,1fr));gap:8px;padding:10px 14px;align-items:start}
.grid .col{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.tag{color:var(--dim);font-size:12px;padding-top:6px}
.cell{background:var(--bg);border:1px solid var(--line);border-radius:6px;min-height:80px;display:flex;
align-items:center;justify-content:center;overflow:hidden}
.cell img{width:100%;height:auto;display:block;cursor:zoom-in;image-rendering:auto}
.cell.sprite img{image-rendering:pixelated;max-height:220px;object-fit:contain}
.none{color:var(--dim);font-size:12px;padding:8px;text-align:center}
code{font:12px ui-monospace,Consolas,monospace;color:var(--dim);word-break:break-all}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9;cursor:zoom-out}
#lb img{max-width:96vw;max-height:94vh;image-rendering:auto}
@media (max-width:760px){.grid{grid-template-columns:60px repeat(3,minmax(0,1fr));gap:4px;padding:8px}}
</style></head><body>
<header><h1>OMF2115 move browser</h1><div class="bar">
<select id="har"><option value="">Both HARs</option><option>Jaguar</option><option>Shadow</option></select>
<select id="status"><option value="">Any status</option><option>authored</option><option>partial</option><option>generic</option></select>
<label><input type="checkbox" id="traced"> only with a trace</label>
<label title="Show one animation per group that shares the same sprites"><input type="checkbox" id="dedupe"> hide duplicates</label>
<input type="search" id="q" placeholder="Search name, input, animation id">
<span id="count"></span></div></header>
<main id="list"></main><div id="lb"><img alt=""></div>
<script>
const DATA=__DATA__;
const $=s=>document.querySelector(s), list=$('#list'), lb=$('#lb');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function cell(src,cls,alt){return src?`<div class="cell ${cls}"><img loading="lazy" src="${esc(src)}" alt="${esc(alt)}"></div>`
 :`<div class="cell"><span class="none">${cls==='sprite'?'not exported':'no capture'}</span></div>`}
function card(m){
 const label=(m.name||'unnamed special')+(['likely','decoded'].includes(m.name_confidence)?` (${m.name_confidence})`:'');
 const rows=m.frames.map(f=>`<div class="tag">sprite ${f.sprite}<br><span class="meta">${f.source==='recorded'?'tick '+f.tick:'pose only'}</span></div>`+
  cell(f.original,'sprite','original sprite '+f.sprite)+cell(f.blk,'cap','blockout')+cell(f.meshy,'cap','meshy')).join('');
 return `<section class="card"><div class="head"><h2>${esc(m.har_name)} &middot; anim ${m.animation} &middot; ${esc(label)}</h2>
 <span class="badge ${m.status}">${m.status} ${m.authored}/${m.sprites}</span>
 ${m.same?`<span class="badge dup" title="draws exactly the same sprites">same sprites as ${esc(m.same.split(' ').join(', '))}</span>`:''}
 <span class="meta">input <code>${esc(m.input_code)}</code> ${esc(m.input)}</span>
 <span class="meta">${m.trace?`trace <code>${esc(m.trace)}</code>`:'no trace: perform it in a live fight'}</span></div>
 <div class="grid"><div></div><div class="col">Original sprite</div><div class="col">Blockout</div><div class="col">Meshy</div>${rows}</div></section>`}
// With 'hide duplicates', keep only the lowest-numbered animation of each sprite-sharing group.
function keep(m,seen){const ids=[m.animation,...m.same.split(' ').filter(Boolean).map(x=>parseInt(x))];
 const key=m.har_name+':'+Math.min(...ids);if(!m.same)return true;if(seen.has(key))return false;seen.add(key);return true}
function render(){
 const har=$('#har').value, st=$('#status').value, tr=$('#traced').checked, dd=$('#dedupe').checked, seen=new Set(), q=$('#q').value.trim().toLowerCase();
 const out=DATA.filter(m=>(!har||m.har_name===har)&&(!st||m.status===st)&&(!tr||m.trace)&&(!dd||keep(m,seen))&&
  (!q||(`${m.name} ${m.input} ${m.input_code} ${m.animation} ${m.har_name}`).toLowerCase().includes(q)));
 list.innerHTML=out.map(card).join('')||'<p class="none">No moves match.</p>';
 $('#count').textContent=out.length+' of '+DATA.length+' moves';
}
['#har','#status','#traced','#dedupe','#q'].forEach(s=>$(s).addEventListener('input',render));
list.addEventListener('click',e=>{if(e.target.tagName==='IMG'){lb.firstElementChild.src=e.target.src;lb.style.display='flex'}});
lb.addEventListener('click',()=>lb.style.display='none');
addEventListener('keydown',e=>{if(e.key==='Escape')lb.style.display='none'});
if(location.hash.startsWith('#q='))$('#q').value=decodeURIComponent(location.hash.slice(3));
render();
</script></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--html-only", action="store_true")
    parser.add_argument("--har", type=int)
    parser.add_argument("--animation", type=int)
    args = parser.parse_args()
    if not EXE.exists() and not args.html_only:
        sys.exit(f"Build omf3d_prototype first: {EXE}")
    OUT.mkdir(parents=True, exist_ok=True)
    data = build_data(load_moves(), args)
    payload = json.dumps(data).replace("</", "<\\/")
    (OUT / "index.html").write_text(PAGE.replace("__DATA__", payload), encoding="utf-8")
    print(f"{len(data)} moves -> {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
