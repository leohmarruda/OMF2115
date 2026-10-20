"""Generate Shadow's editable silhouette blockout from the approved views."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from jaguar.blockout import build as mesh  # noqa: E402

mesh.HERE = HERE
mesh.PARTS.clear()
B, T, S = mesh.box, mesh.tapered, mesh.segment
P, A = mesh.plate, mesh.add
SILVER, LIGHT, DARK, GREEN = mesh.SILVER, mesh.LIGHT, mesh.DARK, mesh.GREEN


def spike(name, base, tip, radius=.12, color=LIGHT):
    x, y, z = base
    v = [(x-radius, y-radius*.5, z-radius*.5),
         (x+radius, y-radius*.5, z-radius*.5),
         (x+radius, y+radius*.5, z+radius*.5),
         (x-radius, y+radius*.5, z+radius*.5), tip]
    A(name, v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
                (0, 3, 2), (0, 2, 1)], color)


def make_model():
    # Compact helmet, recessed featureless face, and solid silver rear shell.
    T("helmet_shell", 2.91, 3.36, .52, .64, .47, .55, color=LIGHT)
    P("face_void", [(-.28, 3.17), (.28, 3.17), (.20, 2.95),
                     (0, 2.85), (-.20, 2.95)], -.325, -.28, DARK)
    P("helmet_brow", [(-.32, 3.23), (0, 3.16), (.32, 3.23),
                       (.26, 3.32), (-.26, 3.32)], -.36, -.29, LIGHT)
    for side in (-1, 1):
        B(f"eye_{side:+d}", (side*.145, 3.10, -.365), (.125, .04, .025), GREEN)
        P(f"helmet_cheek_{side:+d}", [(side*.25, 3.18),
                                      (side*.31, 3.12), (side*.14, 2.91),
                                      (side*.10, 2.94)], -.36, -.28)
    B("neck_rib_core", (0, 2.75, 0), (.30, .25, .30), DARK)
    for rib in range(3):
        B(f"neck_rib_{rib}", (0, 2.70+rib*.08, -.16), (.34, .035, .045), SILVER)
    T("torso_mechanism", 1.69, 2.55, .46, .77, .42, .47, color=DARK)
    # One continuous inverted triangular plate, with long outer tips.
    P("front_inverted_plate", [(-1.48, 2.73), (0, 2.48),
                               (1.48, 2.73), (.46, 2.30),
                               (0, 1.91), (-.46, 2.30)], -.31, -.22, LIGHT)
    mesh.profile("chest_side_wedge", [(2.73, .55), (2.62, -.34),
                                      (2.16, -.62), (1.92, -.42),
                                      (2.31, .17)], .47, LIGHT)
    P("rear_inverted_plate", [(-1.48, 2.73), (0, 2.48),
                              (1.48, 2.73), (.46, 2.30),
                              (0, 1.91), (-.46, 2.30)], .23, .31, SILVER)
    P("chest_light_socket", [(-.10, 2.16), (.10, 2.16),
                             (.06, 2.03), (0, 1.98), (-.06, 2.03)], -.325, -.315, DARK)
    B("chest_light", (0, 2.085, -.345), (.075, .10, .02), GREEN)
    for rib in range(5):
        B(f"waist_rib_{rib}", (0, 1.53+rib*.095, -.245),
          (.50+rib*.025, .045, .06), (67, 74, 80))
    T("pelvis_armor", 1.25, 1.52, .49, .66, .43, .47)
    for side in (-1, 1):
        s = float(side)
        B(f"shoulder_joint_{side:+d}", (s*.79, 2.30, 0), (.27, .25, .31), DARK)
        S(f"upper_arm_rib_core_{side:+d}", (s*.78, 2.25, 0),
          (s*1.03, 1.77, -.02), .21, .18, .25, .23, DARK)
        S(f"upper_arm_side_armor_{side:+d}", (s*.84, 2.27, .16),
          (s*1.06, 1.80, .15), .18, .13, .12, .10)
        B(f"elbow_joint_{side:+d}", (s*1.05, 1.72, -.02), (.25, .25, .27), DARK)
        spike(f"elbow_spike_{side:+d}", (s*1.13, 1.72, -.03),
              (s*1.40, 1.74, -.04), .11)
        S(f"forearm_rib_core_{side:+d}", (s*1.06, 1.66, -.02),
          (s*1.30, 1.11, -.08), .19, .16, .23, .20, DARK)
        S(f"forearm_side_armor_{side:+d}", (s*1.12, 1.62, .13),
          (s*1.32, 1.15, .09), .14, .12, .12, .10)
        for rib in range(4):
            y = 2.11-rib*.10
            B(f"upper_arm_rib_{side:+d}_{rib}", (s*(.87+rib*.05), y, -.14),
              (.22, .038, .055), (67, 74, 80))
            y2 = 1.56-rib*.11
            B(f"forearm_rib_{side:+d}_{rib}", (s*(1.11+rib*.05), y2, -.16),
              (.19, .035, .05), (67, 74, 80))
        B(f"wrist_{side:+d}", (s*1.31, 1.09, -.08), (.18, .12, .20), DARK)
        B(f"hand_base_{side:+d}", (s*1.32, .99, -.09), (.20, .18, .23))
        for finger in (-1, 0, 1):
            x = s*1.32+finger*.075
            spike(f"hand_spike_{side:+d}_{finger:+d}",
                  (x, .91, -.13), (x+finger*.03, .64, -.18), .06)
        B(f"hip_joint_{side:+d}", (s*.35, 1.31, 0), (.27, .20, .29), DARK)
        S(f"thigh_rib_core_{side:+d}", (s*.35, 1.27, 0),
          (s*.42, .76, 0), .23, .20, .32, .27, DARK)
        S(f"thigh_side_armor_{side:+d}", (s*.43, 1.23, .17),
          (s*.46, .82, .15), .22, .18, .16, .13)
        B(f"knee_joint_{side:+d}", (s*.42, .70, 0), (.29, .20, .30), DARK)
        spike(f"knee_spike_{side:+d}", (s*.49, .70, 0),
              (s*.78, .69, 0), .11)
        S(f"shin_rib_core_{side:+d}", (s*.42, .65, 0),
          (s*.44, .24, -.02), .19, .16, .28, .23, DARK)
        S(f"shin_side_armor_{side:+d}", (s*.47, .61, .14),
          (s*.47, .29, .12), .18, .15, .13, .10)
        for rib in range(4):
            B(f"thigh_rib_{side:+d}_{rib}", (s*(.38+rib*.01), 1.13-rib*.10, -.18),
              (.22, .035, .05), (67, 74, 80))
            B(f"shin_rib_{side:+d}_{rib}", (s*.44, .59-rib*.09, -.15),
              (.18, .035, .05), (67, 74, 80))
        B(f"ankle_{side:+d}", (s*.44, .20, -.02), (.22, .13, .24), DARK)
        B(f"foot_heel_{side:+d}", (s*.44, .10, .10), (.34, .20, .40))
        B(f"foot_toe_{side:+d}", (s*.44, .065, -.33), (.35, .13, .47), LIGHT)


if __name__ == "__main__":
    make_model()
    mesh.write_gltf("shadow-blockout.gltf", "OMF2115 Shadow blockout")
    for view in ("front", "back", "side"):
        mesh.render(view, HERE / f"shadow-{view}.png")
    mesh.render("side", HERE / "shadow-fight-distance.png", 960, 600, 55, 1.68)
    print(f"{len(mesh.PARTS)} editable meshes, "
          f"{sum(len(p[2]) for p in mesh.PARTS)} triangles")
