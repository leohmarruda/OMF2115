"""Generate Jaguar's editable, low-poly silhouette blockout and review renders.

Coordinates match the prototype: Y up, negative Z toward the opponent. No
original or Remastered artwork is embedded in the model.
"""
from __future__ import annotations

import base64
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import ConvexHull


HERE = Path(__file__).resolve().parent
SILVER = (178, 190, 199)
LIGHT = (207, 217, 222)
DARK = (30, 38, 45)
GREEN = (35, 229, 67)
PARTS: list[tuple[str, list[tuple[float, float, float]], list[tuple[int, int, int]], tuple[int, int, int]]] = []


def add(name, vertices, faces, color=SILVER):
    PARTS.append((name, vertices, faces, color))


def box(name, center, size, color=SILVER):
    x, y, z = center
    w, h, d = [v / 2 for v in size]
    v = [(x + sx*w, y + sy*h, z + sz*d)
         for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    add(name, v, [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6),
                  (0, 1, 5), (0, 5, 4), (2, 6, 7), (2, 7, 3),
                  (0, 4, 6), (0, 6, 2), (1, 3, 7), (1, 7, 5)], color)


def tapered(name, y0, y1, w0, w1, d0, d1, z=0, color=SILVER):
    v = []
    for y, w, d in ((y0, w0, d0), (y1, w1, d1)):
        for zz in (z-d/2, z+d/2):
            for x in (-w/2, w/2):
                v.append((x, y, zz))
    add(name, v, [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
                  (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
                  (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)], color)


def segment(name, a, b, width0, width1, depth0, depth1, color=SILVER):
    """Six-sided limb volume between two editable joint coordinates."""
    ax, ay, az = a
    bx, by, bz = b
    length = math.hypot(by-ay, bz-az)
    ny, nz = -(bz-az)/length, (by-ay)/length
    v = []
    for (x, y, z), w, d in ((a, width0, depth0), (b, width1, depth1)):
        for sx, sn in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            v.append((x+sx*w/2, y+sn*ny*d/2, z+sn*nz*d/2))
    add(name, v, [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
                  (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
                  (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)], color)


def plate(name, xy, front, back, color=SILVER):
    n = len(xy)
    v = [(x, y, front) for x, y in xy] + [(x, y, back) for x, y in xy]
    faces = []
    for i in range(1, n-1):
        faces.extend(((0, i, i+1), (n, n+i+1, n+i)))
    for i in range(n):
        j = (i+1) % n
        faces.extend(((i, j, n+j), (i, n+j, n+i)))
    add(name, v, faces, color)


def prism(name, outer, inner, color=SILVER):
    """Thin slab: an outer polygon and the same polygon on the inner surface, wound to face out."""
    n = len(outer)
    v = list(outer) + list(inner)
    faces = []
    for i in range(1, n-1):
        faces.extend(((0, i, i+1), (n, n+i+1, n+i)))
    for i in range(n):
        j = (i+1) % n
        faces.extend(((i, j, n+j), (i, n+j, n+i)))
    add(name, v, faces, color)


def profile(name, yz, half_width, color=SILVER):
    """Extrude a side-view silhouette across the robot's width."""
    n = len(yz)
    v = [(-half_width, y, z) for y, z in yz] + \
        [(half_width, y, z) for y, z in yz]
    faces = []
    for i in range(1, n-1):
        faces.extend(((0, i, i+1), (n, n+i+1, n+i)))
    for i in range(n):
        j = (i+1) % n
        faces.extend(((i, j, n+j), (i, n+j, n+i)))
    add(name, v, faces, color)


def head():
    """Canonical wedge helmet: flat top, two front planes meeting at a centre ridge,
    a narrow chin and a back that slopes in. Eyes lie on the front planes."""
    top, chin = 3.34, 2.88
    ridge_top, ridge_chin = -.41, -.15      # centre ridge depth at the brow and at the chin
    edge_top, edge_chin = -.29, -.07        # outer corner depth at the brow and at the chin
    pts = [(-.38, top-.02, edge_top), (.38, top-.02, edge_top), (0, top, ridge_top),
           (-.40, top-.02, .27), (.40, top-.02, .27),
           (-.15, chin+.02, edge_chin), (.15, chin+.02, edge_chin), (0, chin, ridge_chin),
           (-.17, chin+.02, .12), (.17, chin+.02, .12)]
    hull = ConvexHull(pts)
    c = [sum(p[i] for p in pts)/len(pts) for i in range(3)]
    faces = []
    for a, b, d in hull.simplices:
        n = np.cross(np.subtract(pts[b], pts[a]), np.subtract(pts[d], pts[a]))
        outward = np.dot(n, np.subtract(pts[a], c)) > 0
        faces.append((int(a), int(b), int(d)) if outward else (int(a), int(d), int(b)))
    add("helmet_core", pts, faces, LIGHT)

    def face_z(x, y):
        """Depth of the helmet's front surface at (x, y), found on the hull triangles themselves."""
        best = None
        for tri in faces:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (pts[i] for i in tri)
            det = (by-cy)*(ax-cx) + (cx-bx)*(ay-cy)
            if abs(det) < 1e-9:
                continue
            u = ((by-cy)*(x-cx) + (cx-bx)*(y-cy)) / det
            v = ((cy-ay)*(x-cx) + (ax-cx)*(y-cy)) / det
            if min(u, v, 1-u-v) >= -1e-9:
                z = u*az + v*bz + (1-u-v)*cz
                best = z if best is None else min(best, z)
        return best

    for side in (-1, 1):
        # Angry slant: the outer end sits high, the inner end low. A slab, not a decal, so it
        # reads from the side as well.
        eye = [(side*.06, 3.10), (side*.24, 3.19), (side*.25, 3.12), (side*.09, 3.04)]
        if side < 0:
            eye.reverse()
        prism(f"eye_{side:+d}", [(x, y, face_z(x, y) - .03) for x, y in eye],
              [(x, y, face_z(x, y) + .01) for x, y in eye], GREEN)
    # Two rear panels with a central seam, standing just off the sloping back face.
    for side in (-1, 1):
        s = float(side)
        quad = [(s*.012, top-.03), (s*.36, top-.03), (s*.16, chin+.05), (s*.012, chin+.05)]
        zs = (.31, .30, .17, .16)
        if side < 0:
            quad.reverse(); zs = zs[::-1]
        prism(f"rear_helmet_{'left' if side < 0 else 'right'}",
              [(x, y, z+.03) for (x, y), z in zip(quad, zs)],
              [(x, y, z-.01) for (x, y), z in zip(quad, zs)], SILVER)


def make_model():
    # Large volumes first. The rear helmet is deliberately split into two
    # panels; face pieces and the chest mark exist on the front only.
    head()
    box("neck", (0, 2.77, 0), (.30, .22, .31), DARK)
    tapered("torso_core", 1.80, 2.56, .81, 1.22, .47, .55, color=DARK)
    plate("front_chest_wedge", [(-.58, 2.52), (.58, 2.52),
                                 (.47, 2.10), (0, 1.88), (-.47, 2.10)], -.34, -.24, LIGHT)
    profile("chest_side_wedge", [(2.54, .27), (2.54, -.21),
                                  (2.28, -.46), (1.91, -.37),
                                  (1.84, .12), (2.03, .30)], .49, SILVER)
    plate("rear_upper_plate", [(-.57, 2.51), (.57, 2.51),
                                (.46, 2.15), (0, 1.99), (-.46, 2.15)], .285, .32)
    plate("rear_lower_plate", [(-.46, 2.13), (0, 1.96), (.46, 2.13),
                                (.38, 1.83), (-.38, 1.83)], .28, .315)
    plate("chest_emblem_block", [(-.11, 2.35), (0, 2.30), (.11, 2.35),
                                  (.065, 2.22), (0, 2.17), (-.065, 2.22)], -.347, -.339, DARK)
    box("abdomen", (0, 1.67, 0), (.60, .28, .43), DARK)
    tapered("pelvis", 1.30, 1.61, .67, .74, .43, .46, color=SILVER)
    for side in (-1, 1):
        s = float(side)
        plate(f"shoulder_fin_{side:+d}", [(s*.55, 2.55), (s*1.28, 2.76),
                                          (s*1.04, 2.35), (s*.77, 2.30)], -.20, .22, LIGHT)
        box(f"shoulder_joint_{side:+d}", (s*.76, 2.29, .0), (.24, .24, .28), DARK)
        segment(f"upper_arm_{side:+d}", (s*.77, 2.24, 0), (s*1.01, 1.76, -.02),
                .32, .27, .38, .30)
        box(f"elbow_joint_{side:+d}", (s*1.02, 1.72, -.02), (.25, .24, .27), DARK)
        segment(f"forearm_{side:+d}", (s*1.04, 1.66, -.03), (s*1.29, 1.13, -.08),
                .29, .23, .35, .27)
        box(f"wrist_joint_{side:+d}", (s*1.30, 1.09, -.08), (.20, .12, .23), DARK)
        box(f"palm_{side:+d}", (s*1.32, .97, -.10), (.22, .20, .28))
        for digit in (-1, 1):
            x = s*1.32 + digit*.068
            segment(f"finger_{side:+d}_{digit:+d}", (x, .88, -.16),
                    (x+digit*.02, .68, -.18), .067, .055, .10, .08)
        segment(f"thumb_{side:+d}", (s*1.21, 1.00, -.20),
                (s*1.17, .82, -.28), .075, .055, .10, .08)
        box(f"hip_joint_{side:+d}", (s*.34, 1.31, 0), (.28, .19, .30), DARK)
        segment(f"thigh_{side:+d}", (s*.34, 1.30, 0), (s*.40, .75, -.01),
                .36, .31, .47, .38)
        box(f"knee_joint_{side:+d}", (s*.40, .69, -.01), (.31, .20, .34), DARK)
        segment(f"shin_{side:+d}", (s*.40, .65, -.01), (s*.43, .23, -.02),
                .30, .24, .37, .29)
        box(f"ankle_joint_{side:+d}", (s*.43, .19, -.02), (.22, .14, .25), DARK)
        box(f"foot_heel_{side:+d}", (s*.43, .105, .06), (.35, .19, .39))
        box(f"foot_toe_{side:+d}", (s*.43, .075, -.32), (.36, .15, .46), LIGHT)


def write_gltf(filename="jaguar-blockout.gltf", generator="OMF3K Jaguar blockout"):
    blob = bytearray()
    gltf = {"asset": {"version": "2.0", "generator": generator},
            "scene": 0, "scenes": [{"nodes": list(range(len(PARTS)))}],
            "nodes": [], "meshes": [], "materials": [], "buffers": [],
            "bufferViews": [], "accessors": []}
    colors = list(dict.fromkeys(p[3] for p in PARTS))
    for color in colors:
        gltf["materials"].append({"name": {SILVER: "satin_silver", LIGHT: "bright_edge",
                                          DARK: "dark_joint", GREEN: "green_accent"}.get(color, "mechanical_rib"),
                                  "doubleSided": True,
                                  "pbrMetallicRoughness": {"baseColorFactor": [*(c/255 for c in color), 1],
                                                           "metallicFactor": .35, "roughnessFactor": .7}})
    for name, vertices, faces, color in PARTS:
        while len(blob) % 4:
            blob.append(0)
        po = len(blob)
        for v in vertices:
            blob.extend(struct.pack("<3f", *v))
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": po,
                                    "byteLength": len(vertices)*12, "target": 34962})
        pa = len(gltf["accessors"])
        gltf["accessors"].append({"bufferView": len(gltf["bufferViews"])-1,
                                  "componentType": 5126, "count": len(vertices), "type": "VEC3",
                                  "min": [min(v[i] for v in vertices) for i in range(3)],
                                  "max": [max(v[i] for v in vertices) for i in range(3)]})
        io = len(blob)
        indices = [i for f in faces for i in f]
        for i in indices:
            blob.extend(struct.pack("<H", i))
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": io,
                                    "byteLength": len(indices)*2, "target": 34963})
        ia = len(gltf["accessors"])
        gltf["accessors"].append({"bufferView": len(gltf["bufferViews"])-1,
                                  "componentType": 5123, "count": len(indices), "type": "SCALAR",
                                  "min": [min(indices)], "max": [max(indices)]})
        gltf["meshes"].append({"name": name, "primitives": [{"attributes": {"POSITION": pa},
                             "indices": ia, "material": colors.index(color)}]})
        gltf["nodes"].append({"name": name, "mesh": len(gltf["meshes"])-1})
    gltf["buffers"] = [{"byteLength": len(blob), "uri": "data:application/octet-stream;base64,"+
                        base64.b64encode(blob).decode()}]
    (HERE / filename).write_text(json.dumps(gltf, separators=(",", ":")))


