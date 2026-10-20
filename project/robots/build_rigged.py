"""Export editable rigid-joint glTF rigs with eight blockout motion clips.

The prototype's source-sprite pose catalog remains authoritative for match
playback. These glTF clips provide portable review animation in 3D editors.
"""
from __future__ import annotations

import base64
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from jaguar.blockout import build as jaguar  # noqa: E402
from shadow.blockout import build as shadow  # noqa: E402

sys.path.insert(0, str(ROOT.parent / "prototype"))
from generate_model_meshes import group  # noqa: E402


def fpack(blob: bytearray, values: list[float]) -> tuple[int, int]:
    while len(blob) % 4:
        blob.append(0)
    offset = len(blob)
    blob.extend(struct.pack("<"+"f"*len(values), *values))
    return offset, len(values)*4


def ipack(blob: bytearray, values: list[int]) -> tuple[int, int]:
    while len(blob) % 4:
        blob.append(0)
    offset = len(blob)
    blob.extend(struct.pack("<"+"H"*len(values), *values))
    return offset, len(values)*2


def accessor(gltf, blob, values, count, typ, component=5126, target=None):
    offset, length = (fpack(blob, values) if component == 5126 else ipack(blob, values))
    view = {"buffer": 0, "byteOffset": offset, "byteLength": length}
    if target:
        view["target"] = target
    gltf["bufferViews"].append(view)
    size = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[typ]
    vectors = [values[i:i+size] for i in range(0, len(values), size)]
    a = {"bufferView": len(gltf["bufferViews"])-1,
         "componentType": component, "count": count, "type": typ,
         "min": [min(v[i] for v in vectors) for i in range(size)],
         "max": [max(v[i] for v in vectors) for i in range(size)]}
    gltf["accessors"].append(a)
    return len(gltf["accessors"])-1


def clip(name, duration, tracks):
    """All tracks are five evenly spaced samples of normalized source motion."""
    return name, duration, tracks


def clips_for(har):
    punch = .224 if har == 0 else .364
    # X-axis rotations move limbs in the side-view Y/Z plane.
    return [
        clip("idle", 1.0, {"torso": [0,.016,0,-.016,0],
                            "shoulder_-1": [0,.035,0,-.035,0],
                            "shoulder_+1": [0,-.035,0,.035,0]}),
        clip("walk", .56, {"hip_-1": [-.34,0,.34,0,-.34],
                            "hip_+1": [.34,0,-.34,0,.34],
                            "knee_-1": [.10,.25,.10,.03,.10],
                            "knee_+1": [.10,.03,.10,.25,.10],
                            "shoulder_-1": [.20,0,-.20,0,.20],
                            "shoulder_+1": [-.20,0,.20,0,-.20]}),
        clip("jump", .70, {"root_y": [0,.58,.76,.38,0],
                            "hip_-1": [0,.28,.38,.25,0],
                            "hip_+1": [0,.58,.70,.42,0],
                            "knee_-1": [0,-.30,-.38,-.24,0],
                            "knee_+1": [0,-.60,-.72,-.43,0],
                            "shoulder_+1": [0,.20,.32,.12,0]}),
        clip("guard", .28, {"torso": [0,-.04,-.06,-.05,-.04],
                             "shoulder_-1": [0,.22,.30,.30,.30],
                             "shoulder_+1": [0,.22,.30,.30,.30],
                             "elbow_-1": [0,.56,.75,.75,.75],
                             "elbow_+1": [0,.56,.75,.75,.75]}),
        clip("punch", punch, {"torso": [0,.05,.08,.04,0],
                               "shoulder_+1": [0,.54,.91,.48,0],
                               "elbow_+1": [0,.40,.66,.35,0],
                               "hip_+1": [0,.08,.12,.06,0]}),
        clip("kick", .420, {"hip_+1": [0,.52,1.15,.44,0],
                             "knee_+1": [0,-.66,-.20,-.66,0],
                             "shoulder_+1": [0,.14,.30,.12,0],
                             "torso": [0,-.08,-.12,-.04,0]}),
        clip("hit", .40, {"torso": [0,-.15,-.20,-.08,0],
                           "shoulder_-1": [0,-.20,-.33,-.16,0],
                           "shoulder_+1": [0,-.28,-.40,-.18,0],
                           "elbow_+1": [0,.34,.52,.22,0]}),
        clip("signature", .58 if har == 0 else .70,
             {"torso": [0,.08,.13,.11,0],
              "shoulder_+1": [0,.42,1.02,1.08,0],
              "elbow_+1": [0,.28,.61,.55,0],
              "hip_+1": [0,.18,.34,.28,0],
              "hip_-1": [0,-.11,-.22,-.16,0]}),
    ]