def render(view, out, width=600, height=600, scale=135, center_y=1.68):
    """Flat-shaded render with a per-pixel depth buffer, so thin slabs (eyes, rear panels)
    sit correctly against the large parts around them."""
    image = np.zeros((height, width, 3), np.uint8)
    image[:] = (11, 15, 23)
    zbuf = np.full((height, width), np.inf)
    for _, vertices, faces, color in PARTS:
        for tri in faces:
            pts = [vertices[i] for i in tri]
            if view == "front":
                sx = [x for x, y, z in pts]; depth = [z for x, y, z in pts]
            elif view == "back":
                sx = [-x for x, y, z in pts]; depth = [-z for x, y, z in pts]
            else:
                sx = [-z for x, y, z in pts]; depth = [x for x, y, z in pts]
            px = [width/2 + x*scale for x in sx]
            py = [height/2 - (y-center_y)*scale for x, y, z in pts]
            x0, x1 = max(int(min(px)), 0), min(int(max(px))+1, width)
            y0, y1 = max(int(min(py)), 0), min(int(max(py))+1, height)
            if x0 >= x1 or y0 >= y1:
                continue
            det = (py[1]-py[2])*(px[0]-px[2]) + (px[2]-px[1])*(py[0]-py[2])
            if abs(det) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + .5, np.arange(y0, y1) + .5)
            u = ((py[1]-py[2])*(gx-px[2]) + (px[2]-px[1])*(gy-py[2])) / det
            w = ((py[2]-py[0])*(gx-px[2]) + (px[0]-px[2])*(gy-py[2])) / det
            t = 1 - u - w
            inside = (u >= 0) & (w >= 0) & (t >= 0)
            z = u*depth[0] + w*depth[1] + t*depth[2]
            win = inside & (z < zbuf[y0:y1, x0:x1])
            zbuf[y0:y1, x0:x1][win] = z[win]
            image[y0:y1, x0:x1][win] = color
    Image.fromarray(image).save(out)


if __name__ == "__main__":
    make_model()
    write_gltf()
    for view in ("front", "back", "side"):
        render(view, HERE / f"jaguar-{view}.png")
    # Equivalent on-screen height to the source replay's 960x600 fight camera:
    # (3.34 * .84 / 4.6) * 300 = 183 pixels.
    render("side", HERE / "jaguar-fight-distance.png", 960, 600, 55, 1.68)
    print(f"{len(PARTS)} editable meshes, {sum(len(p[2]) for p in PARTS)} triangles")