def export(har, parts, output):
    pivots = {"root": (0, 0, 0), "torso": (0, 0, 0),
              "head": (0, 2.77 if har == 0 else 2.75, 0),
              "pelvis": (0, 1.38, 0)}
    parents = {"root": None, "torso": "root", "head": "torso", "pelvis": "torso"}
    shoulder_x = .76 if har == 0 else .79
    elbow_x = 1.02 if har == 0 else 1.05
    wrist_x = 1.30 if har == 0 else 1.31
    hip_x = .34 if har == 0 else .35
    knee_x = .40 if har == 0 else .42
    ankle_x = .43 if har == 0 else .44
    for side in (-1, 1):
        suffix = f"{side:+d}"
        pivots[f"shoulder_{suffix}"] = (side*shoulder_x, 2.28 if har == 0 else 2.30, 0)
        pivots[f"elbow_{suffix}"] = (side*elbow_x, 1.72, -.02)
        pivots[f"wrist_{suffix}"] = (side*wrist_x, 1.09, -.08)
        pivots[f"hip_{suffix}"] = (side*hip_x, 1.31, 0)
        pivots[f"knee_{suffix}"] = (side*knee_x, .69 if har == 0 else .70, 0)
        pivots[f"ankle_{suffix}"] = (side*ankle_x, .19 if har == 0 else .20, -.02)
        parents[f"shoulder_{suffix}"] = "torso"
        parents[f"elbow_{suffix}"] = f"shoulder_{suffix}"
        parents[f"wrist_{suffix}"] = f"elbow_{suffix}"
        parents[f"hip_{suffix}"] = "pelvis"
        parents[f"knee_{suffix}"] = f"hip_{suffix}"
        parents[f"ankle_{suffix}"] = f"knee_{suffix}"
    gltf = {"asset": {"version": "2.0", "generator": "OMF3K rigid-joint rig"},
            "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [], "meshes": [],
            "materials": [], "animations": [], "buffers": [], "bufferViews": [], "accessors": [],
            "extras": {"design": "approved OMF3K three-view references",
                       "motion": "original OMF sprite poses and matched Remastered frames",
                       "runtime": "source ticks drive prototype poses; these clips are editor previews"}}
    node_ids = {}
    for name, point in pivots.items():
        parent = parents[name]
        parent_point = pivots[parent] if parent else (0, 0, 0)
        rel = [point[i]-parent_point[i] for i in range(3)]
        node_ids[name] = len(gltf["nodes"])
        gltf["nodes"].append({"name": name, "translation": rel, "children": []})
    for name, parent in parents.items():
        if parent:
            gltf["nodes"][node_ids[parent]]["children"].append(node_ids[name])
    blob = bytearray()
    colors = list(dict.fromkeys(part[3] for part in parts))
    for color in colors:
        gltf["materials"].append({"name": "blockout_"+"_".join(map(str,color)),
                                  "doubleSided": True,
                                  "pbrMetallicRoughness": {
                                      "baseColorFactor": [*(c/255 for c in color), 1],
                                      "metallicFactor": .35, "roughnessFactor": .72}})
    for name, vertices, faces, color in parts:
        rig_group = group(name)
        side = -1 if "_-1" in name else (1 if "_+1" in name else 0)
        suffix = f"{side:+d}"
        joint = {0: "torso", 1: "head", 2: "pelvis", 3: f"shoulder_{suffix}",
                 4: f"elbow_{suffix}", 5: f"wrist_{suffix}", 6: f"hip_{suffix}",
                 7: f"knee_{suffix}", 8: f"ankle_{suffix}"}[rig_group]
        pivot = pivots[joint]
        local = [[v[i]-pivot[i] for i in range(3)] for v in vertices]
        pos = accessor(gltf, blob, [v for p in local for v in p], len(local), "VEC3", target=34962)
        flat_faces = [i for face in faces for i in face]
        idx = accessor(gltf, blob, flat_faces, len(flat_faces), "SCALAR", 5123, 34963)
        mesh_id = len(gltf["meshes"])
        gltf["meshes"].append({"name": name, "primitives": [{"attributes": {"POSITION": pos},
                                                               "indices": idx,
                                                               "material": colors.index(color)}]})
        node_id = len(gltf["nodes"])
        gltf["nodes"].append({"name": name, "mesh": mesh_id})
        gltf["nodes"][node_ids[joint]]["children"].append(node_id)
    for clip_name, duration, tracks in clips_for(har):
        times = [duration*i/4 for i in range(5)]
        time_access = accessor(gltf, blob, times, 5, "SCALAR")
        animation = {"name": clip_name, "samplers": [], "channels": []}
        for joint, angles in tracks.items():
            if joint == "root_y":
                values = [v for y in angles for v in (0, y, 0)]
                typ, path, target = "VEC3", "translation", "root"
            else:
                values = [v for a in angles for v in (math.sin(a/2), 0, 0, math.cos(a/2))]
                typ, path, target = "VEC4", "rotation", joint
            output_access = accessor(gltf, blob, values, 5, typ)
            sampler_id = len(animation["samplers"])
            animation["samplers"].append({"input": time_access, "output": output_access,
                                           "interpolation": "LINEAR"})
            animation["channels"].append({"sampler": sampler_id,
                                            "target": {"node": node_ids[target], "path": path}})
        gltf["animations"].append(animation)
    gltf["buffers"] = [{"byteLength": len(blob),
                        "uri": "data:application/octet-stream;base64,"+
                               base64.b64encode(blob).decode()}]
    output.write_text(json.dumps(gltf, separators=(",", ":")))
    print(f"{output.name}: {len(parts)} parts, {len(gltf['animations'])} clips")


def main():
    jaguar.PARTS.clear()
    jaguar.make_model()
    export(0, list(jaguar.PARTS), ROOT / "jaguar" / "blockout" / "jaguar-rigged.gltf")
    jaguar.PARTS.clear()
    shadow.make_model()
    export(1, list(jaguar.PARTS), ROOT / "shadow" / "blockout" / "shadow-rigged.gltf")


if __name__ == "__main__":
    main()
